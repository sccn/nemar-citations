"""Fetch and parse the api.nemar.org/datasets catalog.

The catalog is the primary discovery source for nm-* and on-* IDs. One
paginated request returns every dataset in the NEMAR D1 catalog with DOI,
modalities, source, and github_repo, which removes the GitHub-pagination
hot path that historically caused rate-limit failures.

Legacy `ds-*` IDs not yet imported into NEMAR are absent from the catalog
and still require GitHub-based discovery (see `cli/discover.py`).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from dataset_citations.sources.models import FetchError, FetchResult, FetchSuccess

logger = logging.getLogger(__name__)

CATALOG_URL = "https://api.nemar.org/datasets"
DEFAULT_PAGE_SIZE = 200
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class CatalogRow:
    """One row from `api.nemar.org/datasets`.

    Fields mirror the API shape. `modalities` is normalized to a sorted
    tuple of lowercase strings; everything else is passed through. Optional
    fields reflect catalog nulls observed in real responses (e.g. some
    rows lack `concept_doi` until a DOI is minted).
    """

    dataset_id: str
    doi: str | None
    concept_doi: str | None
    source: str
    source_id: str | None
    github_repo: str
    modalities: tuple[str, ...]
    name: str | None
    visibility: str


def parse_catalog_row(raw: dict[str, Any]) -> CatalogRow:
    """Pure parser for one entry from the catalog `datasets` list.

    Raises KeyError if `dataset_id` is missing; everything else is optional.
    """
    modalities_str = raw.get("modalities") or ""
    modalities = tuple(
        sorted({m.strip().lower() for m in modalities_str.split(",") if m.strip()})
    )
    return CatalogRow(
        dataset_id=raw["dataset_id"],
        doi=raw.get("doi") or None,
        concept_doi=raw.get("concept_doi") or None,
        source=raw.get("source") or "unknown",
        source_id=raw.get("source_id") or None,
        github_repo=raw.get("github_repo") or "",
        modalities=modalities,
        name=raw.get("name") or None,
        visibility=raw.get("visibility") or "public",
    )


def fetch_catalog(
    base_url: str = CATALOG_URL,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> FetchResult[list[CatalogRow]]:
    """Paginate the catalog API until exhausted and return every parsed row.

    Stops when a page returns fewer entries than `page_size` (the API
    convention). Returns `FetchError` on network failure, non-200 status,
    or malformed payload; empty success is shape-legal but not observed
    in production.
    """
    rows: list[CatalogRow] = []
    offset = 0

    while True:
        try:
            response = requests.get(
                base_url,
                params={"limit": page_size, "offset": offset},
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            return FetchError(
                reason="network",
                detail=f"GET {base_url} offset={offset}: {exc}",
            )

        if response.status_code != 200:
            return FetchError(
                reason="other",
                detail=(
                    f"GET {base_url} offset={offset}: "
                    f"HTTP {response.status_code} {response.text[:200]}"
                ),
            )

        try:
            payload = response.json()
        except ValueError as exc:
            return FetchError(
                reason="parse",
                detail=f"json decode at offset={offset}: {exc}",
            )

        page = payload.get("datasets")
        if not isinstance(page, list):
            return FetchError(
                reason="parse",
                detail=(f"expected list at .datasets, got {type(page).__name__}"),
            )

        for raw in page:
            try:
                rows.append(parse_catalog_row(raw))
            except KeyError as exc:
                return FetchError(
                    reason="parse",
                    detail=(
                        f"missing required field {exc} on row "
                        f"{raw.get('dataset_id')!r} at offset={offset}"
                    ),
                )

        count = payload.get("count", len(page))
        total = payload.get("total_count")
        logger.info(
            "catalog page offset=%d count=%d total=%s rows_so_far=%d",
            offset,
            count,
            total,
            len(rows),
        )

        # Terminate on the actual page length rather than the reported count.
        # When `total_count` is an exact multiple of `page_size`, the API
        # serves a full final page and only an extra empty request would
        # signal the end via `count=0`; checking len(page) avoids that
        # wasted round-trip.
        if len(page) < page_size:
            break
        if isinstance(total, int) and len(rows) >= total:
            break
        offset += page_size

    return FetchSuccess(rows)


def filter_by_modality(
    rows: list[CatalogRow], target_modalities: list[str]
) -> list[CatalogRow]:
    """Return rows whose `modalities` intersect `target_modalities`.

    Target modality strings are matched case-insensitively against the
    already-lowercased values in `CatalogRow.modalities`.
    """
    target = {m.lower() for m in target_modalities}
    return [r for r in rows if target.intersection(r.modalities)]


def serialize_row(row: CatalogRow) -> dict[str, Any]:
    """Convert a CatalogRow back to the API-shaped dict for caching.

    The inverse of `parse_catalog_row`. Round-trip property is asserted in
    the test suite.
    """
    return {
        "dataset_id": row.dataset_id,
        "doi": row.doi,
        "concept_doi": row.concept_doi,
        "source": row.source,
        "source_id": row.source_id,
        "github_repo": row.github_repo,
        "modalities": ",".join(row.modalities),
        "name": row.name,
        "visibility": row.visibility,
    }


def load_cached_catalog(
    cache_path: Path, max_age_seconds: int = 3600
) -> list[CatalogRow] | None:
    """Read a cached catalog from disk if it exists and is fresh.

    Returns None on miss, stale cache, unreadable file, or any parse
    failure. Callers should refetch on None.
    """
    if not cache_path.is_file():
        return None
    age = time.time() - cache_path.stat().st_mtime
    if age > max_age_seconds:
        logger.info(
            "catalog cache stale (%.0fs > %ds), refetching", age, max_age_seconds
        )
        return None
    try:
        payload = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("cached catalog unreadable, refetching: %s", exc)
        return None
    if not isinstance(payload, list):
        logger.warning("cached catalog has unexpected shape; refetching")
        return None
    try:
        return [parse_catalog_row(r) for r in payload]
    except (KeyError, TypeError) as exc:
        logger.warning("cached catalog rows malformed, refetching: %s", exc)
        return None


def save_catalog_cache(cache_path: Path, rows: list[CatalogRow]) -> None:
    """Persist parsed rows to disk in the same shape `parse_catalog_row` reads."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps([serialize_row(r) for r in rows], indent=2, ensure_ascii=False)
    )
    logger.info("catalog cached to %s (%d rows)", cache_path, len(rows))


def get_or_fetch_catalog(
    cache_path: Path | None = None,
    max_age_seconds: int = 3600,
    base_url: str = CATALOG_URL,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> FetchResult[list[CatalogRow]]:
    """Convenience: return cached rows if fresh, otherwise fetch and cache.

    Pass `cache_path=None` to bypass the cache entirely. Cache errors are
    treated as misses, not fatals: a stale or unreadable cache triggers a
    network fetch rather than an exception.
    """
    if cache_path is not None:
        cached = load_cached_catalog(cache_path, max_age_seconds=max_age_seconds)
        if cached is not None:
            logger.info("loaded %d rows from catalog cache %s", len(cached), cache_path)
            return FetchSuccess(cached)

    result = fetch_catalog(base_url=base_url, page_size=page_size)
    if cache_path is not None and isinstance(result, FetchSuccess):
        try:
            save_catalog_cache(cache_path, result.value)
        except OSError as exc:
            logger.warning("could not write catalog cache %s: %s", cache_path, exc)
    return result
