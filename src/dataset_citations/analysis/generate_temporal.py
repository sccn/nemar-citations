#!/usr/bin/env python
"""Generate temporal analysis data from citation JSON files."""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict


def generate_temporal(citations_dir: Path, output_dir: Path):
    """Generate temporal analysis data from citation data."""

    # Initialize data structures
    yearly_citations = defaultdict(int)
    yearly_datasets = defaultdict(set)

    # Process all citation files
    for json_file in citations_dir.glob("*.json"):
        dataset_id = json_file.stem.replace("_citations", "")

        with open(json_file) as f:
            data = json.load(f)
            citations = data.get("citation_details", [])

            for citation in citations:
                year = citation.get("year", 0)
                if year and 2000 < year < 2025:
                    yearly_citations[year] += 1
                    yearly_datasets[year].add(dataset_id)

    # Prepare output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save temporal summary
    with open(output_dir / "temporal_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["year", "total_citations", "unique_datasets"]
        )
        writer.writeheader()
        for year in sorted(yearly_citations.keys()):
            writer.writerow(
                {
                    "year": year,
                    "total_citations": yearly_citations[year],
                    "unique_datasets": len(yearly_datasets[year]),
                }
            )

    # Save as JSON too
    temporal_data = {
        "yearly_citations": dict(yearly_citations),
        "yearly_datasets": {str(k): len(v) for k, v in yearly_datasets.items()},
    }

    with open(output_dir / "temporal_analysis.json", "w") as f:
        json.dump(temporal_data, f, indent=2)

    print(f"Generated temporal analysis data: {len(yearly_citations)} years of data")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate temporal analysis data")
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json"),
        help="Directory containing citation JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dashboard_data/temporal"),
        help="Output directory for temporal analysis",
    )

    args = parser.parse_args()

    if not args.citations_dir.exists():
        print(f"Error: Citations directory {args.citations_dir} not found")
        sys.exit(1)

    generate_temporal(args.citations_dir, args.output_dir)
