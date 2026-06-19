#!/usr/bin/env python3
"""Prune ds-* citation JSONs that are now duplicated by an on-* mirror.

When an OpenNeuro `ds-*` dataset is imported into NEMAR it gains an `on-*`
catalog id (the `ds-*` accession survives only as the on-* row's `source_id`),
and `dataset-citations-discover --source catalog` then emits only the `on-*`.
A `ds<N>_citations.json` produced before the mirror existed lingers on disk and
double-counts (every downstream glob counts both files). This CLI removes those
stale ds-* duplicates, keeping the canonical on-* record.

Runs in the hallu cron after `update` and before `find-mentions` so the stale
ds-* is gone before the downstream steps glob it. Idempotent: a second run with
nothing left to prune is a no-op. Epic #180 phase 4, issue #126.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dataset_citations.core.ds_on_dedup import (
    ds_to_on_mirror_map,
    find_mirrored_duplicates,
)
from dataset_citations.sources.models import FetchSuccess
from dataset_citations.sources.nemar_catalog import get_or_fetch_catalog

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_prune_mirrored(args: argparse.Namespace) -> None:
    """Remove ds-* citation files superseded by an on-* mirror.

    Loads the catalog to build the {ds-alias: on-id} mirror map. On a catalog
    failure it prunes nothing and returns normally: pruning is cleanup, not a
    critical step, and deleting without a confirmed mirror map would risk
    dropping a non-duplicated ds-* record.
    """
    citations_dir = Path(args.citations_dir)
    result = get_or_fetch_catalog(
        cache_path=args.catalog_cache, max_age_seconds=args.catalog_cache_max_age
    )
    if not isinstance(result, FetchSuccess):
        logger.warning(
            "could not load catalog (%s): %s; pruning nothing",
            result.reason,
            result.detail,
        )
        return

    ds_to_on = ds_to_on_mirror_map(result.value)
    duplicates = find_mirrored_duplicates(citations_dir, ds_to_on)
    if not duplicates:
        logger.info("no mirrored ds-* duplicates to prune in %s", citations_dir)
        return

    pruned = 0
    for path in duplicates:
        ds_alias = path.name.removesuffix("_citations.json")
        on_id = ds_to_on[ds_alias]
        if args.dry_run:
            logger.info("[dry-run] would prune %s (mirrored by %s)", path.name, on_id)
            continue
        try:
            path.unlink()
        except OSError as e:
            logger.error("failed to prune %s: %s", path, e)
            continue
        pruned += 1
        logger.info("pruned %s (duplicate of %s)", path.name, on_id)

    if args.dry_run:
        logger.info(
            "prune-mirrored dry-run: %d mirrored ds-* duplicate(s) in %s",
            len(duplicates),
            citations_dir,
        )
    else:
        logger.info(
            "prune-mirrored complete: pruned %d of %d duplicate(s) in %s",
            pruned,
            len(duplicates),
            citations_dir,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prune ds-* citation JSONs that are now duplicated by an on-* mirror "
            "(the on-* catalog row's source_id is the ds-* accession). Keeps the "
            "canonical on-* record; only removes a ds-* file when its on-* mirror "
            "file is also present."
        ),
    )
    parser.add_argument(
        "--citations-dir",
        default="citations/json_opencite",
        help="Directory of <id>_citations.json files (default: citations/json_opencite).",
    )
    parser.add_argument(
        "--catalog-cache",
        type=Path,
        default=Path.home() / ".cache" / "dataset_citations" / "catalog.json",
        help="Cached api.nemar.org/datasets response (for the on-* -> ds-* mirror map).",
    )
    parser.add_argument(
        "--catalog-cache-max-age",
        type=int,
        default=3600,
        help="Seconds before the catalog cache is considered stale (default: 3600).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the mirrored ds-* duplicates that would be pruned, delete nothing.",
    )
    args = parser.parse_args()
    run_prune_mirrored(args)


if __name__ == "__main__":
    main()
