"""
CLI command for UMAP analysis and research theme identification.
"""

import argparse
import logging
from pathlib import Path
import time
import json

from ..embeddings.umap_analyzer import UMAPAnalyzer


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def run_umap_analysis(
    embeddings_dir: Path,
    output_dir: Path,
    embedding_type: str = "citations",
    n_components: int = 2,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    metric: str = "cosine",
    random_state: int = 42,
) -> dict:
    """
    Run UMAP dimensionality reduction analysis.

    Args:
        embeddings_dir: Path to embeddings directory
        output_dir: Path to save results
        embedding_type: Type of embeddings to analyze
        n_components: Number of UMAP dimensions
        n_neighbors: UMAP n_neighbors parameter
        min_dist: UMAP min_dist parameter
        metric: Distance metric
        random_state: Random seed

    Returns:
        UMAP analysis results
    """
    logging.info(f"Running UMAP analysis on {embedding_type} embeddings")

    # Initialize analyzer
    analyzer = UMAPAnalyzer(embeddings_dir)

    # Run UMAP analysis
    umap_results = analyzer.run_umap_analysis(
        embedding_type=embedding_type,
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
        save_results=True,
    )

    logging.info(
        f"UMAP analysis complete: {umap_results['n_samples']} embeddings processed"
    )
    logging.info(f"Output shape: {umap_results['umap_embeddings'].shape}")

    return umap_results


def run_clustering_analysis(
    analyzer: UMAPAnalyzer,
    umap_results: dict,
    output_dir: Path,
    method: str = "dbscan",
    **clustering_kwargs,
) -> dict:
    """
    Run clustering analysis on UMAP results.

    Args:
        analyzer: UMAPAnalyzer instance
        umap_results: Results from UMAP analysis
        output_dir: Path to save results
        method: Clustering method
        **clustering_kwargs: Clustering parameters

    Returns:
        Clustering analysis results
    """
    logging.info(f"Running {method} clustering analysis")

    # Run clustering
    clustering_results = analyzer.cluster_umap_embeddings(
        umap_results=umap_results, method=method, save_results=True, **clustering_kwargs
    )

    logging.info(
        f"Clustering complete: {clustering_results['n_clusters']} clusters found"
    )
    logging.info(f"Noise points: {clustering_results['n_noise']}")
    if clustering_results["silhouette_score"]:
        logging.info(f"Silhouette score: {clustering_results['silhouette_score']:.3f}")

    return clustering_results


def create_theme_visualizations(
    analyzer: UMAPAnalyzer, clustering_results: dict, output_dir: Path
) -> dict:
    """
    Create visualizations for research themes.

    Args:
        analyzer: UMAPAnalyzer instance
        clustering_results: Clustering results
        output_dir: Output directory

    Returns:
        Dict of created visualization files
    """
    logging.info("Creating theme visualizations")

    # Create visualizations
    viz_files = analyzer.create_research_theme_visualization(
        clustering_results=clustering_results, output_dir=output_dir, create_plots=True
    )

    for viz_type, file_path in viz_files.items():
        logging.info(f"Created {viz_type}: {file_path}")

    return viz_files


def generate_theme_summary(clustering_results: dict, output_dir: Path) -> Path:
    """
    Generate a comprehensive theme analysis summary.

    Args:
        clustering_results: Clustering results
        output_dir: Output directory

    Returns:
        Path to summary file
    """
    logging.info("Generating comprehensive theme summary")

    # Prepare summary data
    summary = {
        "analysis_overview": {
            "total_items": len(clustering_results["embedding_ids"]),
            "n_clusters": clustering_results["n_clusters"],
            "n_noise": clustering_results["n_noise"],
            "clustering_method": clustering_results["method"],
            "silhouette_score": clustering_results["silhouette_score"],
            "created": clustering_results["created"],
        },
        "cluster_details": clustering_results["cluster_analysis"],
        "research_insights": generate_research_insights(clustering_results),
        "recommendations": generate_recommendations(clustering_results),
    }

    # Save summary
    summary_file = output_dir / "comprehensive_theme_analysis.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logging.info(f"Saved comprehensive summary to: {summary_file}")
    return summary_file


