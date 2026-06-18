"""Derive the accession strings to search for dataset-mention citations.

People rarely cite a dataset's DOI (OpenNeuro / NEMAR DOIs aren't indexed in
OpenAlex); they mention the **accession number** in their methods / data-
availability text, e.g. "ds002718", "on005964", "nm000207". For NEMAR-imported
OpenNeuro datasets the OpenNeuro `ds-` number (carried in the catalog
`source_id`) is the one that actually appears in the literature, so it must be
searched in addition to the `on-` id.

This module is pure: no network, no I/O. The caller feeds the catalog
`dataset_id` + `source_id` and gets back the validated, de-duplicated set of
accession tokens to hand to OpenAlex `fulltext.search`.
"""

from __future__ import annotations

import re

# A well-formed OpenNeuro / NEMAR accession: ds/on/nm followed by exactly six
# digits. Anchoring on this avoids searching free-text noise (a stray "ds1" in
# a paper would match far too much).
_ACCESSION_RE = re.compile(r"^(?:ds|on|nm)\d{6}$")


def accession_search_terms(dataset_id: str, source_id: str | None = None) -> list[str]:
    """Return the validated accession tokens to full-text search for a dataset.

    Includes the dataset's own id and, when present and distinct, its catalog
    `source_id` (the OpenNeuro `ds-` number for `on-*` datasets). Order is
    stable (dataset_id first) and duplicates are removed; malformed inputs are
    dropped rather than searched.

    Args:
        dataset_id: The catalog dataset id (e.g. "on005964", "ds002718").
        source_id: The catalog source id, if any (e.g. "ds005964").

    Returns:
        De-duplicated list of lowercase accession tokens (possibly empty).
    """
    terms: list[str] = []
    for candidate in (dataset_id, source_id):
        if not candidate:
            continue
        token = candidate.strip().lower()
        if _ACCESSION_RE.match(token) and token not in terms:
            terms.append(token)
    return terms
