"""
UMAP analysis for thematic clustering and dimensionality reduction of embeddings.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Union, Any
from datetime import datetime
import logging
import pickle
import json

try:
    import umap

    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    umap = None

try:
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.metrics import silhouette_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .storage_manager import EmbeddingStorageManager

logger = logging.getLogger(__name__)


class UMAPAnalyzer:
    """
    UMAP-based analysis for research theme identification and visualization.

    Provides:
    - UMAP dimensionality reduction for embeddings
    - Clustering analysis for theme identification
    - Temporal evolution tracking
    - Integration with existing embedding storage
    """

    def __init__(self, embeddings_dir: Union[str, Path]):
        """
        Initialize UMAP analyzer.

        Args:
            embeddings_dir: Path to embeddings directory
        """
        if not UMAP_AVAILABLE:
            raise ImportError(
                "UMAP not available. Install with: pip install umap-learn"
            )

        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn not available. Install with: pip install scikit-learn"
            )

        self.embeddings_dir = Path(embeddings_dir)
        self.storage_manager = EmbeddingStorageManager(embeddings_dir)
        self.analysis_dir = self.embeddings_dir / "analysis"

        # Ensure analysis directories exist
        (self.analysis_dir / "umap_projections").mkdir(parents=True, exist_ok=True)
        (self.analysis_dir / "clustering").mkdir(parents=True, exist_ok=True)
        (self.analysis_dir / "themes").mkdir(parents=True, exist_ok=True)

    def run_umap_analysis(
        self,
        embedding_type: str = "citations",
        n_components: int = 2,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = "cosine",
        random_state: int = 42,
        save_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Run UMAP dimensionality reduction on embeddings.

        Args:
            embedding_type: 'citations', 'datasets', or 'both'
            n_components: Number of dimensions for UMAP output
            n_neighbors: UMAP n_neighbors parameter
            min_dist: UMAP min_dist parameter
            metric: Distance metric for UMAP
            random_state: Random seed for reproducibility
            save_results: Whether to save results to files

        Returns:
            Dict with UMAP results and metadata
        """
        logger.info(f"Running UMAP analysis on {embedding_type} embeddings")

        # Load embeddings
        embeddings_dict = self.storage_manager.get_all_current_embeddings(
            embedding_type
        )

        if not embeddings_dict:
            raise ValueError(f"No {embedding_type} embeddings found")

        # Prepare data
        embedding_ids = list(embeddings_dict.keys())
        embeddings_matrix = np.vstack([embeddings_dict[id_] for id_ in embedding_ids])

        logger.info(
            f"Loaded {len(embedding_ids)} embeddings of shape {embeddings_matrix.shape}"
        )

        # Configure UMAP
        umap_model = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric=metric,
            random_state=random_state,
            verbose=True,
        )

        # Fit and transform
        logger.info("Fitting UMAP model...")
        umap_embeddings = umap_model.fit_transform(embeddings_matrix)

        # Prepare results
        results = {
            "embedding_ids": embedding_ids,
            "original_embeddings": embeddings_matrix,
            "umap_embeddings": umap_embeddings,
            "umap_params": {
                "n_components": n_components,
                "n_neighbors": n_neighbors,
                "min_dist": min_dist,
                "metric": metric,
                "random_state": random_state,
            },
            "embedding_type": embedding_type,
            "created": datetime.now().isoformat(),
            "n_samples": len(embedding_ids),
        }

        if save_results:
            # Save UMAP results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{embedding_type}_umap_{n_components}d_v1_{timestamp}.pkl"
            file_path = self.analysis_dir / "umap_projections" / filename

            with open(file_path, "wb") as f:
                pickle.dump(results, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Saved UMAP results to: {file_path}")

            # Update registry
            self._update_analysis_registry("umap_projections", filename, results)

        return results

    def cluster_umap_embeddings(
        self,
        umap_results: Dict[str, Any],
        method: str = "dbscan",
        save_results: bool = True,
        **clustering_kwargs,
    ) -> Dict[str, Any]:
        """
        Cluster UMAP embeddings to identify research themes.

        Args:
            umap_results: Results from run_umap_analysis
            method: Clustering method ('dbscan', 'kmeans')
            save_results: Whether to save clustering results
            **clustering_kwargs: Parameters for clustering algorithm

        Returns:
            Dict with clustering results
        """
        logger.info(f"Clustering UMAP embeddings using {method}")

        umap_embeddings = umap_results["umap_embeddings"]
        embedding_ids = umap_results["embedding_ids"]

        # Configure clustering algorithm
        if method == "dbscan":
            eps = clustering_kwargs.get("eps", 0.5)
            min_samples = clustering_kwargs.get("min_samples", 5)
            clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean")
        elif method == "kmeans":
            n_clusters = clustering_kwargs.get("n_clusters", 8)
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        else:
            raise ValueError(f"Unsupported clustering method: {method}")

        # Perform clustering
        cluster_labels = clusterer.fit_predict(umap_embeddings)

        # Calculate metrics
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_noise = list(cluster_labels).count(-1)

        # Calculate silhouette score if we have more than 1 cluster
        silhouette = None
        if n_clusters > 1 and n_noise < len(cluster_labels):
            # Remove noise points for silhouette calculation
            mask = cluster_labels != -1
            if np.sum(mask) > 1:
                silhouette = silhouette_score(
                    umap_embeddings[mask], cluster_labels[mask]
                )

        # Prepare clustering results
        clustering_results = {
            "cluster_labels": cluster_labels,
            "embedding_ids": embedding_ids,
            "umap_embeddings": umap_embeddings,
            "method": method,
            "parameters": clustering_kwargs,
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "silhouette_score": silhouette,
            "created": datetime.now().isoformat(),
            "based_on_umap": umap_results.get("created", "unknown"),
        }

        # Create cluster analysis
        cluster_analysis = self._analyze_clusters(clustering_results, umap_results)
        clustering_results["cluster_analysis"] = cluster_analysis

        if save_results:
            # Save clustering results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = (
                f"{umap_results['embedding_type']}_clusters_{method}_v1_{timestamp}.pkl"
            )
            file_path = self.analysis_dir / "clustering" / filename

            with open(file_path, "wb") as f:
                pickle.dump(clustering_results, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Saved clustering results to: {file_path}")

            # Save human-readable cluster summary
            self._save_cluster_summary(clustering_results, umap_results)

            # Update registry
            self._update_analysis_registry("clustering", filename, clustering_results)

        return clustering_results

    def _analyze_clusters(
        self, clustering_results: Dict[str, Any], umap_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze clusters to extract meaningful information about research themes.

        Args:
            clustering_results: Results from clustering
            umap_results: Original UMAP results

        Returns:
            Dict with cluster analysis
        """
        cluster_labels = clustering_results["cluster_labels"]
        embedding_ids = clustering_results["embedding_ids"]
        embedding_type = umap_results["embedding_type"]

        # Group by cluster
        clusters = {}
        for i, (emb_id, cluster_id) in enumerate(zip(embedding_ids, cluster_labels)):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(
                {"embedding_id": emb_id, "index": i, "embedding_type": embedding_type}
            )

        # Analyze each cluster
        cluster_analysis = {}
        for cluster_id, members in clusters.items():
            if cluster_id == -1:
                cluster_name = "noise"
            else:
                cluster_name = f"cluster_{cluster_id}"

            analysis = {
                "cluster_id": cluster_id,
                "size": len(members),
                "members": members,
                "percentage": len(members) / len(embedding_ids) * 100,
            }

            # Extract dataset/citation info for thematic analysis
            if embedding_type in ["citations", "both"]:
                citation_members = [
                    m for m in members if m["embedding_id"].startswith("citation_")
                ]
                analysis["citation_count"] = len(citation_members)

                # Try to extract themes from citation IDs (would need title/abstract access)
                if citation_members:
                    analysis["sample_citations"] = citation_members[
                        :5
                    ]  # Sample for manual review

            if embedding_type in ["datasets", "both"]:
                dataset_members = [
                    m for m in members if m["embedding_id"].startswith("dataset_")
                ]
                analysis["dataset_count"] = len(dataset_members)

                if dataset_members:
                    analysis["sample_datasets"] = dataset_members[:5]

            cluster_analysis[cluster_name] = analysis

        return cluster_analysis

    def _save_cluster_summary(
        self, clustering_results: Dict[str, Any], umap_results: Dict[str, Any]
    ):
        """
        Save human-readable cluster summary.

        Args:
            clustering_results: Clustering results
            umap_results: UMAP results
        """
        summary = {
            "analysis_summary": {
                "embedding_type": umap_results["embedding_type"],
                "total_embeddings": len(clustering_results["embedding_ids"]),
                "clustering_method": clustering_results["method"],
                "n_clusters": clustering_results["n_clusters"],
                "n_noise": clustering_results["n_noise"],
                "silhouette_score": clustering_results["silhouette_score"],
                "created": clustering_results["created"],
            },
            "umap_parameters": umap_results["umap_params"],
            "clustering_parameters": clustering_results["parameters"],
            "cluster_details": clustering_results["cluster_analysis"],
        }

        # Save as JSON for easy reading
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{umap_results['embedding_type']}_cluster_summary_{timestamp}.json"
        file_path = self.analysis_dir / "themes" / filename

        with open(file_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Saved cluster summary to: {file_path}")

    def create_research_theme_visualization(
        self,
        clustering_results: Dict[str, Any],
        output_dir: Optional[Union[str, Path]] = None,
        create_plots: bool = True,
    ) -> Dict[str, Path]:
        """
        Create visualizations for research themes identified through clustering.

        Args:
            clustering_results: Results from cluster_umap_embeddings
            output_dir: Directory to save visualizations (defaults to results/umap_analysis/)
            create_plots: Whether to create matplotlib plots

        Returns:
            Dict mapping visualization types to file paths
        """
        if output_dir is None:
            output_dir = Path("results/umap_analysis")
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        if create_plots:
            try:
                import matplotlib.pyplot as plt

                # Create UMAP scatter plot with cluster colors
                fig, axes = plt.subplots(1, 2, figsize=(15, 6))

                umap_embeddings = clustering_results["umap_embeddings"]
                cluster_labels = clustering_results["cluster_labels"]

                # Plot 1: UMAP projection colored by cluster
                scatter = axes[0].scatter(
                    umap_embeddings[:, 0],
                    umap_embeddings[:, 1],
                    c=cluster_labels,
                    cmap="tab10",
                    alpha=0.7,
                    s=30,
                )
                axes[0].set_title(
                    f"Research Themes - UMAP Projection\n({clustering_results['n_clusters']} clusters, {clustering_results['n_noise']} noise)"
                )
                axes[0].set_xlabel("UMAP 1")
                axes[0].set_ylabel("UMAP 2")
                plt.colorbar(scatter, ax=axes[0], label="Cluster")

                # Plot 2: Cluster size distribution
                cluster_sizes = []
                cluster_names = []
                for cluster_id in set(cluster_labels):
                    if cluster_id != -1:  # Exclude noise
                        size = np.sum(cluster_labels == cluster_id)
                        cluster_sizes.append(size)
                        cluster_names.append(f"Cluster {cluster_id}")

                axes[1].bar(cluster_names, cluster_sizes)
                axes[1].set_title("Cluster Size Distribution")
                axes[1].set_xlabel("Cluster")
                axes[1].set_ylabel("Number of Items")
                axes[1].tick_params(axis="x", rotation=45)

                plt.tight_layout()

                # Save plot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_file = output_dir / f"research_themes_umap_{timestamp}.png"
                plt.savefig(plot_file, dpi=300, bbox_inches="tight")
                plt.close()

                saved_files["umap_plot"] = plot_file
                logger.info(f"Saved UMAP visualization to: {plot_file}")

            except ImportError:
                logger.warning("Matplotlib not available, skipping plot creation")

        # Save cluster data as CSV for external analysis
        cluster_data = []
        for i, (emb_id, cluster_label) in enumerate(
            zip(
                clustering_results["embedding_ids"],
                clustering_results["cluster_labels"],
            )
        ):
            cluster_data.append(
                {
                    "embedding_id": emb_id,
                    "cluster": cluster_label,
                    "umap_x": clustering_results["umap_embeddings"][i, 0],
                    "umap_y": clustering_results["umap_embeddings"][i, 1]
                    if clustering_results["umap_embeddings"].shape[1] > 1
                    else 0,
                }
            )

        df = pd.DataFrame(cluster_data)
        csv_file = (
            output_dir
            / f"research_themes_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df.to_csv(csv_file, index=False)
        saved_files["cluster_data"] = csv_file

        logger.info(f"Saved cluster data to: {csv_file}")

        return saved_files

    def _update_analysis_registry(
        self, analysis_type: str, filename: str, results: Dict[str, Any]
    ):
        """
        Update analysis registry with new analysis results.

        Args:
            analysis_type: Type of analysis ('umap_projections', 'clustering')
            filename: Filename of saved results
            results: Analysis results dict
        """
        registry = self.storage_manager.registry.registry

        analysis_record = {
            "file": f"analysis/{analysis_type}/{filename}",
            "created": results["created"],
            "parameters": results.get("umap_params", {})
            if analysis_type == "umap_projections"
            else results.get("parameters", {}),
            "status": "current",
        }

        if analysis_type == "umap_projections":
            analysis_record["input_embeddings"] = len(results["embedding_ids"])
            analysis_record["embedding_type"] = results["embedding_type"]
        elif analysis_type == "clustering":
            analysis_record["n_clusters"] = results["n_clusters"]
            analysis_record["method"] = results["method"]
            analysis_record["silhouette_score"] = results["silhouette_score"]

        registry["analysis"][analysis_type].append(analysis_record)
        self.storage_manager.registry._save_registry()

    def get_analysis_summary(self) -> Dict[str, Any]:
        """
        Get summary of all UMAP analyses performed.

        Returns:
            Dict with analysis summary
        """
        registry = self.storage_manager.registry.registry

        summary = {
            "umap_analyses": len(registry["analysis"]["umap_projections"]),
            "clustering_analyses": len(registry["analysis"]["clustering"]),
            "latest_umap": None,
            "latest_clustering": None,
            "storage_stats": self.storage_manager.get_storage_stats(),
        }

        # Get latest analyses
        if registry["analysis"]["umap_projections"]:
            latest_umap = max(
                registry["analysis"]["umap_projections"], key=lambda x: x["created"]
            )
            summary["latest_umap"] = {
                "created": latest_umap["created"],
                "embedding_type": latest_umap.get("embedding_type", "unknown"),
                "input_embeddings": latest_umap.get("input_embeddings", 0),
            }

        if registry["analysis"]["clustering"]:
            latest_clustering = max(
                registry["analysis"]["clustering"], key=lambda x: x["created"]
            )
            summary["latest_clustering"] = {
                "created": latest_clustering["created"],
                "method": latest_clustering.get("method", "unknown"),
                "n_clusters": latest_clustering.get("n_clusters", 0),
                "silhouette_score": latest_clustering.get("silhouette_score"),
            }

        return summary
