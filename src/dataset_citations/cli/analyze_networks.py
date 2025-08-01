"""CLI command for Neo4j-based multi-dataset citation network analysis."""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from ..graph.neo4j_network_analysis import Neo4jNetworkAnalyzer

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def get_neo4j_credentials() -> tuple[str, str, str]:
    """
    Get Neo4j connection credentials from environment variables.

    Returns:
        Tuple of (uri, username, password)

    Raises:
        ValueError: If required credentials are not found
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError(
            "Neo4j password must be provided via NEO4J_PASSWORD environment variable "
            "or use --neo4j-password argument"
        )

    return uri, username, password


def save_analysis_results(
    multi_dataset_df: pd.DataFrame,
    co_citation_df: pd.DataFrame,
    author_overlap_df: pd.DataFrame,
    author_influence_df: pd.DataFrame,
    impact_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
    bridge_papers_df: pd.DataFrame,
    temporal_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Save Neo4j network analysis results to files.

    Args:
        multi_dataset_df: Multi-dataset citation analysis
        co_citation_df: Dataset co-citation analysis
        author_overlap_df: Author overlap analysis
        author_influence_df: Author influence analysis
        impact_df: Citation impact analysis
        popularity_df: Dataset popularity analysis
        bridge_papers_df: Bridge papers analysis
        temporal_df: Temporal network evolution
        output_dir: Directory to save results
    """
    # Create organized subdirectories
    csv_dir = output_dir / "csv_exports"
    summary_dir = output_dir / "summary_reports"
    csv_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    # Save all analysis DataFrames as CSV in organized structure
    datasets_to_save = [
        (multi_dataset_df, "multi_dataset_citations.csv"),
        (co_citation_df, "dataset_co_citations.csv"),
        (author_overlap_df, "author_overlaps.csv"),
        (author_influence_df, "author_influence.csv"),
        (impact_df, "citation_impact_rankings.csv"),
        (popularity_df, "dataset_popularity.csv"),
        (bridge_papers_df, "bridge_papers.csv"),
        (temporal_df, "temporal_network_evolution.csv"),
    ]

    for df, filename in datasets_to_save:
        if not df.empty:
            df.to_csv(csv_dir / filename, index=False)
            logger.info(f"Saved {filename} with {len(df)} records")

    # Save summary statistics
    import json
    from pathlib import Path

    # Count actual high-confidence citations (≥0.4) across all datasets
    def count_high_confidence_citations(
        citations_dir: Path, confidence_threshold: float = 0.4
    ) -> int:
        """Count total citations with confidence >= threshold."""
        high_confidence_count = 0
        json_files = list(citations_dir.glob("*_citations.json"))

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                citation_details = data.get("citation_details", [])
                for citation in citation_details:
                    confidence_data = citation.get("confidence_scoring", {})
                    confidence = confidence_data.get("confidence_score", 0.0)

                    if confidence >= confidence_threshold:
                        high_confidence_count += 1

            except Exception as e:
                logger.warning(
                    f"Error counting high-confidence citations in {json_file}: {e}"
                )
                continue

        return high_confidence_count

    # Count high-confidence citations from the citations directory
    citations_dir = Path("citations/json")
    if not citations_dir.exists():
        # Try relative path from current working directory
        citations_dir = Path.cwd() / "citations" / "json"

    total_high_confidence_citations = (
        count_high_confidence_citations(citations_dir) if citations_dir.exists() else 0
    )

    summary_stats = {
        "total_multi_dataset_citations": len(multi_dataset_df),
        "total_dataset_pairs_with_shared_citations": len(co_citation_df),
        "total_author_overlaps": len(author_overlap_df),
        "total_influential_authors": len(author_influence_df),
        "total_high_impact_citations": len(impact_df),  # Keep for reference
        "total_high_confidence_citations": total_high_confidence_citations,  # Correct count
        "total_datasets_analyzed": len(popularity_df),
        "total_bridge_papers": len(bridge_papers_df),
        "years_analyzed": len(temporal_df),
        "top_cited_paper": impact_df.iloc[0].to_dict() if not impact_df.empty else None,
        "most_co_cited_datasets": co_citation_df.iloc[0].to_dict()
        if not co_citation_df.empty
        else None,
        "top_bridge_paper": bridge_papers_df.iloc[0].to_dict()
        if not bridge_papers_df.empty
        else None,
    }

    with open(
        summary_dir / "neo4j_network_analysis_summary.json", "w", encoding="utf-8"
    ) as f:
        json.dump(summary_stats, f, indent=2, ensure_ascii=False)

    logger.info(
        "Saved comprehensive summary to summary_reports/neo4j_network_analysis_summary.json"
    )


