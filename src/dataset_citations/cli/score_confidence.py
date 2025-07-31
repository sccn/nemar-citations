#!/usr/bin/env python3
"""
CLI command for calculating citation confidence scores.

This script calculates confidence scores for citations using semantic similarity
between dataset metadata and citation content.

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
import json

# Lazy import to avoid sentence-transformers issues during CLI help

logger = logging.getLogger(__name__)


def get_available_datasets(citations_dir: str, datasets_dir: str) -> List[str]:
    """Find datasets that have both citation and metadata files."""
    available_datasets = []

    if not os.path.exists(citations_dir) or not os.path.exists(datasets_dir):
        return available_datasets

    # Get citation files
    citation_files = [
        f for f in os.listdir(citations_dir) if f.endswith("_citations.json")
    ]

    for citation_file in citation_files:
        dataset_id = citation_file.replace("_citations.json", "")
        metadata_file = f"{dataset_id}_datasets.json"
        metadata_path = os.path.join(datasets_dir, metadata_file)

        if os.path.exists(metadata_path):
            available_datasets.append(dataset_id)
        else:
            logger.warning(f"Missing metadata file for {dataset_id}: {metadata_path}")

    return sorted(available_datasets)


def main():
    """Main function for confidence scoring CLI."""
    parser = argparse.ArgumentParser(
        description="Calculate citation confidence scores using semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Score all available datasets
  dataset-citations-score-confidence --citations-dir citations/json --datasets-dir datasets

  # Score specific datasets
  dataset-citations-score-confidence --dataset-ids ds000117,ds000246 --citations-dir citations/json --datasets-dir datasets

  # Use custom model and save to different directory
  dataset-citations-score-confidence --citations-dir citations/json --datasets-dir datasets --output-dir scored_citations --model Qwen/Qwen3-Embedding-0.6B
        """,
    )

    parser.add_argument(
        "--citations-dir",
        type=str,
        default="citations/json",
        help="Directory containing citation JSON files (default: citations/json)",
    )

    parser.add_argument(
        "--datasets-dir",
        type=str,
        default="datasets",
        help="Directory containing dataset metadata JSON files (default: datasets)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for scored citations (default: overwrite original files)",
    )

    parser.add_argument(
        "--dataset-ids",
        type=str,
        help="Comma-separated list of dataset IDs to score (e.g., ds000117,ds000246)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-Embedding-0.6B",
        help="Sentence transformer model to use (default: Qwen/Qwen3-Embedding-0.6B)",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="mps",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Device to use for sentence transformers ('mps' for Metal GPU on macOS, default: mps)",
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip datasets that already have confidence scores",
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

    # Determine dataset IDs to process
    if args.dataset_ids:
        dataset_ids = [ds.strip() for ds in args.dataset_ids.split(",")]
        logger.info(f"Processing specified dataset IDs: {dataset_ids}")
    else:
        dataset_ids = get_available_datasets(args.citations_dir, args.datasets_dir)
        logger.info(
            f"Found {len(dataset_ids)} datasets with both citation and metadata files"
        )

    if not dataset_ids:
        logger.error("No dataset IDs found to process")
        logger.info("Make sure both citation and metadata files exist for datasets")
        return 1

    # Create output directory if specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    # Process datasets
    successful = 0
    skipped = 0
    failed = 0

    for dataset_id in dataset_ids:
        citation_file = os.path.join(args.citations_dir, f"{dataset_id}_citations.json")
        metadata_file = os.path.join(args.datasets_dir, f"{dataset_id}_datasets.json")

        # Check if files exist
        if not os.path.exists(citation_file):
            logger.error(f"Citation file not found: {citation_file}")
            failed += 1
            continue

        if not os.path.exists(metadata_file):
            logger.error(f"Metadata file not found: {metadata_file}")
            failed += 1
            continue

        # Determine output file
        if args.output_dir:
            output_file = os.path.join(args.output_dir, f"{dataset_id}_citations.json")
        else:
            output_file = citation_file

        # Skip if file already has confidence scores and skip-existing is enabled
        if args.skip_existing:
            try:
                with open(citation_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)

                if "confidence_scoring" in existing_data:
                    logger.info(
                        f"Skipping {dataset_id} - already has confidence scores"
                    )
                    skipped += 1
                    continue

            except Exception as e:
                logger.warning(f"Could not check existing scores for {dataset_id}: {e}")

        try:
            logger.info(f"Scoring citations for {dataset_id}")

            # Score citations (lazy import to avoid sentence-transformers during help)
            from ..quality.confidence_scoring import score_dataset_citations

            score_dataset_citations(
                citation_file, metadata_file, output_file, args.model, args.device
            )

            successful += 1
            logger.info(f"Successfully scored citations for {dataset_id}")

        except Exception as e:
            failed += 1
            logger.error(f"Error scoring citations for {dataset_id}: {e}")

    # Summary
    logger.info("Confidence scoring complete:")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Skipped: {skipped}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total processed: {len(dataset_ids)}")

    if failed > 0:
        logger.warning(f"{failed} datasets had scoring failures")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
