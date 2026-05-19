"""Phase 3 orchestrator: fetch dataset citations via the opencite backend.

Picks a source extractor by dataset-ID prefix (`nm*` / `on*` -> nemar metadata,
`ds*` -> OpenNeuro BIDS description), resolves DOI/PMID/arXiv references,
optionally seeds the dataset's own catalog DOI as an additional anchor, asks
the opencite backend for citing works, deduplicates them across source
anchors, and returns a citation JSON dict in the schema-v2 shape that
`citation_utils.add_discovery_provenance` produces.

A per-dataset checkpoint store (see `core.checkpoint`) records each anchor's
opencite result the moment it lands. A subsequent run only re-fetches anchors
that hadn't completed successfully, which is what lets a 6h CI window resume
where the previous one timed out.

This module deliberately mirrors the legacy `core/citation_utils.save_citation_json`
output shape so the dashboard aggregator and reporting tools keep working
when reading from `citations/json_opencite/`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, cast

from dataset_citations.backends import OpenCiteBackend
from dataset_citations.core.checkpoint import (
    DEFAULT_CHECKPOINT_DIR,
    CheckpointStore,
)
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
from dataset_citations.sources.doi import (
    is_openneuro_dataset_doi,
    normalize_doi,
    validate_identifier,
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
    catalog_doi: str | None = None,
    checkpoint_store: CheckpointStore | None = None,
    use_checkpoint: bool = False,
) -> dict[str, Any]:
    """Return a schema-v2 citation JSON dict for one dataset.

    Steps:
      1. Pick the source by dataset prefix (`nm` / `on` -> nemar, `ds` -> bids).
      2. Fetch DOI/PMID anchors from the source.
      3. If `catalog_doi` is set, add it as an extra anchor with
         `relation_type=References` and `source=nemar_catalog`.
      4. Dedupe anchors by normalized identifier.
      5. If `use_checkpoint=True`, consult the checkpoint store for any
         anchors already fetched successfully on a previous run; skip them
         in the backend call. (Default is off so unit tests aren't surprised
         by ambient filesystem state; the CLI opts in.)
      6. Ask `OpenCiteBackend.get_citing_works_batch` for the remaining anchors.
      7. Persist each new anchor outcome to the checkpoint as it lands.
      8. Aggregate works across all anchors (checkpointed + freshly fetched),
         dedupe by (normalized DOI || title).
      9. Build the JSON dict with discovery provenance fields. On full
         success the checkpoint file is removed.

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
    store = checkpoint_store or (
        CheckpointStore(base_dir=DEFAULT_CHECKPOINT_DIR) if use_checkpoint else None
    )

    if dataset_id.startswith("nm") or dataset_id.startswith("on"):
        # nm-* = NEMAR-native; on-* = OpenNeuro imported into NEMAR. Both carry
        # .nemar/metadata.json so the same source handles them.
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

    refs: list[DoiReference] = _merge_anchors(refs_result.value, catalog_doi)
    if not refs:
        return _stub_payload(dataset_id, when, fetch_status="no_doi_references")

    pending_refs, checkpointed_works, prior_errors = _split_against_checkpoint(
        refs, store, dataset_id
    )

    batch: dict[str, Any] = {}
    if pending_refs:
        batch = backend.get_citing_works_batch(pending_refs)
        if store is not None:
            for ref in pending_refs:
                outcome = batch.get(ref.identifier)
                if outcome is None:
                    continue
                store.record_anchor(dataset_id, ref.identifier, outcome, when=when)

    citing_works, per_anchor_errors = _flatten_batch(
        batch, prior_works=checkpointed_works, prior_errors=prior_errors
    )

    if not citing_works and per_anchor_errors:
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

    if store is not None and not per_anchor_errors:
        store.clear(dataset_id)

    return add_discovery_provenance(payload, discovery_backend="opencite")


def _merge_anchors(
    source_refs: list[DoiReference], catalog_doi: str | None
) -> list[DoiReference]:
    """Combine source-derived refs with an optional catalog-row DOI.

    Catalog DOI is added with relation_type=References and source=nemar_catalog.
    The result is deduplicated by normalized identifier, preserving the
    source-derived entry when there's a collision (more specific relation type).
    """
    seen: dict[str, DoiReference] = {}
    for ref in source_refs:
        seen.setdefault(ref.identifier, ref)

    if catalog_doi:
        normalized = normalize_doi(catalog_doi)
        if not validate_identifier(normalized):
            logger.warning("ignoring malformed catalog DOI %r", catalog_doi)
        elif is_openneuro_dataset_doi(normalized):
            logger.info(
                "skipping OpenNeuro dataset DOI from catalog (not indexed): %s",
                normalized,
            )
        elif normalized not in seen:
            seen[normalized] = DoiReference(
                identifier=normalized,
                identifier_type="doi",
                relation_type="References",
                source=cast(Any, "nemar_catalog"),
                source_field="catalog_doi",
            )

    return list(seen.values())


def _split_against_checkpoint(
    refs: list[DoiReference],
    store: CheckpointStore | None,
    dataset_id: str,
) -> tuple[list[DoiReference], list[CitingWork], dict[str, str]]:
    """Partition anchors into (to-fetch, already-fetched-works, prior-errors).

    A checkpoint hit with status="success" yields its works directly; any
    other status (or a miss) puts the anchor in the to-fetch bucket.
    """
    if store is None:
        return list(refs), [], {}

    checkpoint = store.load(dataset_id)
    pending: list[DoiReference] = []
    prior_works: list[CitingWork] = []
    prior_errors: dict[str, str] = {}

    for ref in refs:
        if checkpoint.is_success(ref.identifier):
            prior_works.extend(checkpoint.successful_works(ref.identifier))
        else:
            pending.append(ref)

    if prior_works:
        logger.info(
            "resuming %s with %d works from checkpoint across %d anchors",
            dataset_id,
            len(prior_works),
            sum(1 for r in refs if checkpoint.is_success(r.identifier)),
        )

    return pending, prior_works, prior_errors


def _flatten_batch(
    batch: dict[str, Any],
    *,
    prior_works: list[CitingWork] | None = None,
    prior_errors: dict[str, str] | None = None,
) -> tuple[list[CitingWork], dict[str, str]]:
    """Dedupe citing works across all anchors; return (works, per-anchor errors).

    `prior_works` and `prior_errors` carry results from previous checkpoint
    hits and are merged with the fresh batch's outcome.
    """
    seen: set[tuple[str, str]] = set()
    works: list[CitingWork] = []
    errors: dict[str, str] = dict(prior_errors or {})

    for work in prior_works or []:
        key = ((work.doi or "").lower(), _normalize_title(work.title))
        if key in seen:
            continue
        seen.add(key)
        works.append(work)

    for anchor_id, result in batch.items():
        if not isinstance(result, FetchSuccess):
            errors[anchor_id] = result.reason
            continue
        for work in result.value:
            key = ((work.doi or "").lower(), _normalize_title(work.title))
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
