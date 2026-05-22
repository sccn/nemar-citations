"""Per-dataset LLM anchor adjudication storage + orchestration.

Phase 2 of epic #76. Productizes the phase-1 probe (`scripts/probe_anchor_judgment.py`)
into a real per-dataset sidecar file at `citations/anchor_judgments/<id>.json`
and the assembly function the batch CLI loops over.

Sidecar schema (locked; phase 3 reads this):

  {
    "dataset_id": "<id>",
    "judged_at": "<ISO-8601 UTC, most recent judgment in this file>",
    "judgment_model": "<ollama model name>",
    "judgments": [
      {
        "anchor_identifier": "10.xxxx/yyyy",
        "anchor_identifier_type": "doi",
        "source_relation": "IsDerivedFrom",
        "classification": "umbrella",
        "reason": "<the LLM's reason string>",
        "paper_title": "<openalex title; null if get_paper failed>",
        "paper_year": 2024,
        "paper_venue": "<openalex venue; nullable>",
        "judged_at": "<ISO-8601 UTC>",
        "error": null
      }
    ]
  }

Classification values MUST belong to `ALLOWED_CLASSIFICATIONS` from
`quality.llm_client`; the LLM client enforces this on parse so the
validation lives there, not here.

Copyright (c) 2026 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dataset_citations.backends.opencite_backend import OpenCiteBackend
from dataset_citations.quality.dataset_metadata import (
    DatasetMetadataRetriever,
    _org_for_dataset,
    extract_dataset_text,
)
from dataset_citations.quality.llm_client import (
    LlmJudgmentError,
    OllamaJudgmentClient,
    build_anchor_prompt,
)
from dataset_citations.sources import (
    BidsMetadataSource,
    FetchError,
    FetchSuccess,
    NemarMetadataSource,
)
from dataset_citations.sources.models import DoiReference

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JudgmentRecord:
    """One per-anchor judgment row inside a sidecar's `judgments[]` list.

    Fields mirror the locked sidecar schema; the `to_dict()` method emits
    them in the documented order so manual file inspection is stable across
    runs. `error` is the only optional-meaning field: None on success, a
    short string when judgment failed (paper lookup, LLM transport, or
    LLM parse). When `error` is non-None, `classification` and `reason`
    may be empty strings and `paper_*` fields may be None.
    """

    anchor_identifier: str
    anchor_identifier_type: str
    source_relation: str
    classification: str
    reason: str
    paper_title: str | None
    paper_year: int | None
    paper_venue: str | None
    judged_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_identifier": self.anchor_identifier,
            "anchor_identifier_type": self.anchor_identifier_type,
            "source_relation": self.source_relation,
            "classification": self.classification,
            "reason": self.reason,
            "paper_title": self.paper_title,
            "paper_year": self.paper_year,
            "paper_venue": self.paper_venue,
            "judged_at": self.judged_at,
            "error": self.error,
        }


def _pick_source(
    dataset_id: str,
    *,
    nemar_source: NemarMetadataSource,
    bids_source: BidsMetadataSource,
) -> NemarMetadataSource | BidsMetadataSource:
    """Route a dataset id to the right DOI source.

    Delegates to `quality.dataset_metadata._org_for_dataset` so the
    metadata fetch and the DOI-ref fetch agree on which org owns the
    dataset (commit cbf595f tightened the prefix check from a loose
    `startswith` to require a digit after `nm`/`on`; future ids like
    `nmr-phantom` must NOT route to nemarDatasets).
    """
    if _org_for_dataset(dataset_id) == "nemarDatasets":
        return nemar_source
    return bids_source


def _utcnow_iso() -> str:
    """Return current time as a timezone-aware ISO-8601 UTC string."""
    return datetime.now(timezone.utc).isoformat()


def _judge_one_anchor(
    *,
    dataset_id: str,
    dataset_description: str,
    ref: DoiReference,
    backend: OpenCiteBackend,
    client: OllamaJudgmentClient,
) -> JudgmentRecord:
    """Fetch the anchor paper, build the prompt, ask the LLM. Return a record.

    Per-anchor failures (paper lookup, LLM transport, malformed output) are
    captured in the returned record's `error` field so the batch loop keeps
    going. Programmer errors are not absorbed; they propagate.
    """
    judged_at = _utcnow_iso()
    paper_result = backend.get_paper(ref.identifier)
    if isinstance(paper_result, FetchError):
        return JudgmentRecord(
            anchor_identifier=ref.identifier,
            anchor_identifier_type=ref.identifier_type,
            source_relation=ref.relation_type,
            classification="",
            reason="",
            paper_title=None,
            paper_year=None,
            paper_venue=None,
            judged_at=judged_at,
            error=f"paper_lookup_failed:{paper_result.reason}:{paper_result.detail}",
        )
    assert isinstance(paper_result, FetchSuccess)
    paper = paper_result.value

    prompt = build_anchor_prompt(
        dataset_id=dataset_id,
        dataset_description=dataset_description,
        anchor_doi=ref.identifier,
        anchor_relation=ref.relation_type,
        paper_title=paper.title,
        paper_abstract=paper.abstract,
        paper_venue=paper.venue,
        paper_authors=paper.authors,
        paper_year=paper.year,
    )
    try:
        judgment = client.judge_anchor(prompt)
    except LlmJudgmentError as exc:
        logger.warning(
            "LLM judgment failed for %s / %s: %s",
            dataset_id,
            ref.identifier,
            exc,
        )
        return JudgmentRecord(
            anchor_identifier=ref.identifier,
            anchor_identifier_type=ref.identifier_type,
            source_relation=ref.relation_type,
            classification="",
            reason="",
            paper_title=paper.title,
            paper_year=paper.year,
            paper_venue=paper.venue,
            judged_at=judged_at,
            error=f"llm_judgment_failed:{exc}",
        )

    return JudgmentRecord(
        anchor_identifier=ref.identifier,
        anchor_identifier_type=ref.identifier_type,
        source_relation=ref.relation_type,
        classification=judgment["classification"],
        reason=judgment["reason"],
        paper_title=paper.title,
        paper_year=paper.year,
        paper_venue=paper.venue,
        judged_at=judged_at,
        error=None,
    )


def judge_dataset_anchors(
    dataset_id: str,
    *,
    nemar_source: NemarMetadataSource,
    bids_source: BidsMetadataSource,
    metadata_retriever: DatasetMetadataRetriever,
    backend: OpenCiteBackend,
    client: OllamaJudgmentClient,
) -> dict[str, Any]:
    """Assemble per-anchor judgments for one dataset into a sidecar dict.

    Returns a dict ready to write to disk via `save_judgment_sidecar`.
    Empty `judgments` is a valid outcome: it means the dataset's metadata
    listed no DOI anchors OR the source lookup failed; the sidecar's
    metadata block carries enough context for phase 3 to handle either case.

    The caller is responsible for skip-existing / freshness gating; this
    function always rebuilds the judgments for the requested dataset.
    """
    source = _pick_source(
        dataset_id, nemar_source=nemar_source, bids_source=bids_source
    )
    refs_result = source.get_doi_references(dataset_id)

    judgments: list[JudgmentRecord] = []
    judged_at_latest = _utcnow_iso()

    if isinstance(refs_result, FetchError):
        logger.info(
            "%s: source returned %s (%s); writing empty judgments sidecar",
            dataset_id,
            refs_result.reason,
            refs_result.detail,
        )
        return {
            "dataset_id": dataset_id,
            "judged_at": judged_at_latest,
            "judgment_model": client.model,
            "judgments": [],
        }
    assert isinstance(refs_result, FetchSuccess)
    refs: list[DoiReference] = [
        r for r in refs_result.value if r.identifier_type == "doi"
    ]
    if not refs:
        logger.info("%s: no DOI anchors; writing empty judgments sidecar", dataset_id)
        return {
            "dataset_id": dataset_id,
            "judged_at": judged_at_latest,
            "judgment_model": client.model,
            "judgments": [],
        }

    metadata = metadata_retriever.get_dataset_metadata(dataset_id)
    dataset_description = extract_dataset_text(metadata)

    for ref in refs:
        record = _judge_one_anchor(
            dataset_id=dataset_id,
            dataset_description=dataset_description,
            ref=ref,
            backend=backend,
            client=client,
        )
        judgments.append(record)

    # judged_at is the most recent per-anchor timestamp so the file-level
    # field always advances when a re-run produces new judgments. The
    # records are processed sequentially, so the last record's timestamp
    # wins; fall back to the loop's pre-computed timestamp if the list is
    # empty (defensive — refs is non-empty above).
    judged_at_latest = judgments[-1].judged_at if judgments else judged_at_latest

    return {
        "dataset_id": dataset_id,
        "judged_at": judged_at_latest,
        "judgment_model": client.model,
        "judgments": [j.to_dict() for j in judgments],
    }


def save_judgment_sidecar(path: str | Path, payload: dict[str, Any]) -> None:
    """Atomically write a sidecar JSON to `path`.

    Writes to a sibling temp file in the same directory, fsyncs, then
    `os.replace`s into place. The sibling-directory choice keeps the
    rename a single filesystem operation (no cross-device copy).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # delete=False so we can close and rename; we clean up on failure below.
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".judgment-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except Exception:
        # Best-effort cleanup of the temp file on any write/replace failure.
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def load_judgment_sidecar(path: str | Path) -> dict[str, Any]:
    """Load a sidecar JSON from disk. Raises on missing file / invalid JSON.

    Returns the parsed dict as-is; callers that need typed access build
    `JudgmentRecord` instances from the `judgments[]` entries themselves.
    """
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: sidecar root is not a JSON object")
    return payload


def is_judgment_fresh(payload: dict[str, Any], *, max_age_days: int) -> bool:
    """Return True iff the sidecar's `judged_at` is within `max_age_days`.

    Mirrors the freshness semantics from `cli/update.py::_is_fresh_success`
    (which currently uses `<=`; issue #80 tracks the off-by-one fix). We
    keep `<=` here so phase-2 freshness behaves identically to the existing
    citation freshness gate; once #80 lands, both gates should be updated
    together.

    Robust against missing fields and unparseable timestamps: any failure
    to determine freshness returns False (re-judge).
    """
    if max_age_days <= 0:
        return False
    raw = payload.get("judged_at")
    if not isinstance(raw, str):
        return False
    try:
        when = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - when
    return age <= timedelta(days=max_age_days)
