"""Find papers that mention a dataset accession via OpenAlex full-text search.

Datasets are cited by accession number in running text ("ds002718",
"on005964", "nm000207"), not by DOI (OpenNeuro / NEMAR DOIs aren't indexed in
OpenAlex). OpenAlex's `fulltext.search` filter surfaces those works. This
backend reuses opencite's `OpenAlexClient` + `Config` (no new HTTP client) and
maps each hit to the same citation-detail dict the opencite pipeline emits,
tagged `discovery_method="accession_mention"`. Sync facade over the async
client, mirroring `OpenCiteBackend`. Issue #169.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from opencite.clients.openalex import OpenAlexClient
from opencite.config import Config

logger = logging.getLogger(__name__)


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str | None:
    """Rebuild plain abstract text from OpenAlex's abstract_inverted_index."""
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for i in idxs:
            positions.append((i, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(word for _, word in positions)


def _bare_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    stripped = (
        doi.replace("https://doi.org/", "").replace("http://doi.org/", "").lower()
    )
    return stripped or None


def _short_id(url_id: str | None) -> str | None:
    if not url_id:
        return None
    return url_id.rsplit("/", 1)[-1] or None


def work_to_citation(work: dict[str, Any], matched_accession: str) -> dict[str, Any]:
    """Map a raw OpenAlex work JSON to a citation-detail dict.

    Mirrors `opencite_pipeline._citing_work_to_dict` so accession-mention
    citations are schema-compatible with anchor-based ones, plus the
    `discovery_method` / `matched_accession` tags that mark the dataset bucket.
    """
    authors = [
        a.get("author", {}).get("display_name")
        for a in work.get("authorships", [])
        if a.get("author", {}).get("display_name")
    ]
    source = (work.get("primary_location") or {}).get("source") or {}
    pmid = (work.get("ids") or {}).get("pmid")
    if pmid:
        pmid = pmid.rsplit("/", 1)[-1]
    doi = _bare_doi(work.get("doi"))
    return {
        "title": work.get("title"),
        "author": ", ".join(authors) if authors else "n/a",
        "venue": source.get("display_name") or "n/a",
        "year": work.get("publication_year") or 0,
        "url": f"https://doi.org/{doi}" if doi else (work.get("id") or ""),
        "cited_by": work.get("cited_by_count") or 0,
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "doi": doi,
        "pmid": pmid,
        "openalex_id": _short_id(work.get("id")),
        "source_doi": None,
        "source_relation": None,
        "discovery_backend": "openalex",
        "discovery_method": "accession_mention",
        "matched_accession": matched_accession,
    }


async def _search_term(
    client: OpenAlexClient, term: str, max_results: int
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor: str | None = "*"
    per_page = min(max(max_results, 1), 100)
    while cursor and len(out) < max_results:
        resp = await client.get(
            "works",
            params={
                "filter": f"fulltext.search:{term}",
                "per-page": per_page,
                "cursor": cursor,
            },
        )
        data = resp.json()
        for work in data.get("results", []):
            out.append(work_to_citation(work, term))
            if len(out) >= max_results:
                break
        cursor = (data.get("meta") or {}).get("next_cursor")
    return out


class AccessionSearchBackend:
    """Sync facade: search OpenAlex full text for dataset accession mentions."""

    def __init__(self, config: Config | None = None, *, max_results: int = 200) -> None:
        self._config = config or Config.from_env()
        self._max_results = max_results

    def search(self, terms: list[str]) -> list[dict[str, Any]]:
        """Return deduped citation dicts mentioning any of `terms`.

        Dedup is by DOI, then OpenAlex id, then title (lowercased) so a paper
        that mentions both the `on-` and `ds-` accession appears once. Results
        are sorted by a stable key so repeated runs produce identical output
        (content-idempotent writes depend on this). Per-term failures are
        logged and skipped, never fatal.
        """
        if not terms:
            return []
        return asyncio.run(self._search_all(terms))

    async def _search_all(self, terms: list[str]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        async with OpenAlexClient(self._config) as client:
            assert isinstance(client, OpenAlexClient), (
                "opencite changed OpenAlexClient.__aenter__ return type; "
                f"got {type(client).__name__}"
            )
            for term in terms:
                try:
                    hits = await _search_term(client, term, self._max_results)
                except (httpx.HTTPError, asyncio.TimeoutError, OSError) as e:
                    logger.warning("accession search failed for %s: %s", term, e)
                    continue
                for citation in hits:
                    key = (
                        citation.get("doi")
                        or citation.get("openalex_id")
                        or (citation.get("title") or "")
                    ).lower()
                    if key and key not in deduped:
                        deduped[key] = citation
        return sorted(deduped.values(), key=_stable_key)


def _stable_key(citation: dict[str, Any]) -> str:
    return (
        citation.get("doi")
        or citation.get("openalex_id")
        or citation.get("title")
        or ""
    ).lower()
