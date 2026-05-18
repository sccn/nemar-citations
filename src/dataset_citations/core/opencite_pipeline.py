"""Phase 3 orchestrator: fetch dataset citations via the opencite backend.

Picks a source extractor by dataset-ID prefix (`nm*` -> nemar metadata,
`ds*` -> OpenNeuro BIDS description), resolves DOI/PMID/arXiv references,
asks the opencite backend for citing works, deduplicates them across source
anchors, and returns a citation JSON dict in the schema-v2 shape that
`citation_utils.add_discovery_provenance` produces.

This module deliberately mirrors the legacy `core/citation_utils.save_citation_json`
output shape so the dashboard aggregator and reporting tools keep working
when reading from `citations/json_opencite/`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from dataset_citations.backends import OpenCiteBackend
from dataset_citations.core.citation_utils import (
    SCHEMA_VERSION_V2,
    add_discovery_provenance,
)
from dataset_citations.sources import (
    BidsMetadataSource,
    CitingWork,
    DoiReference,
    FetchSuccess,
    NemarMetadataSource,
)

logger = logging.getLogger(__name__)


def fetch_dataset_citations_via_opencite(
    dataset_id: str,
    *,
    backend: OpenCiteBackend | None = None,
    nemar_source: NemarMetadataSource | None = None,
    bids_source: BidsMetadataSource | None = None,
    github_token: str | None = None,
    fetch_date: datetime | None = None,
) -> dict[str, Any]:
    """Return a schema-v2 citation JSON dict for one dataset.

    Steps:
      1. Pick the source by dataset prefix (`nm` -> nemar, `ds` -> bids).
      2. Fetch DOI/PMID anchors. On error, return a stub with the FetchError
         reason in `metadata.fetch_status` and empty `citation_details`.
      3. Ask `OpenCiteBackend.get_citing_works_batch` for citing works.
      4. Aggregate works across anchors, dedupe by (normalized DOI || title).
      5. Build the JSON dict with discovery provenance fields.

    Always returns a dict; never raises for expected fetch failures.
    `metadata.fetch_status` distinguishes outcomes:
      - "success": every anchor returned a successful result.
      - "partial": at least one anchor returned a FetchError but others
        produced citing works; see `metadata.anchor_errors` for details.
      - Any other value (e.g. "rate_limit", "not_found", "no_doi_references",
        "unsupported_prefix:...") indicates a stub payload with zero citations.
    """
    when = fetch_date or datetime.now(timezone.utc)
    backend = backend or OpenCiteBackend()

    if dataset_id.startswith("nm"):
        source: Any = nemar_source or NemarMetadataSource(github_token=github_token)
    elif dataset_id.startswith("ds"):
        source = bids_source or BidsMetadataSource(github_token=github_token)
    else:
        return _stub_payload(
            dataset_id, when, fetch_status=f"unsupported_prefix:{dataset_id[:2]}"
        )

    refs_result = source.get_doi_references(dataset_id)
    if not isinstance(refs_result, FetchSuccess):
        logger.warning(
            "source lookup for %s failed: %s (%s)",
            dataset_id,
            refs_result.reason,
            refs_result.detail,
        )
        return _stub_payload(dataset_id, when, fetch_status=refs_result.reason)

    refs: list[DoiReference] = refs_result.value
    if not refs:
        return _stub_payload(dataset_id, when, fetch_status="no_doi_references")

    batch = backend.get_citing_works_batch(refs)
    citing_works, per_anchor_errors = _flatten_batch(batch)

    if not citing_works and per_anchor_errors:
        # Every anchor failed; surface the dominant failure reason.
        reason = _dominant_error_reason(per_anchor_errors)
        return _stub_payload(
            dataset_id,
            when,
            fetch_status=reason,
            anchor_count=len(refs),
            anchor_errors=per_anchor_errors,
        )

    citation_details = [_citing_work_to_dict(w) for w in citing_works]
    total_cumulative_citations = sum((w.citation_count or 0) for w in citing_works)

    payload: dict[str, Any] = {
        "dataset_id": dataset_id,
        "num_citations": len(citation_details),
        "date_last_updated": when.isoformat(),
        "metadata": {
            "total_cumulative_citations": int(total_cumulative_citations),
            "fetch_date": when.isoformat(),
            "processing_version": "1.0",
            "schema_version": SCHEMA_VERSION_V2,
            "discovery_backend": "opencite",
            "fetch_status": "success" if not per_anchor_errors else "partial",
            "anchor_count": len(refs),
            "anchor_errors": per_anchor_errors,
        },
        "citation_details": citation_details,
    }
    return add_discovery_provenance(payload, discovery_backend="opencite")


def _flatten_batch(
    batch: dict[str, Any],
) -> tuple[list[CitingWork], dict[str, str]]:
    """Dedupe citing works across anchors; return (works, per-anchor error map)."""
    seen: set[tuple[str, str]] = set()
    works: list[CitingWork] = []
    errors: dict[str, str] = {}
    for anchor_id, result in batch.items():
        if not isinstance(result, FetchSuccess):
            errors[anchor_id] = result.reason
            continue
        for work in result.value:
            key = (
                (work.doi or "").lower(),
                _normalize_title(work.title),
            )
            if key in seen:
                continue
            seen.add(key)
            works.append(work)
    return works, errors


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _citing_work_to_dict(work: CitingWork) -> dict[str, Any]:
    return {
        "title": work.title,
        "author": ", ".join(a.name for a in work.authors) if work.authors else "n/a",
        "venue": work.venue or "n/a",
        "year": work.year or 0,
        "url": _doi_to_url(work.doi),
        "cited_by": work.citation_count or 0,
        "abstract": work.abstract,
        "doi": work.doi,
        "pmid": work.pmid,
        "openalex_id": work.openalex_id,
        "source_doi": work.source_doi,
        "source_relation": work.source_relation,
        "discovery_backend": "opencite",
    }


def _doi_to_url(doi: str | None) -> str:
    return f"https://doi.org/{doi}" if doi else "n/a"


def _dominant_error_reason(errors: dict[str, str]) -> str:
    """Return the most common reason in the per-anchor error map."""
    counts: dict[str, int] = {}
    for reason in errors.values():
        counts[reason] = counts.get(reason, 0) + 1
    return max(counts, key=lambda r: counts[r]) if counts else "unknown"


def _stub_payload(
    dataset_id: str,
    when: datetime,
    *,
    fetch_status: str,
    anchor_count: int = 0,
    anchor_errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = {
        "dataset_id": dataset_id,
        "num_citations": 0,
        "date_last_updated": when.isoformat(),
        "metadata": {
            "total_cumulative_citations": 0,
            "fetch_date": when.isoformat(),
            "processing_version": "1.0",
            "schema_version": SCHEMA_VERSION_V2,
            "discovery_backend": "opencite",
            "fetch_status": fetch_status,
            "anchor_count": anchor_count,
            "anchor_errors": anchor_errors or {},
        },
        "citation_details": [],
    }
    return add_discovery_provenance(payload, discovery_backend="opencite")
