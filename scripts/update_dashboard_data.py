#!/usr/bin/env python
"""
Update all dashboard data dependencies.

This script ensures all source files needed by the dashboard are properly generated
with the correct parameters (e.g., top 20 citations instead of just 5).
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dataset_citations.graph.neo4j_network_analysis import NetworkAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def update_network_analysis(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    output_dir: Path,
    confidence_threshold: float = 0.4,
) -> None:
    """
    Update network analysis CSV files for the dashboard.

    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        output_dir: Directory to save CSV files
        confidence_threshold: Minimum confidence score for citations
    """
    logger.info("🔄 Updating network analysis data...")

    # Initialize analyzer
    analyzer = NetworkAnalyzer(neo4j_uri, neo4j_user, neo4j_password)

    # Create output directory
    csv_dir = output_dir / "network"
    csv_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Dataset popularity (all datasets)
        logger.info("📊 Analyzing dataset popularity...")
        popularity_df = analyzer.analyze_dataset_popularity_trends()
        popularity_df.to_csv(csv_dir / "dataset_popularity.csv", index=False)

        # 2. Citation impact rankings (TOP 20+ for dashboard modal)
        logger.info("📈 Analyzing citation impact rankings (top 20+)...")
        impact_df = analyzer.analyze_citation_impact_rankings(
            confidence_threshold=confidence_threshold,
            limit=25,  # Get 25 to ensure we have at least 20 good ones
        )
        impact_df.to_csv(csv_dir / "citation_impact_rankings.csv", index=False)

        # 3. Dataset co-citations
        logger.info("🔗 Analyzing dataset co-citations...")
        cocitation_df = analyzer.analyze_dataset_cocitations(min_cooccurrences=2)
        cocitation_df.to_csv(csv_dir / "dataset_co_citations.csv", index=False)

        # 4. Multi-dataset citations (bridge papers)
        logger.info("🌉 Analyzing multi-dataset citations...")
        multi_df = analyzer.analyze_multi_dataset_citations(min_datasets=2)
        multi_df.to_csv(csv_dir / "multi_dataset_citations.csv", index=False)

        # 5. Bridge papers
        logger.info("🌉 Identifying bridge papers...")
        bridge_df = analyzer.identify_bridge_papers(min_datasets=2)
        bridge_df.to_csv(csv_dir / "bridge_papers.csv", index=False)

        # 6. Author influence
        logger.info("👥 Analyzing author influence...")
        overlap_df, influence_df = analyzer.analyze_author_citation_overlap(
            min_citations=5
        )
        influence_df.to_csv(csv_dir / "author_influence.csv", index=False)

        logger.info(f"✅ Network analysis updated in {csv_dir}")

    finally:
        analyzer.close()


def update_temporal_analysis(citations_dir: Path, output_dir: Path) -> None:
    """
    Update temporal analysis data.

    Args:
        citations_dir: Directory containing citation JSON files
        output_dir: Directory to save temporal analysis
    """
    logger.info("📅 Updating temporal analysis...")

    temporal_dir = output_dir / "temporal"
    temporal_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Implement temporal analysis update
    # For now, just ensure the directory exists
    logger.info(f"✅ Temporal analysis directory ready: {temporal_dir}")


def update_theme_analysis(embeddings_dir: Path, output_dir: Path) -> None:
    """
    Update theme analysis data.

    Args:
        embeddings_dir: Directory containing embeddings
        output_dir: Directory to save theme analysis
    """
    logger.info("🎨 Updating theme analysis...")

    themes_dir = output_dir / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    # TODO: Implement theme analysis update
    # For now, just ensure the directory exists
    logger.info(f"✅ Theme analysis directory ready: {themes_dir}")


def verify_dashboard_dependencies(
    dashboard_data_dir: Path, citations_dir: Path
) -> bool:
    """
    Verify all dashboard dependencies are present and valid.

    Args:
        dashboard_data_dir: Directory containing dashboard data
        citations_dir: Directory containing citation JSON files

    Returns:
        True if all dependencies are valid
    """
    logger.info("🔍 Verifying dashboard dependencies...")

    all_valid = True

    # Check network analysis files
    network_files = [
        "dataset_popularity.csv",
        "citation_impact_rankings.csv",
        "dataset_co_citations.csv",
        "multi_dataset_citations.csv",
        "bridge_papers.csv",
        "author_influence.csv",
    ]

    network_dir = dashboard_data_dir / "network"
    for file_name in network_files:
        file_path = network_dir / file_name
        if not file_path.exists():
            logger.error(f"❌ Missing: {file_path}")
            all_valid = False
        else:
            # Check if citation_impact_rankings has enough entries
            if file_name == "citation_impact_rankings.csv":
                import pandas as pd

                df = pd.read_csv(file_path)
                if len(df) < 20:
                    logger.warning(
                        f"⚠️  {file_name} has only {len(df)} entries, should have 20+"
                    )
            logger.info(f"✅ Found: {file_path}")

    # Check citations directory
    if not citations_dir.exists():
        logger.error(f"❌ Citations directory not found: {citations_dir}")
        all_valid = False
    else:
        json_count = len(list(citations_dir.glob("*.json")))
        logger.info(f"✅ Found {json_count} citation JSON files")

    return all_valid


def main():
    parser = argparse.ArgumentParser(
        description="Update all dashboard data dependencies"
    )
    parser.add_argument(
        "--dashboard-data-dir",
        type=Path,
        default=Path("dashboard_data"),
        help="Directory for dashboard data (default: dashboard_data)",
    )
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json"),
        help="Directory containing citation JSON files",
    )
    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j connection URI",
    )
    parser.add_argument(
        "--neo4j-user",
        default="neo4j",
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j-password",
        required=False,
        help="Neo4j password (will prompt if not provided)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum confidence score for citations (default: 0.4)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify dependencies without updating",
    )

    args = parser.parse_args()

    # Verify only mode
    if args.verify_only:
        is_valid = verify_dashboard_dependencies(
            args.dashboard_data_dir, args.citations_dir
        )
        sys.exit(0 if is_valid else 1)

    # Get Neo4j password if not provided
    if not args.neo4j_password:
        import getpass

        args.neo4j_password = getpass.getpass("Neo4j password: ")

    try:
        # Update network analysis
        update_network_analysis(
            args.neo4j_uri,
            args.neo4j_user,
            args.neo4j_password,
            args.dashboard_data_dir,
            args.confidence_threshold,
        )

        # Update temporal analysis
        update_temporal_analysis(args.citations_dir, args.dashboard_data_dir)

        # Update theme analysis
        update_theme_analysis(
            Path("embeddings"),  # Default embeddings directory
            args.dashboard_data_dir,
        )

        # Verify all dependencies
        is_valid = verify_dashboard_dependencies(
            args.dashboard_data_dir, args.citations_dir
        )

        if is_valid:
            logger.info("✅ All dashboard dependencies updated successfully!")
            logger.info("\n📊 Next step: Generate the dashboard with:")
            logger.info(
                f"  python -m dataset_citations.dashboard.core "
                f"--results-dir {args.dashboard_data_dir} "
                f"--citations-dir {args.citations_dir}"
            )
        else:
            logger.warning("⚠️ Some dependencies may be missing or invalid")

    except Exception as e:
        logger.error(f"❌ Error updating dashboard data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
