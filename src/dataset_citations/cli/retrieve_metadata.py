#!/usr/bin/env python3
"""
CLI command for retrieving dataset metadata from GitHub.

This script retrieves dataset_description.json and README files from OpenNeuro
GitHub repositories for use in citation confidence scoring.

Copyright (c) 2025 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import os
import argparse
import logging
from typing import List

from ..quality.dataset_metadata import DatasetMetadataRetriever, save_dataset_metadata

logger = logging.getLogger(__name__)


def get_dataset_ids_from_citations_dir(citations_dir: str) -> List[str]:
    """Extract dataset IDs from citation JSON files."""
    dataset_ids = []

    if not os.path.exists(citations_dir):
        logger.error(f"Citations directory not found: {citations_dir}")
        return dataset_ids

    for filename in os.listdir(citations_dir):
        if filename.endswith("_citations.json"):
            dataset_id = filename.replace("_citations.json", "")
            dataset_ids.append(dataset_id)

    return sorted(dataset_ids)


def main():
    """Main function for dataset metadata retrieval CLI."""
    parser = argparse.ArgumentParser(
        description="Retrieve dataset metadata from GitHub for confidence scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Retrieve metadata for all datasets with citation files
  dataset-citations-retrieve-metadata --citations-dir citations/json --output-dir datasets

  # Retrieve metadata for specific datasets
  dataset-citations-retrieve-metadata --dataset-ids ds000117,ds000246 --output-dir datasets

  # Use custom GitHub token
  dataset-citations-retrieve-metadata --citations-dir citations/json --output-dir datasets --github-token $GITHUB_TOKEN
        """,
    )

    parser.add_argument(
        "--citations-dir",
        type=str,
        default="citations/json",
        help="Directory containing citation JSON files (default: citations/json)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="datasets",
        help="Output directory for dataset metadata files (default: datasets)",
    )

    parser.add_argument(
        "--dataset-ids",
        type=str,
        help="Comma-separated list of dataset IDs to retrieve (e.g., ds000117,ds000246)",
    )

    parser.add_argument(
        "--github-token",
        type=str,
        help="GitHub token for API access (uses environment variable GITHUB_TOKEN if not provided)",
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip datasets that already have metadata files",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Get GitHub token
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.warning(
            "No GitHub token provided. Using public API access with rate limits."
        )

    # Determine dataset IDs to process
    if args.dataset_ids:
        dataset_ids = [ds.strip() for ds in args.dataset_ids.split(",")]
        logger.info(f"Processing specified dataset IDs: {dataset_ids}")
    else:
        dataset_ids = get_dataset_ids_from_citations_dir(args.citations_dir)
        logger.info(f"Found {len(dataset_ids)} datasets from citations directory")

    if not dataset_ids:
        logger.error("No dataset IDs found to process")
        return 1

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize metadata retriever
    retriever = DatasetMetadataRetriever(github_token)

    # Process datasets
    successful = 0
    skipped = 0
    failed = 0

    for dataset_id in dataset_ids:
        output_file = os.path.join(args.output_dir, f"{dataset_id}_datasets.json")

        # Skip if file exists and skip-existing is enabled
        if args.skip_existing and os.path.exists(output_file):
            logger.info(f"Skipping {dataset_id} - metadata file already exists")
            skipped += 1
            continue

        try:
            logger.info(f"Retrieving metadata for {dataset_id}")
            metadata = retriever.get_dataset_metadata(dataset_id)

            # Save metadata
            save_dataset_metadata(metadata, args.output_dir)

            # Check if retrieval was successful
            repo_status = metadata.get("retrieval_status", {}).get("repository", "")
            if repo_status == "success":
                successful += 1
                logger.info(f"Successfully retrieved metadata for {dataset_id}")
            else:
                failed += 1
                logger.warning(
                    f"Partial/failed retrieval for {dataset_id}: {repo_status}"
                )

        except Exception as e:
            failed += 1
            logger.error(f"Error retrieving metadata for {dataset_id}: {e}")

    # Summary
    logger.info("Metadata retrieval complete:")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total processed: {len(dataset_ids)}")

    if failed > 0:
        logger.warning(f"{failed} datasets had retrieval failures")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