def print_summary_stats(
    multi_dataset_df: pd.DataFrame,
    co_citation_df: pd.DataFrame,
    author_overlap_df: pd.DataFrame,
    author_influence_df: pd.DataFrame,
    impact_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
    bridge_papers_df: pd.DataFrame,
    temporal_df: pd.DataFrame,
) -> None:
    """Print comprehensive Neo4j network analysis summary to console."""

    print("\n" + "=" * 70)
    print("🚀 NEO4J DATASET CITATION NETWORK ANALYSIS SUMMARY")
    print("=" * 70)

    # Multi-dataset citations (bridge papers)
    print("\n🔗 Multi-Dataset Citations (Bridge Papers):")
    print(f"   • {len(multi_dataset_df)} citations appear across multiple datasets")

    if not multi_dataset_df.empty:
        top_bridge = multi_dataset_df.iloc[0]
        max_datasets = multi_dataset_df["num_datasets_cited"].max()
        print(f"   • Maximum datasets cited by single paper: {max_datasets}")
        print(f"   • Top bridge paper: {top_bridge['citation_title'][:80]}...")
        print(
            f"     └─ Author: {top_bridge['citation_author']}, Impact: {top_bridge['citation_impact']:,} citations"
        )

    # Co-citation analysis
    print("\n🤝 Dataset Co-Citations:")
    print(f"   • {len(co_citation_df)} dataset pairs share high-confidence citations")

    if not co_citation_df.empty:
        top_pair = co_citation_df.iloc[0]
        print(
            f"   • Most co-cited pair: {top_pair['dataset1']} ↔ {top_pair['dataset2']}"
        )
        print(f"     └─ {top_pair['shared_citations']} shared citations")

    # Author networks
    print("\n👥 Author Collaboration Networks:")
    print(
        f"   • {len(author_overlap_df)} direct overlaps (dataset creators who also appear in citations)"
    )
    print(
        f"   • {len(author_influence_df)} influential authors citing multiple datasets"
    )

    if not author_influence_df.empty:
        top_author = author_influence_df.iloc[0]
        print(f"   • Most connected author: {top_author['author']}")
        print(
            f"     └─ Cites {top_author['num_datasets_cited']} datasets with {top_author['total_citation_impact']:,} total impact"
        )

    # Citation impact rankings
    print("\n📈 Citation Impact Analysis:")
    print(f"   • {len(impact_df)} high-confidence citations analyzed")

    if not impact_df.empty:
        top_citation = impact_df.iloc[0]
        total_impact = impact_df["citation_impact"].sum()
        avg_impact = impact_df["citation_impact"].mean()
        print(f"   • Most cited paper: {top_citation['citation_impact']:,} citations")
        print(f"     └─ {top_citation['citation_title'][:80]}...")
        print(f"   • Total citation impact: {total_impact:,} citations")
        print(f"   • Average citation impact: {avg_impact:.1f} citations per paper")

    # Dataset popularity
    print("\n📊 Dataset Popularity:")
    print(f"   • {len(popularity_df)} datasets analyzed")

    if not popularity_df.empty:
        top_dataset = popularity_df.iloc[0]
        total_datasets_with_citations = len(
            popularity_df[popularity_df["high_confidence_citations"] > 0]
        )
        print(
            f"   • Most popular dataset: {top_dataset['dataset_id']} ({top_dataset['cumulative_citations']:,} cumulative citations)"
        )
        print(
            f"   • Datasets with high-confidence citations: {total_datasets_with_citations}/{len(popularity_df)}"
        )

    # Bridge papers detailed
    print("\n🌉 Research Bridge Analysis:")
    print(f"   • {len(bridge_papers_df)} papers bridge multiple datasets")

    if not bridge_papers_df.empty:
        cross_discipline = len(
            bridge_papers_df[bridge_papers_df["num_data_types_bridged"] > 1]
        )
        print(
            f"   • Cross-disciplinary bridges: {cross_discipline} papers span multiple data types"
        )

    # Temporal evolution
    print("\n⏱️ Temporal Network Evolution:")
    print(f"   • {len(temporal_df)} years analyzed")

    if not temporal_df.empty:
        recent_years = temporal_df[temporal_df["year"] >= 2020]
        if not recent_years.empty:
            avg_recent_citations = recent_years["citations_count"].mean()
            print(
                f"   • Average citations per year (2020+): {avg_recent_citations:.1f}"
            )

    print("\n" + "=" * 70)


