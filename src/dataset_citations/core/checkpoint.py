"""Per-anchor checkpoint store for the opencite pipeline.

Crash recovery for long-running citation fetches: persist each anchor's
opencite result the moment it lands so a re-run only re-fetches the
anchors that didn't complete the first time. The file format mirrors the
schema-v2 citation JSON shape closely enough that a partial checkpoint
can be inspected by hand.

A checkpoint file lives at `<base>/<dataset_id>.json` (default base:
`citations/.checkpoints/`). Files are local-only transient state; the
gitignore excludes them.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from dataset_citations.sources.models import (
    Author,
    CitingWork,
    FetchError,
    FetchErrorReason,
    FetchSuccess,
    RelationType,
)

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DIR = Path("citations/.checkpoints")
CHECKPOINT_SCHEMA = "1.0"


@dataclass(slots=True)
class AnchorOutcome:
    """One anchor's recorded result.

    `status == "success"` means `works` holds the citing-works payload and
    no re-fetch is needed. Anything else is a `FetchErrorReason` and the
    pipeline will retry that anchor on the next run.
    """

    status: str
    works: list[CitingWork] = field(default_factory=list)
    fetched_at: str = ""


@dataclass(slots=True)
class Checkpoint:
    """Aggregate of anchor outcomes for one dataset."""

    dataset_id: str
    anchors: dict[str, AnchorOutcome] = field(default_factory=dict)

    def is_success(self, anchor_identifier: str) -> bool:
        outcome = self.anchors.get(anchor_identifier)
        return outcome is not None and outcome.status == "success"

    def successful_works(self, anchor_identifier: str) -> list[CitingWork]:
        outcome = self.anchors.get(anchor_identifier)
        if outcome is None or outcome.status != "success":
            return []
        return list(outcome.works)


class CheckpointStore:
    """File-backed checkpoint store. One JSON file per dataset_id."""

    def __init__(self, base_dir: Path = DEFAULT_CHECKPOINT_DIR) -> None:
        self.base_dir = Path(base_dir)

    def path_for(self, dataset_id: str) -> Path:
        return self.base_dir / f"{dataset_id}.json"

    def load(self, dataset_id: str) -> Checkpoint:
        """Read the checkpoint file if it exists; otherwise return empty."""
        path = self.path_for(dataset_id)
        if not path.is_file():
            return Checkpoint(dataset_id=dataset_id)
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("checkpoint %s unreadable, treating as empty: %s", path, exc)
            return Checkpoint(dataset_id=dataset_id)
        if not isinstance(payload, dict):
            logger.warning("checkpoint %s has wrong shape, ignoring", path)
            return Checkpoint(dataset_id=dataset_id)
        return _deserialize(payload, dataset_id)

    def save(self, checkpoint: Checkpoint) -> None:
        """Persist the full checkpoint atomically (write to tmp, rename)."""
        path = self.path_for(checkpoint.dataset_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(_serialize(checkpoint), indent=2, ensure_ascii=False)
        )
        tmp_path.replace(path)

    def record_anchor(
        self,
        dataset_id: str,
        anchor_identifier: str,
        result: FetchSuccess[list[CitingWork]] | FetchError,
        when: datetime | None = None,
    ) -> Checkpoint:
        """Update one anchor's outcome and flush the file."""
        checkpoint = self.load(dataset_id)
        ts = (when or datetime.now(timezone.utc)).isoformat()
        if isinstance(result, FetchSuccess):
            outcome = AnchorOutcome(
                status="success", works=list(result.value), fetched_at=ts
            )
        else:
            outcome = AnchorOutcome(status=result.reason, works=[], fetched_at=ts)
        checkpoint.anchors[anchor_identifier] = outcome
        self.save(checkpoint)
        return checkpoint

    def clear(self, dataset_id: str) -> None:
        """Remove the checkpoint file for a dataset (post-success cleanup)."""
        path = self.path_for(dataset_id)
        if path.is_file():
            path.unlink()


