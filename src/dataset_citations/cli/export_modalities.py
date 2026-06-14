"""Export per-dataset primary modality to JSON for the dashboard.

The citation JSON carries no modality, so the dashboard's modality breakdown
needs the `api.nemar.org/datasets` catalog (D1), which lists `modalities` per
dataset. This CLI fetches the catalog once and writes a flat id -> primary
recording modality map so the Astro build can render a modality donut without a
runtime catalog fetch.

The map is keyed by BOTH `dataset_id` and `source_id` so ds-*, nm-*, and on-*
citation IDs all resolve (an on-* mirror carries the ds-* source_id).

Writes `dashboard_data/dataset_modalities.json`:
  {"generated_from": "api.nemar.org/datasets",
   "modalities": {"<id>": "eeg", ...}}
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dataset_citations.sources.models import FetchSuccess
from dataset_citations.sources.nemar_catalog import CatalogRow, get_or_fetch_catalog

logger = logging.getLogger(__name__)

# Recording-modality priority: a dataset's primary acquisition technique wins
# over secondary tags (beh / anat / motion / func / mri) when several are listed.
_PRIORITY: tuple[str, ...] = ("ieeg", "meg", "eeg", "emg", "nirs")


def primary_modality(modalities: tuple[str, ...]) -> str:
    """Pick the primary recording modality from a normalized modality tuple.

    Returns the highest-priority recording modality present, else "other"
    (e.g. a dataset tagged only beh/anat).
    """
    present = set(modalities)
    for modality in _PRIORITY:
        if modality in present:
            return modality
    return "other"


def build_modality_map(rows: list[CatalogRow]) -> dict[str, str]:
    """id -> primary modality, keyed by both dataset_id and source_id."""
    mapping: dict[str, str] = {}
    for row in rows:
        modality = primary_modality(row.modalities)
        for key in (row.dataset_id, row.source_id):
            if key:
                mapping[key] = modality
    return mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export per-dataset primary modality (from api.nemar.org/datasets) "
            "to dashboard_data/dataset_modalities.json for the dashboard."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dashboard_data"),
        help="Directory to write dataset_modalities.json into.",
    )
    parser.add_argument(
        "--catalog-file",
        type=Path,
        default=None,
        help=(
            "Path to a cached api.nemar.org/datasets response (shared with "
            "discover/update). Used if fresh; otherwise the catalog is refetched "
            "and this path is written."
        ),
    )
    parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=3600,
        help="Treat the cache as stale beyond this age (default 3600).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    result = get_or_fetch_catalog(
        cache_path=args.catalog_file, max_age_seconds=args.max_age_seconds
    )
    if not isinstance(result, FetchSuccess):
        logger.error("failed to fetch catalog: %s", result)
        return 1

    mapping = build_modality_map(result.value)
    if not mapping:
        logger.error("catalog returned no datasets; refusing to write empty map")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / "dataset_modalities.json"
    out_path.write_text(
        json.dumps(
            {"generated_from": "api.nemar.org/datasets", "modalities": mapping},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    logger.info("wrote %d id->modality entries to %s", len(mapping), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