def main() -> None:
    """Main CLI function for Neo4j-based network analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze multi-dataset citation networks using Neo4j graph database"
    )
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default="bolt://localhost:7687",
        help="Neo4j database URI (default: bolt://localhost:7687)",
    )
    parser.add_argument(
        "--neo4j-username",
        type=str,
        default="neo4j",
        help="Neo4j username (default: neo4j)",
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        help="Neo4j password (can also use NEO4J_PASSWORD env var)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results/network_analysis",
        help="Directory to save analysis results (default: results/network_analysis)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum confidence score for citations (default: 0.4)",
    )
    parser.add_argument(
        "--limit-results",
        type=int,
        default=100,
        help="Maximum number of impact results to analyze (default: 100)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Get Neo4j credentials
    try:
        if args.neo4j_password:
            neo4j_uri, neo4j_username, neo4j_password = (
                args.neo4j_uri,
                args.neo4j_username,
                args.neo4j_password,
            )
        else:
            neo4j_uri, neo4j_username, neo4j_password = get_neo4j_credentials()
            neo4j_uri = args.neo4j_uri  # Override with command line if provided
            neo4j_username = (
                args.neo4j_username
            )  # Override with command line if provided
    except ValueError as e:
        logger.error(f"Neo4j credentials error: {e}")
        sys.exit(1)

    try:
        # Initialize Neo4j network analyzer
        logger.info(f"Connecting to Neo4j at {neo4j_uri}...")
        with Neo4jNetworkAnalyzer(
            neo4j_uri, neo4j_username, neo4j_password
        ) as analyzer:
            # Multi-dataset citation analysis
            logger.info("🔗 Analyzing multi-dataset citations (bridge papers)...")
            multi_dataset_df = analyzer.find_multi_dataset_citations(
                args.confidence_threshold
            )

            # Co-citation analysis
            logger.info("🤝 Analyzing dataset co-citations...")
            co_citation_df = analyzer.analyze_dataset_co_citations(
                args.confidence_threshold
            )

            # Author network analysis
            logger.info("👥 Analyzing author collaboration networks...")
            author_overlap_df, author_influence_df = (
                analyzer.analyze_author_collaboration_networks(
                    args.confidence_threshold
                )
            )

            # Citation impact analysis
            logger.info("📈 Analyzing citation impact rankings...")
            impact_df = analyzer.analyze_citation_impact_rankings(
                args.confidence_threshold, args.limit_results
            )

            # Dataset popularity analysis
            logger.info("📊 Analyzing dataset popularity trends...")
            popularity_df = analyzer.analyze_dataset_popularity_trends()

            # Bridge papers analysis
            logger.info("🌉 Analyzing research bridge papers...")
            bridge_papers_df = analyzer.find_bridge_papers_and_research_themes(
                args.confidence_threshold
            )

            # Temporal network evolution
            logger.info("⏱️ Analyzing temporal network evolution...")
            temporal_df = analyzer.get_temporal_network_evolution(
                args.confidence_threshold
            )

            # Save results
            logger.info("💾 Saving comprehensive analysis results...")
            save_analysis_results(
                multi_dataset_df,
                co_citation_df,
                author_overlap_df,
                author_influence_df,
                impact_df,
                popularity_df,
                bridge_papers_df,
                temporal_df,
                args.output_dir,
            )

            # Print summary
            print_summary_stats(
                multi_dataset_df,
                co_citation_df,
                author_overlap_df,
                author_influence_df,
                impact_df,
                popularity_df,
                bridge_papers_df,
                temporal_df,
            )

            logger.info(
                f"🎉 Neo4j network analysis complete! Results saved to {args.output_dir}"
            )

    except Exception as e:
        logger.error(f"Error during Neo4j network analysis: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
