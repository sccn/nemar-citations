"""Generate temporal analysis data from citation JSON files."""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

# Default confidence threshold; matches the dashboard's high-confidence filter
# (dashboard/components/network_data.py and charts.py).
DEFAULT_CONFIDENCE_THRESHOLD = 0.4
MIN_YEAR = 2000


def _confidence_score(citation: dict) -> float:
    """Per-citation confidence, tolerant of a missing/None scoring block."""
    scoring = citation.get("confidence_scoring") or {}
    return scoring.get("confidence_score") or 0.0


def generate_temporal(
    citations_dir: Path,
    output_dir: Path,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    max_year: int | None = None,
):
    """Generate temporal analysis data from citation data.

    Emits per-year ``total_citations`` (all citations) and
    ``high_confidence_citations`` (confidence_score >= ``confidence_threshold``).
    The high-confidence series is what the dashboard growth chart consumes;
    without it the timeline rendered flat at zero.
    """
    if max_year is None:
        # Allow next-year preprints; the previous hardcoded `< 2025` silently
        # dropped every 2025+ citation.
        max_year = datetime.now(UTC).year + 1

    yearly_citations: dict[int, int] = defaultdict(int)
    yearly_high_conf: dict[int, int] = defaultdict(int)
    yearly_datasets: dict[int, set[str]] = defaultdict(set)

    for json_file in citations_dir.glob("*.json"):
        dataset_id = json_file.stem.replace("_citations", "")

        with open(json_file) as f:
            data = json.load(f)
            citations = data.get("citation_details", [])

            for citation in citations:
                year = citation.get("year", 0)
                if not year or not (MIN_YEAR < year <= max_year):
                    continue
                yearly_citations[year] += 1
                yearly_datasets[year].add(dataset_id)
                if _confidence_score(citation) >= confidence_threshold:
                    yearly_high_conf[year] += 1

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "temporal_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "total_citations",
                "high_confidence_citations",
                "unique_datasets",
            ],
        )
        writer.writeheader()
        for year in sorted(yearly_citations.keys()):
            writer.writerow(
                {
                    "year": year,
                    "total_citations": yearly_citations[year],
                    "high_confidence_citations": yearly_high_conf[year],
                    "unique_datasets": len(yearly_datasets[year]),
                }
            )

    temporal_data = {
        "yearly_citations": dict(yearly_citations),
        "yearly_high_confidence_citations": dict(yearly_high_conf),
        "yearly_datasets": {str(k): len(v) for k, v in yearly_datasets.items()},
        "confidence_threshold": confidence_threshold,
    }

    with open(output_dir / "temporal_analysis.json", "w") as f:
        json.dump(temporal_data, f, indent=2)

    print(f"Generated temporal analysis data: {len(yearly_citations)} years of data")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate temporal analysis data")
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json_opencite"),
        help="Directory containing citation JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dashboard_data/temporal"),
        help="Output directory for temporal analysis",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help="Minimum confidence score for the high_confidence_citations series",
    )

    args = parser.parse_args()

    if not args.citations_dir.exists():
        print(f"Error: Citations directory {args.citations_dir} not found")
        sys.exit(1)

    generate_temporal(
        args.citations_dir,
        args.output_dir,
        confidence_threshold=args.confidence_threshold,
    )


if __name__ == "__main__":
    main()
