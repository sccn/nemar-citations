"""
CLI command for temporal analysis of research theme evolution.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import json
import pickle
import numpy as np
from datetime import datetime
from collections import defaultdict, Counter

try:
    import matplotlib.pyplot as plt

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

from ..embeddings.umap_analyzer import UMAPAnalyzer
from ..core.citation_utils import load_citations_from_json


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


class TemporalThemeAnalyzer:
    """
    Analyzer for temporal evolution of research themes.
    """

    def __init__(self, embeddings_dir: Path, citations_dir: Path):
        """Initialize temporal theme analyzer."""
        self.embeddings_dir = embeddings_dir
        self.citations_dir = citations_dir
        self.analyzer = UMAPAnalyzer(embeddings_dir)

    def load_clustering_with_temporal_data(
        self, clustering_file: Optional[Path] = None
    ) -> Dict:
        """
        Load clustering results and augment with temporal information.

        Args:
            clustering_file: Specific clustering file to load

        Returns:
            Clustering results with temporal data
        """
        # Load clustering results
        if clustering_file:
            with open(clustering_file, "rb") as f:
                clustering_results = pickle.load(f)
        else:
            # Find latest clustering results
            clustering_dir = self.embeddings_dir / "analysis" / "clustering"
            if not clustering_dir.exists():
                raise FileNotFoundError(
                    "No clustering results found. Run UMAP analysis first."
                )

            clustering_files = list(clustering_dir.glob("*.pkl"))
            if not clustering_files:
                raise FileNotFoundError(
                    "No clustering results found. Run UMAP analysis first."
                )

            latest_file = max(clustering_files, key=lambda f: f.stat().st_mtime)
            logging.info(f"Loading clustering results from: {latest_file}")

            with open(latest_file, "rb") as f:
                clustering_results = pickle.load(f)

        # Augment with temporal data
        temporal_data = self._extract_temporal_data(clustering_results["embedding_ids"])
        clustering_results["temporal_data"] = temporal_data

        return clustering_results

    def _extract_temporal_data(self, embedding_ids: List[str]) -> Dict:
        """
        Extract temporal information for citations.

        Args:
            embedding_ids: List of embedding IDs

        Returns:
            Dict with temporal information for each embedding
        """
        temporal_data = {}

        # Load all citation files to extract years
        citation_files = list((self.citations_dir / "json").glob("ds*_citations.json"))

        for citation_file in citation_files:
            dataset_id = citation_file.stem.replace("_citations", "")

            try:
                citations_data = load_citations_from_json(citation_file)
                if "citation_details" not in citations_data:
                    continue

                for citation in citations_data["citation_details"]:
                    # Generate citation hash
                    title = citation.get("title", "")
                    abstract = citation.get("abstract", "")
                    citation_text = f"{title} {abstract}".strip()

                    if citation_text:
                        import hashlib

                        citation_hash = hashlib.sha256(
                            citation_text.encode()
                        ).hexdigest()[:8]
                        emb_id = f"citation_{citation_hash}"

                        if emb_id in embedding_ids:
                            # Extract confidence score from nested structure
                            confidence_data = citation.get("confidence_scoring", {})
                            confidence_score = confidence_data.get(
                                "confidence_score", 0.0
                            )

                            temporal_data[emb_id] = {
                                "year": citation.get("year"),
                                "title": title,
                                "dataset_id": dataset_id,
                                "confidence_score": confidence_score,
                                "cited_by": citation.get("cited_by", 0),
                            }

            except Exception as e:
                logging.warning(f"Error processing {citation_file}: {e}")
                continue

        logging.info(f"Extracted temporal data for {len(temporal_data)} citations")
        return temporal_data

    def analyze_theme_evolution(
        self, clustering_results: Dict, year_window: int = 3
    ) -> Dict:
        """
        Analyze how research themes evolve over time.

        Args:
            clustering_results: Clustering results with temporal data
            year_window: Window size for temporal analysis

        Returns:
            Theme evolution analysis results
        """
        logging.info("Analyzing temporal theme evolution...")

        temporal_data = clustering_results["temporal_data"]
        cluster_labels = clustering_results["cluster_labels"]
        embedding_ids = clustering_results["embedding_ids"]

        # Group by cluster and year
        theme_timeline = defaultdict(lambda: defaultdict(list))
        cluster_years = defaultdict(list)

        for i, (emb_id, cluster_id) in enumerate(zip(embedding_ids, cluster_labels)):
            if cluster_id == -1:  # Skip noise
                continue

            if emb_id in temporal_data:
                year = temporal_data[emb_id]["year"]
                if year and isinstance(year, (int, float)) and 1990 <= year <= 2030:
                    theme_timeline[cluster_id][int(year)].append(emb_id)
                    cluster_years[cluster_id].append(int(year))

        # Analyze evolution patterns
        evolution_analysis = {
            "theme_lifespans": {},
            "theme_peaks": {},
            "theme_trends": {},
            "temporal_overlaps": {},
            "emergence_patterns": {},
            "yearly_theme_distribution": defaultdict(lambda: defaultdict(int)),
        }

        for cluster_id in theme_timeline:
            years = sorted(theme_timeline[cluster_id].keys())
            if not years:
                continue

            # Calculate lifespan
            evolution_analysis["theme_lifespans"][cluster_id] = {
                "start_year": min(years),
                "end_year": max(years),
                "duration": max(years) - min(years) + 1,
                "active_years": len(years),
                "total_citations": sum(
                    len(citations) for citations in theme_timeline[cluster_id].values()
                ),
            }

            # Find peak year
            year_counts = {
                year: len(citations)
                for year, citations in theme_timeline[cluster_id].items()
            }
            peak_year = max(year_counts, key=year_counts.get)
            evolution_analysis["theme_peaks"][cluster_id] = {
                "peak_year": peak_year,
                "peak_count": year_counts[peak_year],
                "total_in_peak": year_counts[peak_year],
            }

            # Analyze trend (simple linear)
            if len(years) >= 3:
                trend = self._calculate_trend(year_counts)
                evolution_analysis["theme_trends"][cluster_id] = trend

            # Update yearly distribution
            for year, citations in theme_timeline[cluster_id].items():
                evolution_analysis["yearly_theme_distribution"][year][cluster_id] = len(
                    citations
                )

        # Analyze temporal overlaps between themes
        all_years = set()
        for cluster_years_list in cluster_years.values():
            all_years.update(cluster_years_list)

        for year in sorted(all_years):
            active_themes = []
            for cluster_id in theme_timeline:
                if year in theme_timeline[cluster_id]:
                    active_themes.append(cluster_id)

            if len(active_themes) > 1:
                for i, theme1 in enumerate(active_themes):
                    for theme2 in active_themes[i + 1 :]:
                        pair = tuple(sorted([theme1, theme2]))
                        if pair not in evolution_analysis["temporal_overlaps"]:
                            evolution_analysis["temporal_overlaps"][pair] = []
                        evolution_analysis["temporal_overlaps"][pair].append(year)

        # Identify emergence patterns
        evolution_analysis["emergence_patterns"] = self._identify_emergence_patterns(
            theme_timeline
        )

        return evolution_analysis

    def _calculate_trend(self, year_counts: Dict[int, int]) -> Dict:
        """Calculate simple trend analysis."""
        years = sorted(year_counts.keys())
        counts = [year_counts[year] for year in years]

        if len(years) < 2:
            return {"trend": "insufficient_data"}

        # Simple linear trend
        x = np.array(range(len(years)))
        y = np.array(counts)

        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]

            if slope > 0.5:
                trend_direction = "increasing"
            elif slope < -0.5:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "unknown"

        return {
            "trend": trend_direction,
            "slope": float(slope) if len(x) > 1 else 0,
            "start_count": counts[0],
            "end_count": counts[-1],
            "max_count": max(counts),
            "years_analyzed": len(years),
        }

    def _identify_emergence_patterns(self, theme_timeline: Dict) -> Dict:
        """Identify emergence and decline patterns."""
        patterns = {
            "emerging_themes": [],  # Themes that start after 2015 and show growth
            "declining_themes": [],  # Themes that peak before 2018 and decline
            "persistent_themes": [],  # Themes active for >5 years
            "flash_themes": [],  # Themes active for 1-2 years only
        }

        for cluster_id, yearly_data in theme_timeline.items():
            years = sorted(yearly_data.keys())
            if not years:
                continue

            start_year = min(years)
            end_year = max(years)
            duration = end_year - start_year + 1
            active_years = len(years)

            # Emerging themes (started recently and growing)
            if start_year >= 2015 and active_years >= 2:
                recent_counts = [len(yearly_data[year]) for year in years[-3:]]
                if len(recent_counts) >= 2 and recent_counts[-1] > recent_counts[0]:
                    patterns["emerging_themes"].append(
                        {
                            "cluster_id": cluster_id,
                            "start_year": start_year,
                            "recent_growth": recent_counts[-1] - recent_counts[0],
                        }
                    )

            # Persistent themes
            if duration >= 5 and active_years >= 4:
                patterns["persistent_themes"].append(
                    {
                        "cluster_id": cluster_id,
                        "duration": duration,
                        "active_years": active_years,
                        "start_year": start_year,
                        "end_year": end_year,
                    }
                )

            # Flash themes
            if duration <= 2 and active_years <= 2:
                total_citations = sum(
                    len(citations) for citations in yearly_data.values()
                )
                patterns["flash_themes"].append(
                    {
                        "cluster_id": cluster_id,
                        "duration": duration,
                        "total_citations": total_citations,
                        "years": years,
                    }
                )

            # Declining themes (peak before 2018, declining since)
            year_counts = {
                year: len(citations) for year, citations in yearly_data.items()
            }
            if years and max(year_counts, key=year_counts.get) < 2018:
                recent_years = [year for year in years if year >= 2018]
                if len(recent_years) >= 2:
                    recent_trend = [year_counts[year] for year in recent_years]
                    if len(recent_trend) >= 2 and recent_trend[-1] < recent_trend[0]:
                        patterns["declining_themes"].append(
                            {
                                "cluster_id": cluster_id,
                                "peak_year": max(year_counts, key=year_counts.get),
                                "recent_decline": recent_trend[0] - recent_trend[-1],
                            }
                        )

        return patterns

    def create_temporal_visualizations(
        self, evolution_analysis: Dict, clustering_results: Dict, output_dir: Path
    ) -> List[Path]:
        """
        Create visualizations for temporal theme evolution.

        Args:
            evolution_analysis: Theme evolution analysis results
            clustering_results: Original clustering results
            output_dir: Output directory

        Returns:
            List of created visualization files
        """
        if not PLOTTING_AVAILABLE:
            logging.error("Matplotlib/seaborn not available for plotting")
            return []

        logging.info("Creating temporal theme visualizations...")

        viz_dir = output_dir / "temporal_visualizations"
        viz_dir.mkdir(parents=True, exist_ok=True)

        created_files = []

        # 1. Theme lifespan timeline
        lifespan_file = self._create_lifespan_timeline(
            evolution_analysis["theme_lifespans"], viz_dir / "theme_lifespans.png"
        )
        if lifespan_file:
            created_files.append(lifespan_file)

        # 2. Yearly theme activity heatmap
        heatmap_file = self._create_yearly_heatmap(
            evolution_analysis["yearly_theme_distribution"],
            viz_dir / "yearly_theme_activity.png",
        )
        if heatmap_file:
            created_files.append(heatmap_file)

        # 3. Theme trends plot
        trends_file = self._create_trends_plot(
            evolution_analysis["theme_trends"], viz_dir / "theme_trends.png"
        )
        if trends_file:
            created_files.append(trends_file)

        # 4. Emergence patterns summary
        emergence_file = self._create_emergence_summary(
            evolution_analysis["emergence_patterns"], viz_dir / "emergence_patterns.png"
        )
        if emergence_file:
            created_files.append(emergence_file)

        return created_files

    def _create_lifespan_timeline(
        self, lifespans: Dict, output_file: Path
    ) -> Optional[Path]:
        """Create timeline visualization of theme lifespans."""
        try:
            fig, ax = plt.subplots(figsize=(14, 8))

            themes = list(lifespans.keys())
            y_positions = range(len(themes))

            for i, theme_id in enumerate(themes):
                lifespan = lifespans[theme_id]
                start = lifespan["start_year"]
                end = lifespan["end_year"]
                citations = lifespan["total_citations"]

                # Draw timeline bar
                ax.barh(
                    i,
                    end - start + 1,
                    left=start,
                    height=0.6,
                    alpha=0.7,
                    color=plt.cm.tab10(i % 10),
                )

                # Add citation count annotation
                ax.text(
                    start + (end - start) / 2,
                    i,
                    f"{citations}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                )

            ax.set_yticks(y_positions)
            ax.set_yticklabels([f"Theme {theme_id}" for theme_id in themes])
            ax.set_xlabel("Year")
            ax.set_title("Research Theme Lifespans and Activity")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches="tight")
            plt.close()

            logging.info(f"Created lifespan timeline: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error creating lifespan timeline: {e}")
            return None

    def _create_yearly_heatmap(
        self, yearly_distribution: Dict, output_file: Path
    ) -> Optional[Path]:
        """Create heatmap of yearly theme activity."""
        try:
            # Prepare data for heatmap
            years = sorted(yearly_distribution.keys())
            all_themes = set()
            for year_data in yearly_distribution.values():
                all_themes.update(year_data.keys())

            themes = sorted(all_themes)

            # Create matrix
            matrix = []
            for theme in themes:
                row = []
                for year in years:
                    count = yearly_distribution[year].get(theme, 0)
                    row.append(count)
                matrix.append(row)

            # Create heatmap
            fig, ax = plt.subplots(
                figsize=(max(len(years) * 0.4, 10), max(len(themes) * 0.3, 6))
            )

            im = ax.imshow(matrix, cmap="Blues", aspect="auto")

            # Set ticks and labels
            ax.set_xticks(range(len(years)))
            ax.set_xticklabels(years, rotation=45)
            ax.set_yticks(range(len(themes)))
            ax.set_yticklabels([f"Theme {theme}" for theme in themes])

            # Add colorbar
            plt.colorbar(im, ax=ax, label="Number of Citations")

            # Add text annotations for non-zero values
            for i in range(len(themes)):
                for j in range(len(years)):
                    if matrix[i][j] > 0:
                        ax.text(
                            j,
                            i,
                            str(matrix[i][j]),
                            ha="center",
                            va="center",
                            color="white"
                            if matrix[i][j] > max(max(row) for row in matrix) * 0.5
                            else "black",
                            fontsize=8,
                        )

            ax.set_title("Research Theme Activity Over Time")
            ax.set_xlabel("Year")
            ax.set_ylabel("Research Theme")

            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches="tight")
            plt.close()

            logging.info(f"Created yearly heatmap: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error creating yearly heatmap: {e}")
            return None

    def _create_trends_plot(self, trends: Dict, output_file: Path) -> Optional[Path]:
        """Create plot of theme trends."""
        try:
            if not trends:
                logging.warning("No trend data available for visualization")
                return None

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Plot 1: Trend directions
            trend_counts = Counter(
                trend_data["trend"] for trend_data in trends.values()
            )
            colors = ["green", "red", "blue", "gray"]
            ax1.pie(
                trend_counts.values(),
                labels=trend_counts.keys(),
                autopct="%1.1f%%",
                colors=colors[: len(trend_counts)],
            )
            ax1.set_title("Theme Trend Directions")

            # Plot 2: Slope distribution
            slopes = [trend_data["slope"] for trend_data in trends.values()]
            ax2.hist(slopes, bins=10, alpha=0.7, edgecolor="black")
            ax2.set_xlabel("Trend Slope")
            ax2.set_ylabel("Number of Themes")
            ax2.set_title("Distribution of Theme Trend Slopes")
            ax2.axvline(x=0, color="red", linestyle="--", alpha=0.7, label="No trend")
            ax2.legend()

            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches="tight")
            plt.close()

            logging.info(f"Created trends plot: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error creating trends plot: {e}")
            return None

    def _create_emergence_summary(
        self, emergence_patterns: Dict, output_file: Path
    ) -> Optional[Path]:
        """Create summary visualization of emergence patterns."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

            # Plot 1: Emerging themes
            emerging = emergence_patterns["emerging_themes"]
            if emerging:
                start_years = [theme["start_year"] for theme in emerging]
                ax1.hist(
                    start_years,
                    bins=range(min(start_years), max(start_years) + 2),
                    alpha=0.7,
                    color="green",
                    edgecolor="black",
                )
                ax1.set_title(f"Emerging Themes ({len(emerging)} total)")
                ax1.set_xlabel("Start Year")
                ax1.set_ylabel("Number of Themes")
            else:
                ax1.text(
                    0.5,
                    0.5,
                    "No emerging themes identified",
                    ha="center",
                    va="center",
                    transform=ax1.transAxes,
                )
                ax1.set_title("Emerging Themes")

            # Plot 2: Persistent themes
            persistent = emergence_patterns["persistent_themes"]
            if persistent:
                durations = [theme["duration"] for theme in persistent]
                ax2.hist(durations, bins=10, alpha=0.7, color="blue", edgecolor="black")
                ax2.set_title(f"Persistent Themes ({len(persistent)} total)")
                ax2.set_xlabel("Duration (years)")
                ax2.set_ylabel("Number of Themes")
            else:
                ax2.text(
                    0.5,
                    0.5,
                    "No persistent themes identified",
                    ha="center",
                    va="center",
                    transform=ax2.transAxes,
                )
                ax2.set_title("Persistent Themes")

            # Plot 3: Flash themes
            flash = emergence_patterns["flash_themes"]
            if flash:
                citations = [theme["total_citations"] for theme in flash]
                ax3.hist(
                    citations, bins=10, alpha=0.7, color="orange", edgecolor="black"
                )
                ax3.set_title(f"Flash Themes ({len(flash)} total)")
                ax3.set_xlabel("Total Citations")
                ax3.set_ylabel("Number of Themes")
            else:
                ax3.text(
                    0.5,
                    0.5,
                    "No flash themes identified",
                    ha="center",
                    va="center",
                    transform=ax3.transAxes,
                )
                ax3.set_title("Flash Themes")

            # Plot 4: Pattern summary
            pattern_counts = {
                "Emerging": len(emerging),
                "Persistent": len(persistent),
                "Flash": len(flash),
                "Declining": len(emergence_patterns["declining_themes"]),
            }

            colors = ["green", "blue", "orange", "red"]
            bars = ax4.bar(
                pattern_counts.keys(), pattern_counts.values(), color=colors, alpha=0.7
            )
            ax4.set_title("Theme Pattern Summary")
            ax4.set_ylabel("Number of Themes")

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax4.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{int(height)}",
                        ha="center",
                        va="bottom",
                    )

            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches="tight")
            plt.close()

            logging.info(f"Created emergence summary: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error creating emergence summary: {e}")
            return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze temporal evolution of research themes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic temporal analysis
  dataset-citations-analyze-temporal-themes --embeddings-dir embeddings/ --citations-dir citations/

  # Analysis with custom clustering file
  dataset-citations-analyze-temporal-themes --clustering-file embeddings/analysis/clustering/citations_clusters_dbscan_v1.pkl

  # Create visualizations with custom year window
  dataset-citations-analyze-temporal-themes --create-visualizations --year-window 5

  # Export results for external analysis
  dataset-citations-analyze-temporal-themes --export-results results/temporal_themes/analysis.json
        """,
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default="embeddings",
        help="Path to embeddings directory (default: embeddings)",
    )

    parser.add_argument(
        "--citations-dir",
        type=Path,
        default="citations",
        help="Path to citations directory (default: citations)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results/temporal_themes",
        help="Output directory for results (default: results/temporal_themes)",
    )

    parser.add_argument(
        "--clustering-file",
        type=Path,
        help="Specific clustering results file to use (uses latest if not specified)",
    )

    parser.add_argument(
        "--year-window",
        type=int,
        default=3,
        help="Year window for trend analysis (default: 3)",
    )

    parser.add_argument(
        "--create-visualizations",
        action="store_true",
        help="Create temporal visualization plots",
    )

    parser.add_argument(
        "--export-results", type=Path, help="Export analysis results to JSON file"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Validate inputs
    if not args.embeddings_dir.exists():
        logging.error(f"Embeddings directory not found: {args.embeddings_dir}")
        return 1

    if not args.citations_dir.exists():
        logging.error(f"Citations directory not found: {args.citations_dir}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        logging.info("=" * 60)
        logging.info("TEMPORAL THEME EVOLUTION ANALYSIS")
        logging.info("=" * 60)

        # Initialize analyzer
        analyzer = TemporalThemeAnalyzer(
            embeddings_dir=args.embeddings_dir, citations_dir=args.citations_dir
        )

        # Load clustering with temporal data
        clustering_results = analyzer.load_clustering_with_temporal_data(
            args.clustering_file
        )
        logging.info(
            f"Loaded clustering with {clustering_results['n_clusters']} themes"
        )

        # Analyze theme evolution
        evolution_analysis = analyzer.analyze_theme_evolution(
            clustering_results=clustering_results, year_window=args.year_window
        )

        # Display summary
        print("\n" + "=" * 50)
        print("TEMPORAL EVOLUTION SUMMARY")
        print("=" * 50)

        print("📊 Theme Analysis:")
        print(
            f"   • Total themes analyzed: {len(evolution_analysis['theme_lifespans'])}"
        )
        print(
            f"   • Emerging themes: {len(evolution_analysis['emergence_patterns']['emerging_themes'])}"
        )
        print(
            f"   • Persistent themes: {len(evolution_analysis['emergence_patterns']['persistent_themes'])}"
        )
        print(
            f"   • Flash themes: {len(evolution_analysis['emergence_patterns']['flash_themes'])}"
        )
        print(
            f"   • Declining themes: {len(evolution_analysis['emergence_patterns']['declining_themes'])}"
        )

        # Create visualizations
        created_files = []
        if args.create_visualizations:
            logging.info("=" * 40)
            logging.info("CREATING VISUALIZATIONS")
            logging.info("=" * 40)

            viz_files = analyzer.create_temporal_visualizations(
                evolution_analysis=evolution_analysis,
                clustering_results=clustering_results,
                output_dir=args.output_dir,
            )
            created_files.extend(viz_files)

        # Export results
        if args.export_results:
            args.export_results.parent.mkdir(parents=True, exist_ok=True)

            export_data = {
                "analysis_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "clustering_file": str(args.clustering_file)
                    if args.clustering_file
                    else "latest",
                    "year_window": args.year_window,
                    "total_themes": len(evolution_analysis["theme_lifespans"]),
                },
                "evolution_analysis": evolution_analysis,
                "clustering_summary": {
                    "n_clusters": clustering_results["n_clusters"],
                    "n_noise": clustering_results["n_noise"],
                    "total_embeddings": len(clustering_results["embedding_ids"]),
                },
            }

            with open(args.export_results, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            logging.info(f"Exported results to: {args.export_results}")

        # Final summary
        logging.info("=" * 60)
        logging.info("TEMPORAL ANALYSIS COMPLETE")
        logging.info("=" * 60)
        logging.info(f"Results saved to: {args.output_dir}")
        if created_files:
            logging.info(f"Created {len(created_files)} visualization files")

        return 0

    except Exception as e:
        logging.error(f"Error during temporal analysis: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
