"""
CLI for creating interactive network visualizations directly from Neo4j.
"""

import argparse
import logging
from pathlib import Path

from ..graph.network_visualizations import (
    Neo4jNetworkVisualizer,
    create_static_network_graphs,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Main function for the network visualization CLI."""
    parser = argparse.ArgumentParser(
        description="Create interactive network visualizations from Neo4j graph data"
    )
    parser.add_argument(
        "--neo4j-uri",
        default="bolt://localhost:7687",
        help="Neo4j connection URI (default: bolt://localhost:7687)",
    )
    parser.add_argument(
        "--neo4j-username",
        default="neo4j",
        help="Neo4j username (default: neo4j)",
    )
    parser.add_argument(
        "--neo4j-password",
        default="dataset123",
        help="Neo4j password (default: dataset123)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results/network_visualizations",
        help="Directory to save visualizations (default: results/network_visualizations)",
    )
    parser.add_argument(
        "--min-shared-citations",
        type=int,
        default=2,
        help="Minimum shared citations for co-citation network (default: 2)",
    )
    parser.add_argument(
        "--min-datasets-per-author",
        type=int,
        default=5,
        help="Minimum datasets per author for author network (default: 5)",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Create only static network graphs (no Neo4j connection needed)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default="results/network_analysis",
        help="Directory with CSV exports (for static mode)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        logger.info("🌐 Starting network visualization creation...")
        args.output_dir.mkdir(parents=True, exist_ok=True)

        if args.static_only:
            logger.info("📊 Creating static network graphs from CSV data...")
            create_static_network_graphs(args.results_dir, args.output_dir)
        else:
            logger.info("🔗 Connecting to Neo4j for interactive network generation...")

            # Create Neo4j visualizer
            visualizer = Neo4jNetworkVisualizer(
                uri=args.neo4j_uri,
                username=args.neo4j_username,
                password=args.neo4j_password,
            )

            try:
                # Create co-citation network
                logger.info(
                    f"📈 Creating dataset co-citation network (min {args.min_shared_citations} shared citations)..."
                )
                co_citation_output = (
                    args.output_dir / "dataset_co_citation_network.html"
                )
                visualizer.create_interactive_co_citation_network(
                    co_citation_output, min_shared=args.min_shared_citations
                )

                # Create author network
                logger.info(
                    f"👥 Creating author-dataset network (min {args.min_datasets_per_author} datasets per author)..."
                )
                author_output = args.output_dir / "author_dataset_network.html"
                visualizer.create_interactive_author_network(
                    author_output, min_datasets=args.min_datasets_per_author
                )

                # Also create static versions
                logger.info("📊 Creating static network graphs...")
                create_static_network_graphs(args.results_dir, args.output_dir)

            finally:
                visualizer.close()

        logger.info("✅ Network visualization creation completed!")

        if not args.static_only:
            print(f"""
🎉 Interactive Network Visualizations Created!

📁 Output locations:
   🌐 Interactive co-citation network: {args.output_dir}/dataset_co_citation_network.html
   👥 Interactive author network: {args.output_dir}/author_dataset_network.html
   📊 Static network graphs: {args.output_dir}/dataset_co_citation_network.png

🔍 Open the HTML files in your browser for interactive exploration!
   - Hover over nodes for details
   - Zoom and pan to explore
   - Node sizes represent citation counts/influence
            """)
        else:
            print(f"""
🎉 Static Network Visualizations Created!

📁 Output location:
   📊 Static network graph: {args.output_dir}/dataset_co_citation_network.png
            """)

    except Exception as e:
        logger.error(f"❌ Error during network visualization creation: {e}")
        raise


if __name__ == "__main__":
    main()