def _serialize(checkpoint: Checkpoint) -> dict[str, Any]:
    return {
        "dataset_id": checkpoint.dataset_id,
        "schema_version": CHECKPOINT_SCHEMA,
        "anchors": {
            identifier: {
                "status": outcome.status,
                "fetched_at": outcome.fetched_at,
                "works": [_serialize_work(w) for w in outcome.works],
            }
            for identifier, outcome in checkpoint.anchors.items()
        },
    }


def _deserialize(payload: dict[str, Any], dataset_id: str) -> Checkpoint:
    anchors_raw = payload.get("anchors") or {}
    anchors: dict[str, AnchorOutcome] = {}
    if not isinstance(anchors_raw, dict):
        return Checkpoint(dataset_id=dataset_id)
    for identifier, raw in anchors_raw.items():
        if not isinstance(raw, dict):
            continue
        status = raw.get("status", "")
        works_raw = raw.get("works") or []
        works: list[CitingWork] = []
        if isinstance(works_raw, list):
            for w in works_raw:
                if not isinstance(w, dict):
                    continue
                try:
                    works.append(_deserialize_work(w))
                except (KeyError, ValueError, TypeError) as exc:
                    logger.warning(
                        "skipping malformed checkpoint work for %s/%s: %s",
                        dataset_id,
                        identifier,
                        exc,
                    )
        anchors[identifier] = AnchorOutcome(
            status=str(status), works=works, fetched_at=str(raw.get("fetched_at") or "")
        )
    return Checkpoint(dataset_id=dataset_id, anchors=anchors)


def _serialize_work(work: CitingWork) -> dict[str, Any]:
    return {
        "title": work.title,
        "doi": work.doi,
        "pmid": work.pmid,
        "openalex_id": work.openalex_id,
        "year": work.year,
        "authors": [
            {"name": a.name, "family": a.family, "given": a.given, "orcid": a.orcid}
            for a in work.authors
        ],
        "venue": work.venue,
        "abstract": work.abstract,
        "citation_count": work.citation_count,
        "source_doi": work.source_doi,
        "source_relation": work.source_relation,
    }


def _deserialize_work(raw: dict[str, Any]) -> CitingWork:
    authors_raw = raw.get("authors") or []
    authors: list[Author] = []
    if isinstance(authors_raw, list):
        for a in authors_raw:
            if isinstance(a, dict) and "name" in a:
                authors.append(
                    Author(
                        name=a["name"],
                        family=a.get("family"),
                        given=a.get("given"),
                        orcid=a.get("orcid"),
                    )
                )
    return CitingWork(
        title=raw["title"],
        doi=raw.get("doi"),
        pmid=raw.get("pmid"),
        openalex_id=raw.get("openalex_id"),
        year=raw.get("year"),
        authors=tuple(authors),
        venue=raw.get("venue"),
        abstract=raw.get("abstract"),
        citation_count=raw.get("citation_count"),
        source_doi=raw["source_doi"],
        source_relation=_validate_relation(raw["source_relation"]),
    )


def _validate_relation(value: Any) -> RelationType:
    allowed = {"References", "IsDerivedFrom", "IsIdenticalTo", "IsVersionOf"}
    if value not in allowed:
        raise ValueError(f"source_relation {value!r} not in allow-list")
    return value  # type: ignore[return-value]


def reason_for_status(status: str) -> FetchErrorReason | None:
    """Map a checkpoint status string back to a FetchErrorReason, if applicable.

    Returns None for `"success"`; otherwise the literal value (validated to
    be one of the FetchErrorReason union members).
    """
    if status == "success":
        return None
    allowed: set[FetchErrorReason] = {
        "not_found",
        "auth",
        "network",
        "parse",
        "rate_limit",
        "other",
    }
    if status in allowed:
        return cast(FetchErrorReason, status)
    return "other"