def generate_research_insights(clustering_results: dict) -> dict:
    """Generate research insights from clustering results."""
    cluster_analysis = clustering_results["cluster_analysis"]

    insights = {
        "cluster_distribution": {
            "largest_cluster": None,
            "smallest_cluster": None,
            "average_cluster_size": 0,
            "cluster_size_variance": 0,
        },
        "research_patterns": {
            "well_defined_themes": 0,
            "emerging_themes": 0,
            "noise_ratio": clustering_results["n_noise"]
            / len(clustering_results["embedding_ids"]),
        },
    }

    # Analyze cluster sizes (excluding noise)
    cluster_sizes = []
    largest_size = 0
    smallest_size = float("inf")

    for cluster_name, analysis in cluster_analysis.items():
        if cluster_name != "noise":
            size = analysis["size"]
            cluster_sizes.append(size)

            if size > largest_size:
                largest_size = size
                insights["cluster_distribution"]["largest_cluster"] = {
                    "name": cluster_name,
                    "size": size,
                    "percentage": analysis["percentage"],
                }

            if size < smallest_size:
                smallest_size = size
                insights["cluster_distribution"]["smallest_cluster"] = {
                    "name": cluster_name,
                    "size": size,
                    "percentage": analysis["percentage"],
                }

    if cluster_sizes:
        insights["cluster_distribution"]["average_cluster_size"] = sum(
            cluster_sizes
        ) / len(cluster_sizes)
        if len(cluster_sizes) > 1:
            mean_size = insights["cluster_distribution"]["average_cluster_size"]
            variance = sum((size - mean_size) ** 2 for size in cluster_sizes) / len(
                cluster_sizes
            )
            insights["cluster_distribution"]["cluster_size_variance"] = variance

    # Classify themes
    for cluster_name, analysis in cluster_analysis.items():
        if cluster_name != "noise":
            size = analysis["size"]
            if size >= 10:  # Well-defined themes
                insights["research_patterns"]["well_defined_themes"] += 1
            elif size >= 3:  # Emerging themes
                insights["research_patterns"]["emerging_themes"] += 1

    return insights


