"""Merge accession-mention citations into a dataset's citation JSON.

Accession-mention citations (papers that name the dataset accession in text)
are discovered by `backends/accession_search.py` and folded into the same
`citation_details[]` list as anchor-based citations, each tagged
`discovery_method="accession_mention"`. The toggle (#169) buckets:
  - "cites dataset"   = accession mentions + anchor citations whose
                        source_relation is IsVersionOf / IsIdenticalTo
  - "cites data paper"= the remaining anchor citations (References /
                        IsDerivedFrom)

This module is pure (no network / I/O) and deterministic so repeated runs are
content-idempotent (issue #165). Issue #169.
"""

from __future__ import annotations

from typing import Any

# source_relation values whose anchor IS the dataset (vs the data paper).
_DATASET_RELATIONS = frozenset({"IsVersionOf", "IsIdenticalTo"})


def _key(citation: dict[str, Any]) -> str:
    """Dedup key: DOI, else OpenAlex id, else title (all lowercased)."""
    for field in ("doi", "openalex_id", "title"):
        value = citation.get(field)
        if value:
            return str(value).strip().lower()
    return ""


def cites_dataset(citation: dict[str, Any]) -> bool:
    """True if `citation` belongs in the 'cites dataset' bucket."""
    if citation.get("discovery_method") == "accession_mention":
        return True
    if citation.get("mentions_accession"):
        return True
    return citation.get("source_relation") in _DATASET_RELATIONS


def merge_accession_mentions(
    citation_json: dict[str, Any],
    mentions: list[dict[str, Any]],
    searched_accessions: list[str],
) -> dict[str, Any]:
    """Fold accession `mentions` into `citation_json` (mutated and returned).

    - A mention whose paper is already a citation flags that existing entry
      (`mentions_accession=True` + `matched_accession`) so a paper that both
      cites the data paper and names the accession lands in BOTH buckets. An
      existing accession-mention entry is left untouched (idempotent).
    - A mention not already present is appended.
    - When new mentions are appended, the stale top-level `confidence_scoring`
      block is dropped so the downstream score step (its `--skip-existing`
      skips files that already carry the block) re-scores the dataset.
    - `num_citations` is recomputed; `metadata` records the searched accessions
      and the per-bucket breakdown.

    All counts derive from the final state (not deltas), so a re-run with the
    same mentions produces byte-identical output.
    """
    details: list[dict[str, Any]] = citation_json.setdefault("citation_details", [])
    by_key: dict[str, dict[str, Any]] = {}
    for citation in details:
        key = _key(citation)
        if key:
            by_key.setdefault(key, citation)

    appended = 0
    for mention in mentions:
        key = _key(mention)
        if not key:
            continue
        existing = by_key.get(key)
        if existing is None:
            details.append(mention)
            by_key[key] = mention
            appended += 1
        elif existing.get("discovery_method") != "accession_mention":
            # Anchor citation that also names the accession -> flag for both
            # buckets (no-op if already flagged, keeping re-runs idempotent).
            existing["mentions_accession"] = True
            existing.setdefault("matched_accession", mention.get("matched_accession"))

    if appended:
        citation_json.pop("confidence_scoring", None)

    citation_json["num_citations"] = len(details)
    meta = citation_json.setdefault("metadata", {})
    meta["searched_accessions"] = list(searched_accessions)
    meta["num_accession_mentions"] = sum(
        1 for c in details if c.get("discovery_method") == "accession_mention"
    )
    meta["num_anchor_citations"] = sum(
        1 for c in details if c.get("discovery_method") != "accession_mention"
    )
    return citation_json
