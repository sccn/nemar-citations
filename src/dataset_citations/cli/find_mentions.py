#!/usr/bin/env python3
"""Find dataset accession-mention citations via OpenAlex and merge them in.

For each dataset that already has a citation JSON, full-text search OpenAlex
for the dataset accession (`ds*`/`on*`/`nm*`, plus the OpenNeuro `ds-` alias
carried in the catalog `source_id`) and fold the matching papers into
`citation_details[]` tagged `discovery_method="accession_mention"`. This
automates the old "search the accession by hand, keep high-confidence hits"
workflow; the downstream score step ranks the merged citations. Issue #169.

Runs after `dataset-citations-update` and before
`dataset-citations-score-confidence` in the hallu cron.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
from pathlib import Path

from dataset_citations.backends.accession_search import AccessionSearchBackend
from dataset_citations.core.accession_mentions import merge_accession_mentions
from dataset_citations.core.citation_utils import write_citation_json_if_changed
from dataset_citations.sources.accession import accession_search_terms
from dataset_citations.sources.models import FetchSuccess
from dataset_citations.sources.nemar_catalog import get_or_fetch_catalog

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _load_source_id_map(
    cache_path: Path | None, max_age_seconds: int
) -> dict[str, str]:
    """Return a {dataset_id: source_id} map for catalog datasets that have one.

    `source_id` is the OpenNeuro `ds-` number for `on-*` datasets, which is the
    accession people actually cite. On catalog failure we log and return {};
    the search then falls back to the dataset id alone.
    """
    result = get_or_fetch_catalog(
        cache_path=cache_path, max_age_seconds=max_age_seconds
    )
    if not isinstance(result, FetchSuccess):
        logger.warning(
            "could not load catalog (%s): %s; searching dataset ids only",
            result.reason,
            result.detail,
        )
        return {}
    return {row.dataset_id: row.source_id for row in result.value if row.source_id}


def _dataset_ids(args: argparse.Namespace, json_dir: str) -> list[str]:
    if args.dataset_list_file:
        with open(args.dataset_list_file, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return sorted(
        os.path.basename(p).removesuffix("_citations.json")
        for p in glob.glob(os.path.join(json_dir, "*_citations.json"))
    )


def run_find_mentions(args: argparse.Namespace) -> None:
    """Merge accession-mention citations into each dataset's citation JSON.

    Raises SystemExit(2) if every processed dataset failed to write.
    """
    json_dir = args.citations_dir
    source_ids = _load_source_id_map(args.catalog_cache, args.catalog_cache_max_age)
    backend = AccessionSearchBackend(max_results=args.max_results)

    dataset_ids = _dataset_ids(args, json_dir)
    logger.info("searching accession mentions for %d dataset(s)", len(dataset_ids))

    processed = 0
    updated = 0
    no_terms = 0
    missing = 0
    write_failures = 0
    total_mentions = 0
    for dataset_id in dataset_ids:
        filepath = os.path.join(json_dir, f"{dataset_id}_citations.json")
        if not os.path.isfile(filepath):
            missing += 1
            continue
        terms = accession_search_terms(dataset_id, source_ids.get(dataset_id))
        if not terms:
            no_terms += 1
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                citation_json = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("%s: could not read (%s); skipping", dataset_id, e)
            continue
        processed += 1
        mentions = backend.search(terms)
        total_mentions += len(mentions)
        merged = merge_accession_mentions(citation_json, mentions, terms)
        try:
            if write_citation_json_if_changed(filepath, merged):
                updated += 1
        except OSError as e:
            logger.error("Failed to write %s: %s", filepath, e)
            write_failures += 1
            continue
        logger.info(
            "%s: %d mention(s) for %s", dataset_id, len(mentions), ",".join(terms)
        )

    logger.info(
        "accession-mention run complete: %d processed, %d updated, %d mentions found, "
        "%d no-terms, %d missing-json, %d write failures.",
        processed,
        updated,
        total_mentions,
        no_terms,
        missing,
        write_failures,
    )
    if processed and write_failures == processed:
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Find dataset accession-mention citations via OpenAlex full-text "
            "search and merge them into the per-dataset citation JSON."
        ),
    )
    parser.add_argument(
        "--citations-dir",
        default="citations/json_opencite",
        help="Directory of <id>_citations.json files (default: citations/json_opencite).",
    )
    parser.add_argument(
        "--dataset-list-file",
        default=None,
        help="Optional file of dataset IDs (one per line). Defaults to all JSONs in --citations-dir.",
    )
    parser.add_argument(
        "--catalog-cache",
        type=Path,
        default=Path.home() / ".cache" / "dataset_citations" / "catalog.json",
        help="Cached api.nemar.org/datasets response (for the on-* -> ds-* alias).",
    )
    parser.add_argument(
        "--catalog-cache-max-age",
        type=int,
        default=3600,
        help="Seconds before the catalog cache is considered stale (default: 3600).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="Max OpenAlex works to pull per accession term (default: 200).",
    )
    args = parser.parse_args()
    run_find_mentions(args)


if __name__ == "__main__":
    main()
