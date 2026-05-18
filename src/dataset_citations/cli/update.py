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

from dataset_citations.core.opencite_pipeline import (
    fetch_dataset_citations_via_opencite,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_opencite_backend(args: argparse.Namespace) -> None:
    """Run the opencite pipeline against each dataset in the input list.

    Writes results to `<output-dir>/json_opencite/<id>_citations.json`.
    Returns normally on success or partial-success; raises SystemExit(2) only
    when every single dataset failed to write (e.g. disk full / read-only
    output directory) so automation can detect wholesale failure.
    """
    json_dir = os.path.join(args.output_dir, "json_opencite")
    os.makedirs(json_dir, exist_ok=True)

    with open(args.dataset_list_file, encoding="utf-8") as f:
        dataset_ids = [line.strip() for line in f if line.strip()]

    logger.info(
        "Running opencite backend for %d dataset(s) -> %s",
        len(dataset_ids),
        json_dir,
    )

    successes = 0
    stub_only = 0
    write_failures = 0
    for dataset_id in dataset_ids:
        payload = fetch_dataset_citations_via_opencite(dataset_id)
        filepath = os.path.join(json_dir, f"{dataset_id}_citations.json")
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
            logger.info("%s: 0 citations (status=%s)", dataset_id, status)

    logger.info(
        "opencite run complete: %d with citations, %d empty/stub, "
        "%d write failures, %d total.",
        successes,
        stub_only,
        write_failures,
        len(dataset_ids),
    )
    if write_failures and write_failures == len(dataset_ids):
        raise SystemExit(2)


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

    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info("Created output directory: %s", args.output_dir)

    run_opencite_backend(args)


if __name__ == "__main__":
    main()
