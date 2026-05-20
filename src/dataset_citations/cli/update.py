#!/usr/bin/env python3
"""Update citation lists for the datasets in a dataset-IDs file.

Runs the opencite-backed citation discovery pipeline against each dataset
listed in the input file and writes a citation JSON per dataset to
`<output-dir>/json_opencite/<id>_citations.json`.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dataset_citations.backends import OpenCiteBackend
from dataset_citations.core.opencite_pipeline import (
    fetch_dataset_citations_via_opencite,
)
from dataset_citations.sources.doi import normalize_doi
from dataset_citations.sources.models import FetchSuccess
from dataset_citations.sources.nemar_catalog import get_or_fetch_catalog

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _is_fresh_success(filepath: str, max_age_seconds: int) -> bool:
    """Return True if `filepath` is a successful, recent citation JSON.

    Used by run_opencite_backend to skip datasets that were already
    successfully fetched within the freshness window (typically the
    weekly cron cadence). A JSON that doesn't parse, doesn't have a
    success fetch_status, or has a stale date_last_updated triggers
    a re-fetch.

    Robust against missing fields and unparseable timestamps: any
    failure to determine freshness returns False (refetch).
    """
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return False
    if metadata.get("fetch_status") != "success":
        return False
    raw_date = payload.get("date_last_updated")
    if not isinstance(raw_date, str):
        return False
    try:
        fetched_at = datetime.fromisoformat(raw_date)
    except ValueError:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - fetched_at
    return age <= timedelta(seconds=max_age_seconds)


def _load_catalog_doi_map(
    cache_path: Path | None, max_age_seconds: int
) -> dict[str, str]:
    """Return a {dataset_id: catalog_doi} map for catalog-indexed datasets.

    The catalog is fetched from `api.nemar.org/datasets` (or reused from the
    shared cache populated by the discover step earlier in the same workflow
    run). DOIs are run through `normalize_doi` (lowercased + prefix-stripped)
    so the map values match what the pipeline's `_merge_anchors` produces
    when deduping anchors. Empty / missing entries are omitted: a missing
    catalog DOI is not an error; the pipeline simply doesn't seed an extra
    anchor for that dataset.

    On fetch failure we log and return an empty map rather than aborting:
    the rest of the pipeline still produces citation JSON from the source-
    derived anchors. The catalog DOI is purely additive.
    """
    result = get_or_fetch_catalog(
        cache_path=cache_path, max_age_seconds=max_age_seconds
    )
    if not isinstance(result, FetchSuccess):
        logger.warning(
            "could not load catalog (%s): %s; proceeding without catalog DOIs",
            result.reason,
            result.detail,
        )
        return {}
    return {row.dataset_id: normalize_doi(row.doi) for row in result.value if row.doi}


def run_opencite_backend(args: argparse.Namespace) -> None:
    """Run the opencite pipeline against each dataset in the input list.

    Writes results to `<output-dir>/json_opencite/<id>_citations.json`.
    Returns normally on success or partial-success. Raises non-zero
    `SystemExit` so automation (cron / CI) can detect degraded runs:
      - exit 2 when every single dataset failed to write (disk full, read-only).
      - exit 3 when zero datasets returned citing works AND every empty
        result was an API failure (rate_limit, auth, network, etc.). A run
        where datasets legitimately lack DOIs (`no_doi_references`) is
        considered success and does NOT trigger this.
    """
    json_dir = os.path.join(args.output_dir, "json_opencite")
    os.makedirs(json_dir, exist_ok=True)

    with open(args.dataset_list_file, encoding="utf-8") as f:
        dataset_ids = [line.strip() for line in f if line.strip()]

    # OPENCITE_CONCURRENCY caps the anchor fan-out inside one dataset. The CI
    # workflow sets it to 1 to avoid Semantic Scholar 429s when canonical
    # anchor papers are shared across datasets (issue #49). Construct ONE
    # backend instance and pass it to every per-dataset call so the
    # CitationExplorer session and rate-limit headers are reused.
    try:
        concurrency = max(1, int(os.environ.get("OPENCITE_CONCURRENCY", "4")))
    except ValueError:
        concurrency = 4
    backend = OpenCiteBackend(concurrency=concurrency)

    # Load the catalog once so each dataset can be seeded with its own
    # NEMAR-minted DOI as an additional opencite anchor. The catalog cache
    # is shared with the discover step in the same workflow run, so this
    # is typically a no-op disk read; the explicit fetch is a safety net
    # for when update.py is invoked outside the workflow.
    catalog_dois = _load_catalog_doi_map(args.catalog_cache, args.catalog_cache_max_age)
    logger.info(
        "Running opencite backend for %d dataset(s) -> %s "
        "(concurrency=%d, catalog rows known=%d)",
        len(dataset_ids),
        json_dir,
        concurrency,
        len(catalog_dois),
    )

    # Statuses that indicate a genuine API failure rather than legitimately
    # absent DOIs. If every dataset stubs out with one of these, we should
    # exit non-zero so automation (cron / CI) can detect a fully-degraded
    # run instead of silently producing a PR full of empty JSONs.
    api_failure_statuses = {
        "rate_limit",
        "auth",
        "network",
        "not_found",
        "parse",
        "other",
    }
    max_age_seconds = args.max_age_days * 86400 if args.max_age_days > 0 else None
    successes = 0
    stub_only = 0
    write_failures = 0
    api_failures = 0
    skipped_fresh = 0
    for dataset_id in dataset_ids:
        filepath = os.path.join(json_dir, f"{dataset_id}_citations.json")
        if max_age_seconds is not None and _is_fresh_success(filepath, max_age_seconds):
            logger.info(
                "%s: skipping (existing JSON is fresh-success within %d days)",
                dataset_id,
                args.max_age_days,
            )
            skipped_fresh += 1
            continue
        payload = fetch_dataset_citations_via_opencite(
            dataset_id,
            backend=backend,
            catalog_doi=catalog_dois.get(dataset_id),
            use_checkpoint=True,
        )
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to write %s: %s", filepath, e)
            write_failures += 1
            continue
        if payload["num_citations"] > 0:
            successes += 1
        else:
            stub_only += 1
            status = payload.get("metadata", {}).get("fetch_status", "empty")
            if status in api_failure_statuses:
                api_failures += 1
            logger.info("%s: 0 citations (status=%s)", dataset_id, status)

    logger.info(
        "opencite run complete: %d with citations, %d empty/stub "
        "(%d API-failure), %d write failures, %d skipped (fresh), %d total.",
        successes,
        stub_only,
        api_failures,
        write_failures,
        skipped_fresh,
        len(dataset_ids),
    )
    total = len(dataset_ids)
    if total and write_failures == total:
        # Every write failed (disk full, read-only output). Exit 2.
        raise SystemExit(2)
    if total and successes == 0 and api_failures == total:
        # Zero successes and every stub was an API failure (not just a
        # dataset without DOIs). Exit 3 so cron can detect the degraded
        # run before downstream steps regenerate empty CSVs.
        raise SystemExit(3)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Update dataset citations via the opencite pipeline. Anchors on "
            "DOIs surfaced by .nemar/metadata.json (nm datasets) or "
            "dataset_description.json (legacy ds datasets), looks up citing "
            "works via opencite, and writes a JSON per dataset to "
            "<output-dir>/json_opencite/."
        ),
    )
    parser.add_argument(
        "--dataset-list-file",
        required=True,
        help="Path to the file containing the list of dataset IDs (one per line).",
    )
    parser.add_argument(
        "--output-dir",
        default="citations",
        help="Directory to save output files (default: citations/).",
    )
    parser.add_argument(
        "--catalog-cache",
        type=Path,
        default=Path.home() / ".cache" / "dataset_citations" / "catalog.json",
        help=(
            "Path to a cached api.nemar.org/datasets response. Shared with "
            "dataset-citations-discover so the catalog is fetched once per "
            "workflow run."
        ),
    )
    parser.add_argument(
        "--catalog-cache-max-age",
        type=int,
        default=3600,
        help="Seconds before the catalog cache is considered stale (default: 3600).",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help=(
            "Skip datasets whose existing JSON has fetch_status=success and "
            "date_last_updated within this many days (default: 7, matching "
            "the weekly cron cadence). Set to 0 to force re-fetch every "
            "dataset on every invocation."
        ),
    )

    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info("Created output directory: %s", args.output_dir)

    run_opencite_backend(args)


if __name__ == "__main__":
    main()
