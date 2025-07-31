#!/usr/bin/env python3
"""
Extract dataset IDs from previous_citations.csv for batch processing.

This script reads the CSV file and outputs dataset IDs that can be used
with the dataset-citations CLI commands.
"""

import pandas as pd
import argparse


def extract_dataset_ids(
    csv_file: str, min_citations: int = 0, limit: int = None
) -> list:
    """
    Extract dataset IDs from the citations CSV file.

    Args:
        csv_file: Path to the previous_citations.csv file
        min_citations: Minimum number of citations to include
        limit: Maximum number of dataset IDs to return

    Returns:
        List of dataset IDs
    """
    # Read the CSV file
    df = pd.read_csv(csv_file)

    # Filter by minimum citations if specified
    if min_citations > 0:
        df = df[df["number_of_citations"] >= min_citations]

    # Sort by number of citations (descending) to prioritize high-citation datasets
    df = df.sort_values("number_of_citations", ascending=False)

    # Apply limit if specified
    if limit:
        df = df.head(limit)

    # Extract dataset IDs
    dataset_ids = df["dataset_id"].tolist()

    return dataset_ids


def main():
    parser = argparse.ArgumentParser(
        description="Extract dataset IDs from previous_citations.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all dataset IDs
  python extract_dataset_ids.py citations/previous_citations.csv

  # Get dataset IDs with at least 5 citations
  python extract_dataset_ids.py citations/previous_citations.csv --min-citations 5

  # Get top 10 most cited datasets
  python extract_dataset_ids.py citations/previous_citations.csv --limit 10

  # Get comma-separated list for CLI use
  python extract_dataset_ids.py citations/previous_citations.csv --limit 10 --format comma
        """,
    )

    parser.add_argument("csv_file", help="Path to the previous_citations.csv file")
    parser.add_argument(
        "--min-citations",
        type=int,
        default=0,
        help="Minimum number of citations (default: 0)",
    )
    parser.add_argument(
        "--limit", type=int, help="Maximum number of dataset IDs to return"
    )
    parser.add_argument(
        "--format",
        choices=["list", "comma"],
        default="list",
        help="Output format: list (one per line) or comma (comma-separated)",
    )

    args = parser.parse_args()

    # Extract dataset IDs
    dataset_ids = extract_dataset_ids(args.csv_file, args.min_citations, args.limit)

    # Output results
    if args.format == "comma":
        print(",".join(dataset_ids))
    else:
        for dataset_id in dataset_ids:
            print(dataset_id)

    print(f"\n# Found {len(dataset_ids)} dataset IDs", file=sys.stderr)
    if args.min_citations > 0:
        print(f"# With minimum {args.min_citations} citations", file=sys.stderr)


if __name__ == "__main__":
    import sys

    main()
