"""CLI command for temporal analysis of dataset citations."""

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from ..graph.temporal import (
    analyze_citation_timeline,
    create_temporal_summary,
    get_dataset_temporal_stats,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def save_results(
    timeline_data: dict,
    summary_df: pd.DataFrame,
    output_dir: Path,
    dataset_id: Optional[str] = None,
) -> None:
    """
    Save temporal analysis results to files.

    Args:
        timeline_data: Full timeline analysis results
        summary_df: Summary DataFrame
        output_dir: Directory to save results
        dataset_id: Optional specific dataset to analyze
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full timeline data as JSON
    timeline_file = output_dir / "temporal_analysis.json"
    with open(timeline_file, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2, default=str)
    logger.info(f"Saved timeline data to {timeline_file}")

    # Save summary as CSV
    if not summary_df.empty:
        summary_file = output_dir / "temporal_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"Saved temporal summary to {summary_file}")

    # Save dataset-specific stats if requested
    if dataset_id:
        dataset_stats = get_dataset_temporal_stats(timeline_data, dataset_id)
        if dataset_stats:
            dataset_file = output_dir / f"{dataset_id}_temporal_stats.json"
            with open(dataset_file, "w", encoding="utf-8") as f:
                json.dump(dataset_stats, f, indent=2, default=str)
            logger.info(f"Saved {dataset_id} stats to {dataset_file}")
        else:
            logger.warning(f"No temporal data found for dataset {dataset_id}")


def print_summary_stats(timeline_data: dict, summary_df: pd.DataFrame) -> None:
    """Print summary statistics to console."""
    print("\n=== TEMPORAL ANALYSIS SUMMARY ===")

    if timeline_data["datasets"]:
        total_datasets = len(timeline_data["datasets"])
        years = sorted(timeline_data["yearly_totals"].keys())
        year_range = f"{min(years)}-{max(years)}" if years else "N/A"

        print(f"Total datasets analyzed: {total_datasets}")
        print(f"Year range: {year_range}")
        print(f"Total citations: {sum(timeline_data['yearly_totals'].values())}")
        print(
            f"High confidence citations: {sum(timeline_data['high_confidence_yearly'].values())}"
        )

        if not summary_df.empty:
            print(
                f"\nPeak citation year: {summary_df.loc[summary_df['total_citations'].idxmax(), 'year']}"
            )
            print(f"Peak citations in a year: {summary_df['total_citations'].max()}")

            # Show top 5 datasets by citation count
            dataset_citations = [
                (dataset_id, data["total_citations"])
                for dataset_id, data in timeline_data["datasets"].items()
            ]
            dataset_citations.sort(key=lambda x: x[1], reverse=True)

            print("\nTop 5 datasets by citation count:")
            for i, (dataset_id, count) in enumerate(dataset_citations[:5], 1):
                print(f"  {i}. {dataset_id}: {count} citations")
    else:
        print("No datasets with valid citation data found.")


def run_temporal_analysis(
    citations_dir: Path,
    output_dir: Path,
    confidence_threshold: float = 0.4,
    dataset_id: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """
    Run temporal analysis on dataset citations.

    Args:
        citations_dir: Directory containing citation JSON files
        output_dir: Directory to save analysis results
        confidence_threshold: Minimum confidence score for citations
        dataset_id: Optional specific dataset to analyze
        verbose: Enable verbose logging
    """
    setup_logging(verbose)

    if not citations_dir.exists():
        raise FileNotFoundError(f"Citations directory not found: {citations_dir}")

    logger.info(f"Starting temporal analysis on {citations_dir}")
    logger.info(f"Confidence threshold: {confidence_threshold}")

    # Run the main analysis
    timeline_data = analyze_citation_timeline(citations_dir, confidence_threshold)

    # Create summary DataFrame
    summary_df = create_temporal_summary(timeline_data)

    # Save results
    save_results(timeline_data, summary_df, output_dir, dataset_id)

    # Print summary to console
    print_summary_stats(timeline_data, summary_df)

    logger.info("Temporal analysis completed successfully")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze temporal patterns in dataset citations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "citations_dir",
        type=Path,
        help="Directory containing citation JSON files (e.g., citations/json/)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("temporal_analysis_results"),
        help="Directory to save analysis results",
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum confidence score for including citations",
    )

    parser.add_argument(
        "--dataset-id", type=str, help="Analyze specific dataset (e.g., ds000117)"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        run_temporal_analysis(
            citations_dir=args.citations_dir,
            output_dir=args.output_dir,
            confidence_threshold=args.confidence_threshold,
            dataset_id=args.dataset_id,
            verbose=args.verbose,
        )
    except Exception as e:
        logger.error(f"Temporal analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
