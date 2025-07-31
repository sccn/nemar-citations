"""
CLI for creating visualizations from network analysis results.
"""

import argparse
import logging
import pandas as pd
from pathlib import Path

from ..graph.visualizations import (
    create_temporal_growth_chart,
    create_citation_impact_dashboard,
    create_author_network_diagram,
    create_dataset_popularity_ranking,
)

logger = logging.getLogger(__name__)


def load_analysis_data(results_dir: Path) -> dict:
    """
    Load all analysis CSV files from results directory.

    Args:
        results_dir: Directory containing CSV analysis results

    Returns:
        Dictionary with loaded DataFrames
    """
    csv_dir = results_dir / "csv_exports"

    data = {}
    csv_files = {
        "temporal": "temporal_network_evolution.csv",
        "impact": "citation_impact_rankings.csv",
        "popularity": "dataset_popularity.csv",
        "authors": "author_influence.csv",
        "multi_dataset": "multi_dataset_citations.csv",
        "co_citations": "dataset_co_citations.csv",
        "bridge_papers": "bridge_papers.csv",
    }

    for key, filename in csv_files.items():
        filepath = csv_dir / filename
        if filepath.exists():
            data[key] = pd.read_csv(filepath)
            logger.info(f"Loaded {key} data: {len(data[key])} records")
        else:
            logger.warning(f"File not found: {filepath}")
            data[key] = pd.DataFrame()

    return data


def create_all_visualizations(
    data: dict, output_base_dir: Path, top_n: int = 15
) -> None:
    """
    Create all visualization types and save to organized directories.

    Args:
        data: Dictionary of loaded DataFrames
        output_base_dir: Base directory for saving visualizations
        top_n: Number of top items to show in rankings
    """

    # 1. Temporal Growth Chart
    if not data["temporal"].empty:
        temporal_dir = output_base_dir / "temporal_analysis"
        create_temporal_growth_chart(
            data["temporal"],
            temporal_dir / "citation_growth_timeline.png",
            title="BIDS Dataset Citation Growth (2007-2025)",
        )

    # 2. Citation Impact Dashboard
    if not data["impact"].empty and not data["popularity"].empty:
        impact_dir = output_base_dir / "impact_analysis"
        create_citation_impact_dashboard(
            data["impact"],
            data["popularity"],
            impact_dir / "citation_impact_dashboard.png",
            top_n=top_n,
        )

    # 3. Author Network Diagram
    if not data["authors"].empty:
        author_dir = output_base_dir / "author_networks"
        create_author_network_diagram(
            data["authors"],
            author_dir / "influential_authors_network.png",
            top_n=min(20, len(data["authors"])),
        )

    # 4. Dataset Popularity Ranking
    if not data["popularity"].empty:
        popularity_dir = output_base_dir / "dataset_popularity"
        create_dataset_popularity_ranking(
            data["popularity"],
            popularity_dir / "dataset_popularity_rankings.png",
            top_n=top_n,
        )

    logger.info(f"All visualizations created and saved to {output_base_dir}")


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Main function for the visualization CLI."""
    parser = argparse.ArgumentParser(
        description="Create visualizations from network analysis results"
    )
    parser.add_argument(
        "results_dir",
        type=Path,
        default="results/network_analysis",
        help="Directory containing analysis CSV results",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results",
        help="Base directory for saving visualizations (default: results)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="Number of top items to show in rankings (default: 15)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        logger.info("🎨 Starting visualization creation...")
        logger.info(f"📊 Loading data from: {args.results_dir}")

        # Load analysis data
        data = load_analysis_data(args.results_dir)

        # Check if we have any data
        if all(df.empty for df in data.values()):
            logger.error("❌ No analysis data found. Run network analysis first.")
            return

        # Create visualizations
        logger.info(f"🎯 Creating visualizations with top-{args.top_n} rankings...")
        create_all_visualizations(data, args.output_dir, args.top_n)

        logger.info("✅ Visualization creation completed!")
        print(f"""
🎉 Visualizations created successfully!

📁 Output locations:
   📈 Temporal analysis: {args.output_dir}/temporal_analysis/
   📊 Impact analysis: {args.output_dir}/impact_analysis/  
   🌐 Author networks: {args.output_dir}/author_networks/
   🏆 Dataset popularity: {args.output_dir}/dataset_popularity/

🔍 Use these for publications, presentations, or further analysis!
        """)

    except Exception as e:
        logger.error(f"❌ Error during visualization creation: {e}")
        raise


if __name__ == "__main__":
    main()