def generate_recommendations(clustering_results: dict) -> dict:
    """Generate recommendations based on clustering results."""
    n_clusters = clustering_results["n_clusters"]
    n_noise = clustering_results["n_noise"]
    total_items = len(clustering_results["embedding_ids"])
    noise_ratio = n_noise / total_items

    recommendations = {
        "clustering_quality": {"assessment": "good", "suggestions": []},
        "research_opportunities": [],
        "methodological_suggestions": [],
    }

    # Assess clustering quality
    if noise_ratio > 0.3:
        recommendations["clustering_quality"]["assessment"] = "poor"
        recommendations["clustering_quality"]["suggestions"].append(
            "High noise ratio suggests need for parameter tuning or different clustering method"
        )
    elif noise_ratio > 0.15:
        recommendations["clustering_quality"]["assessment"] = "fair"
        recommendations["clustering_quality"]["suggestions"].append(
            "Moderate noise ratio - consider adjusting clustering parameters"
        )

    if n_clusters < 3:
        recommendations["clustering_quality"]["suggestions"].append(
            "Few clusters found - data may be too homogeneous or parameters too restrictive"
        )
    elif n_clusters > 20:
        recommendations["clustering_quality"]["suggestions"].append(
            "Many clusters found - consider increasing min_samples or eps for DBSCAN"
        )

    # Research opportunities
    if n_clusters >= 5:
        recommendations["research_opportunities"].append(
            "Multiple distinct research themes identified - opportunities for cross-theme collaboration"
        )

    if noise_ratio < 0.1:
        recommendations["research_opportunities"].append(
            "Well-clustered data suggests clear research domains - good for specialization studies"
        )

    # Methodological suggestions
    recommendations["methodological_suggestions"].extend(
        [
            "Consider temporal analysis to track theme evolution over time",
            "Analyze inter-cluster relationships for research bridge identification",
            "Generate word clouds for automatic theme labeling",
            "Cross-reference with author networks for collaboration patterns",
        ]
    )

    return recommendations


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="UMAP analysis and research theme identification for BIDS dataset citations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic UMAP analysis on citations
  dataset-citations-analyze-umap --embeddings-dir embeddings/ --output-dir results/umap_analysis/

  # Analyze datasets with custom UMAP parameters
  dataset-citations-analyze-umap --embedding-type datasets --n-neighbors 25 --min-dist 0.2

  # Run complete analysis with clustering
  dataset-citations-analyze-umap --clustering --clustering-method dbscan --eps 0.3

  # High-dimensional UMAP for detailed analysis
  dataset-citations-analyze-umap --n-components 10 --embedding-type both
        """,
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default="embeddings",
        help="Path to embeddings directory (default: embeddings)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results/umap_analysis",
        help="Output directory for results (default: results/umap_analysis)",
    )

    parser.add_argument(
        "--embedding-type",
        choices=["datasets", "citations", "both"],
        default="citations",
        help="Type of embeddings to analyze (default: citations)",
    )

    # UMAP parameters
    parser.add_argument(
        "--n-components",
        type=int,
        default=2,
        help="Number of UMAP dimensions (default: 2)",
    )

    parser.add_argument(
        "--n-neighbors",
        type=int,
        default=15,
        help="UMAP n_neighbors parameter (default: 15)",
    )

    parser.add_argument(
        "--min-dist",
        type=float,
        default=0.1,
        help="UMAP min_dist parameter (default: 0.1)",
    )

    parser.add_argument(
        "--metric", default="cosine", help="UMAP distance metric (default: cosine)"
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    # Clustering options
    parser.add_argument(
        "--clustering", action="store_true", help="Run clustering analysis after UMAP"
    )

    parser.add_argument(
        "--clustering-method",
        choices=["dbscan", "kmeans"],
        default="dbscan",
        help="Clustering method (default: dbscan)",
    )

    # DBSCAN parameters
    parser.add_argument(
        "--eps", type=float, default=0.5, help="DBSCAN eps parameter (default: 0.5)"
    )

    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="DBSCAN min_samples parameter (default: 5)",
    )

    # KMeans parameters
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=8,
        help="KMeans n_clusters parameter (default: 8)",
    )

    parser.add_argument(
        "--create-visualizations",
        action="store_true",
        help="Create visualization plots",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Validate inputs
    if not args.embeddings_dir.exists():
        logging.error(f"Embeddings directory not found: {args.embeddings_dir}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        logging.info("=" * 60)
        logging.info("UMAP RESEARCH THEME ANALYSIS")
        logging.info("=" * 60)

        # Run UMAP analysis
        umap_results = run_umap_analysis(
            embeddings_dir=args.embeddings_dir,
            output_dir=args.output_dir,
            embedding_type=args.embedding_type,
            n_components=args.n_components,
            n_neighbors=args.n_neighbors,
            min_dist=args.min_dist,
            metric=args.metric,
            random_state=args.random_state,
        )

        # Run clustering if requested
        clustering_results = None
        if args.clustering:
            logging.info("=" * 60)
            logging.info("CLUSTERING ANALYSIS")
            logging.info("=" * 60)

            # Initialize analyzer
            analyzer = UMAPAnalyzer(args.embeddings_dir)

            # Prepare clustering parameters
            clustering_kwargs = {}
            if args.clustering_method == "dbscan":
                clustering_kwargs = {"eps": args.eps, "min_samples": args.min_samples}
            elif args.clustering_method == "kmeans":
                clustering_kwargs = {"n_clusters": args.n_clusters}

            # Run clustering
            clustering_results = run_clustering_analysis(
                analyzer=analyzer,
                umap_results=umap_results,
                output_dir=args.output_dir,
                method=args.clustering_method,
                **clustering_kwargs,
            )

            # Create visualizations if requested
            if args.create_visualizations:
                logging.info("=" * 60)
                logging.info("CREATING VISUALIZATIONS")
                logging.info("=" * 60)

                create_theme_visualizations(
                    analyzer=analyzer,
                    clustering_results=clustering_results,
                    output_dir=args.output_dir,
                )

            # Generate comprehensive summary
            generate_theme_summary(
                clustering_results=clustering_results, output_dir=args.output_dir
            )

        # Final summary
        elapsed_time = time.time() - start_time
        logging.info("=" * 60)
        logging.info("UMAP ANALYSIS COMPLETE")
        logging.info("=" * 60)
        logging.info(f"Processed {umap_results['n_samples']} embeddings")
        if clustering_results:
            logging.info(
                f"Identified {clustering_results['n_clusters']} research themes"
            )
        logging.info(f"Results saved to: {args.output_dir}")
        logging.info(f"Total time: {elapsed_time:.1f} seconds")

        return 0

    except Exception as e:
        logging.error(f"Error during UMAP analysis: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
