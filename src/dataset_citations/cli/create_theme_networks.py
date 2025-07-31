"""
CLI command for creating word clouds and context networks from research themes.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import json
import pickle
from collections import Counter, defaultdict
import re

try:
    from wordcloud import WordCloud

    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

try:
    import networkx as nx
    import matplotlib.pyplot as plt

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from ..embeddings.umap_analyzer import UMAPAnalyzer
from ..core.citation_utils import load_citations_from_json


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


class ThemeNetworkGenerator:
    """
    Generator for word clouds and context networks from research themes.
    """

    def __init__(self, embeddings_dir: Path, citations_dir: Path, datasets_dir: Path):
        """Initialize the theme network generator."""
        self.embeddings_dir = embeddings_dir
        self.citations_dir = citations_dir
        self.datasets_dir = datasets_dir
        self.analyzer = UMAPAnalyzer(embeddings_dir)

    def load_clustering_results(self, clustering_file: Optional[Path] = None) -> Dict:
        """
        Load clustering results from file.

        Args:
            clustering_file: Specific clustering file to load (or latest if None)

        Returns:
            Clustering results dictionary
        """
        if clustering_file:
            with open(clustering_file, "rb") as f:
                return pickle.load(f)

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

        # Get most recent file
        latest_file = max(clustering_files, key=lambda f: f.stat().st_mtime)
        logging.info(f"Loading clustering results from: {latest_file}")

        with open(latest_file, "rb") as f:
            return pickle.load(f)

    def extract_citation_texts(self, embedding_ids: List[str]) -> Dict[str, Dict]:
        """
        Extract citation texts for given embedding IDs.

        Args:
            embedding_ids: List of embedding IDs (e.g., 'citation_a1b2c3d4')

        Returns:
            Dict mapping embedding IDs to citation info
        """
        citation_texts = {}

        # Group by dataset for efficient loading
        dataset_citations = defaultdict(list)

        for emb_id in embedding_ids:
            if emb_id.startswith("citation_"):
                citation_hash = emb_id.replace("citation_", "")
                # We need to find which dataset this citation belongs to
                # This requires scanning citation files - could be optimized with an index
                dataset_citations["unknown"].append((emb_id, citation_hash))

        # Load all citation files to find matching hashes
        citation_files = list((self.citations_dir / "json").glob("ds*_citations.json"))

        for citation_file in citation_files:
            dataset_id = citation_file.stem.replace("_citations", "")

            try:
                citations_data = load_citations_from_json(citation_file)
                if "citation_details" not in citations_data:
                    continue

                for citation in citations_data["citation_details"]:
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
                            citation_texts[emb_id] = {
                                "title": title,
                                "abstract": abstract,
                                "full_text": citation_text,
                                "dataset_id": dataset_id,
                                "confidence_score": citation.get(
                                    "confidence_score", 0.0
                                ),
                                "year": citation.get("year"),
                                "author": citation.get("author", ""),
                                "venue": citation.get("venue", ""),
                            }

            except Exception as e:
                logging.warning(f"Error loading citation file {citation_file}: {e}")
                continue

        logging.info(
            f"Extracted {len(citation_texts)} citation texts from {len(embedding_ids)} embedding IDs"
        )
        return citation_texts

    def extract_dataset_texts(self, embedding_ids: List[str]) -> Dict[str, Dict]:
        """
        Extract dataset texts for given embedding IDs.

        Args:
            embedding_ids: List of embedding IDs (e.g., 'dataset_ds000117')

        Returns:
            Dict mapping embedding IDs to dataset info
        """
        dataset_texts = {}

        for emb_id in embedding_ids:
            if emb_id.startswith("dataset_"):
                dataset_id = emb_id.replace("dataset_", "")
                dataset_file = self.datasets_dir / f"{dataset_id}_datasets.json"

                if dataset_file.exists():
                    try:
                        with open(dataset_file, "r") as f:
                            dataset_data = json.load(f)

                        # Extract relevant text
                        description = dataset_data.get("description", "")
                        readme = dataset_data.get("readme_content", "")
                        dataset_desc = dataset_data.get("dataset_description", {})

                        dataset_texts[emb_id] = {
                            "dataset_id": dataset_id,
                            "description": description,
                            "readme_content": readme,
                            "dataset_description": dataset_desc,
                            "full_text": f"{description} {readme}".strip(),
                        }

                    except Exception as e:
                        logging.warning(f"Error loading dataset {dataset_id}: {e}")

        logging.info(f"Extracted {len(dataset_texts)} dataset texts")
        return dataset_texts

    def generate_cluster_word_clouds(
        self,
        clustering_results: Dict,
        output_dir: Path,
        min_word_length: int = 3,
        max_words: int = 100,
        stopwords: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """
        Generate word clouds for each research theme cluster.

        Args:
            clustering_results: Clustering results from UMAP analysis
            output_dir: Output directory for word clouds
            min_word_length: Minimum word length to include
            max_words: Maximum number of words in word cloud
            stopwords: Additional stopwords to exclude

        Returns:
            Dict mapping cluster names to word cloud file paths
        """
        if not WORDCLOUD_AVAILABLE:
            logging.error(
                "WordCloud not available. Install with: pip install wordcloud"
            )
            return {}

        logging.info("Generating word clouds for research themes")

        # Set up output directory
        wordcloud_dir = output_dir / "word_clouds"
        wordcloud_dir.mkdir(parents=True, exist_ok=True)

        # Extract texts for embeddings
        embedding_ids = clustering_results["embedding_ids"]
        citation_texts = self.extract_citation_texts(embedding_ids)
        dataset_texts = self.extract_dataset_texts(embedding_ids)

        # Default stopwords
        default_stopwords = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "up",
            "down",
            "out",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "any",
            "both",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "can",
            "will",
            "just",
            "don",
            "should",
            "now",
            "study",
            "data",
            "using",
            "used",
            "analysis",
            "results",
            "show",
            "shows",
            "research",
            "participants",
            "subjects",
            "experiment",
            "experimental",
            "neural",
            "brain",
            "cognitive",
        }

        if stopwords:
            default_stopwords.update(stopwords)

        # Group embeddings by cluster
        cluster_groups = defaultdict(list)
        for i, (emb_id, cluster_label) in enumerate(
            zip(embedding_ids, clustering_results["cluster_labels"])
        ):
            cluster_groups[cluster_label].append(emb_id)

        word_cloud_files = {}

        # Generate word cloud for each cluster
        for cluster_id, emb_ids in cluster_groups.items():
            if cluster_id == -1:  # Skip noise
                continue

            cluster_name = f"cluster_{cluster_id}"
            logging.info(
                f"Generating word cloud for {cluster_name} ({len(emb_ids)} items)"
            )

            # Collect all text for this cluster
            cluster_texts = []

            for emb_id in emb_ids:
                if emb_id in citation_texts:
                    text = citation_texts[emb_id]["full_text"]
                    cluster_texts.append(text)
                elif emb_id in dataset_texts:
                    text = dataset_texts[emb_id]["full_text"]
                    cluster_texts.append(text)

            if not cluster_texts:
                logging.warning(f"No text found for {cluster_name}")
                continue

            # Combine all texts
            combined_text = " ".join(cluster_texts)

            # Clean and preprocess text
            # Remove special characters and normalize
            cleaned_text = re.sub(r"[^\w\s]", " ", combined_text.lower())
            cleaned_text = re.sub(r"\s+", " ", cleaned_text)

            # Filter words
            words = [
                word
                for word in cleaned_text.split()
                if len(word) >= min_word_length and word not in default_stopwords
            ]

            if len(words) < 10:
                logging.warning(f"Too few words for {cluster_name} word cloud")
                continue

            # Create word frequency dict
            word_freq = Counter(words)

            # Generate word cloud
            try:
                wordcloud = WordCloud(
                    width=800,
                    height=400,
                    background_color="white",
                    max_words=max_words,
                    colormap="viridis",
                    relative_scaling=0.5,
                    min_font_size=10,
                ).generate_from_frequencies(word_freq)

                # Save word cloud
                plt.figure(figsize=(10, 5))
                plt.imshow(wordcloud, interpolation="bilinear")
                plt.axis("off")
                plt.title(
                    f"Research Theme {cluster_id} - Word Cloud\n({len(emb_ids)} items)"
                )
                plt.tight_layout()

                output_file = wordcloud_dir / f"theme_{cluster_id}_wordcloud.png"
                plt.savefig(output_file, dpi=300, bbox_inches="tight")
                plt.close()

                word_cloud_files[cluster_name] = output_file
                logging.info(f"Saved word cloud: {output_file}")

            except Exception as e:
                logging.error(f"Error generating word cloud for {cluster_name}: {e}")

        return word_cloud_files

    def create_theme_context_network(
        self,
        clustering_results: Dict,
        output_dir: Path,
        min_connections: int = 2,
        layout_algorithm: str = "spring",
    ) -> Path:
        """
        Create a context network showing connections between themes, papers, and datasets.

        Args:
            clustering_results: Clustering results
            output_dir: Output directory
            min_connections: Minimum connections for nodes to include
            layout_algorithm: Network layout algorithm

        Returns:
            Path to network visualization file
        """
        if not NETWORKX_AVAILABLE:
            logging.error(
                "NetworkX not available. Install with: pip install networkx matplotlib"
            )
            return None

        logging.info("Creating theme context network")

        # Set up output directory
        network_dir = output_dir / "context_networks"
        network_dir.mkdir(parents=True, exist_ok=True)

        # Extract texts
        embedding_ids = clustering_results["embedding_ids"]
        citation_texts = self.extract_citation_texts(embedding_ids)
        dataset_texts = self.extract_dataset_texts(embedding_ids)

        # Create network graph
        G = nx.Graph()

        # Group by clusters
        cluster_groups = defaultdict(list)
        for i, (emb_id, cluster_label) in enumerate(
            zip(embedding_ids, clustering_results["cluster_labels"])
        ):
            if cluster_label != -1:  # Exclude noise
                cluster_groups[cluster_label].append(emb_id)

        # Add cluster nodes
        for cluster_id, emb_ids in cluster_groups.items():
            cluster_name = f"Theme_{cluster_id}"
            G.add_node(cluster_name, node_type="theme", size=len(emb_ids), color="red")

        # Add paper and dataset nodes, connect to themes
        for cluster_id, emb_ids in cluster_groups.items():
            cluster_name = f"Theme_{cluster_id}"

            for emb_id in emb_ids:
                if emb_id in citation_texts:
                    # Add citation node
                    citation_info = citation_texts[emb_id]
                    paper_name = f"Paper_{emb_id[:12]}"

                    G.add_node(
                        paper_name,
                        node_type="paper",
                        title=citation_info["title"][:50] + "...",
                        dataset_id=citation_info["dataset_id"],
                        confidence=citation_info["confidence_score"],
                        color="blue",
                    )

                    # Connect to theme
                    G.add_edge(cluster_name, paper_name, edge_type="contains")

                    # Connect to dataset if available
                    dataset_name = f"Dataset_{citation_info['dataset_id']}"
                    if not G.has_node(dataset_name):
                        G.add_node(
                            dataset_name,
                            node_type="dataset",
                            dataset_id=citation_info["dataset_id"],
                            color="green",
                        )

                    G.add_edge(paper_name, dataset_name, edge_type="cites")

                elif emb_id in dataset_texts:
                    # Add dataset node if not already added
                    dataset_info = dataset_texts[emb_id]
                    dataset_name = f"Dataset_{dataset_info['dataset_id']}"

                    if not G.has_node(dataset_name):
                        G.add_node(
                            dataset_name,
                            node_type="dataset",
                            dataset_id=dataset_info["dataset_id"],
                            description=dataset_info["description"][:50] + "...",
                            color="green",
                        )

                    # Connect to theme
                    G.add_edge(cluster_name, dataset_name, edge_type="contains")

        # Filter nodes with minimum connections
        nodes_to_remove = [
            node
            for node, degree in G.degree()
            if degree < min_connections and G.nodes[node].get("node_type") != "theme"
        ]
        G.remove_nodes_from(nodes_to_remove)

        logging.info(
            f"Created context network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges"
        )

        # Create visualization
        plt.figure(figsize=(20, 15))

        # Choose layout
        if layout_algorithm == "spring":
            pos = nx.spring_layout(G, k=3, iterations=50)
        elif layout_algorithm == "circular":
            pos = nx.circular_layout(G)
        elif layout_algorithm == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.spring_layout(G)

        # Draw nodes by type
        theme_nodes = [
            n for n, d in G.nodes(data=True) if d.get("node_type") == "theme"
        ]
        paper_nodes = [
            n for n, d in G.nodes(data=True) if d.get("node_type") == "paper"
        ]
        dataset_nodes = [
            n for n, d in G.nodes(data=True) if d.get("node_type") == "dataset"
        ]

        # Draw theme nodes (largest)
        if theme_nodes:
            theme_sizes = [G.nodes[n].get("size", 10) * 100 for n in theme_nodes]
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=theme_nodes,
                node_color="red",
                node_size=theme_sizes,
                alpha=0.8,
                label="Research Themes",
            )

        # Draw paper nodes (medium)
        if paper_nodes:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=paper_nodes,
                node_color="lightblue",
                node_size=300,
                alpha=0.6,
                label="Papers",
            )

        # Draw dataset nodes (small)
        if dataset_nodes:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=dataset_nodes,
                node_color="lightgreen",
                node_size=200,
                alpha=0.6,
                label="Datasets",
            )

        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.3, width=0.5)

        # Add labels for theme nodes only (to avoid clutter)
        theme_labels = {n: n for n in theme_nodes}
        nx.draw_networkx_labels(G, pos, labels=theme_labels, font_size=8)

        plt.title(
            "Research Theme Context Network\nConnections between Themes, Papers, and Datasets",
            fontsize=16,
        )
        plt.legend()
        plt.axis("off")
        plt.tight_layout()

        # Save network
        network_file = network_dir / "theme_context_network.png"
        plt.savefig(network_file, dpi=300, bbox_inches="tight")
        plt.close()

        # Save network data as GraphML for external tools
        graphml_file = network_dir / "theme_context_network.graphml"
        nx.write_graphml(G, graphml_file)

        logging.info(f"Saved context network: {network_file}")
        logging.info(f"Saved network data: {graphml_file}")

        return network_file


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate word clouds and context networks from research themes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate word clouds for all themes
  dataset-citations-create-theme-networks --embeddings-dir embeddings/ --output-dir results/theme_analysis/

  # Create context network with custom parameters
  dataset-citations-create-theme-networks --create-networks --min-connections 3 --layout spring

  # Generate both with custom clustering results
  dataset-citations-create-theme-networks --clustering-file embeddings/analysis/clustering/citations_clusters_dbscan_v1.pkl

  # Custom word cloud settings
  dataset-citations-create-theme-networks --max-words 150 --min-word-length 4
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
        "--datasets-dir",
        type=Path,
        default="datasets",
        help="Path to datasets directory (default: datasets)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default="results/theme_analysis",
        help="Output directory for results (default: results/theme_analysis)",
    )

    parser.add_argument(
        "--clustering-file",
        type=Path,
        help="Specific clustering results file to use (uses latest if not specified)",
    )

    # Word cloud options
    parser.add_argument(
        "--create-word-clouds",
        action="store_true",
        default=True,
        help="Generate word clouds for themes (default: True)",
    )

    parser.add_argument(
        "--max-words",
        type=int,
        default=100,
        help="Maximum words in word clouds (default: 100)",
    )

    parser.add_argument(
        "--min-word-length",
        type=int,
        default=3,
        help="Minimum word length for word clouds (default: 3)",
    )

    parser.add_argument(
        "--stopwords", nargs="+", help="Additional stopwords to exclude"
    )

    # Network options
    parser.add_argument(
        "--create-networks", action="store_true", help="Create context networks"
    )

    parser.add_argument(
        "--min-connections",
        type=int,
        default=2,
        help="Minimum connections for network nodes (default: 2)",
    )

    parser.add_argument(
        "--layout",
        choices=["spring", "circular", "kamada_kawai"],
        default="spring",
        help="Network layout algorithm (default: spring)",
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

    if not args.datasets_dir.exists():
        logging.error(f"Datasets directory not found: {args.datasets_dir}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        logging.info("=" * 60)
        logging.info("THEME NETWORK GENERATION")
        logging.info("=" * 60)

        # Initialize generator
        generator = ThemeNetworkGenerator(
            embeddings_dir=args.embeddings_dir,
            citations_dir=args.citations_dir,
            datasets_dir=args.datasets_dir,
        )

        # Load clustering results
        clustering_results = generator.load_clustering_results(args.clustering_file)
        logging.info(
            f"Loaded clustering with {clustering_results['n_clusters']} themes"
        )

        created_files = []

        # Generate word clouds
        if args.create_word_clouds:
            logging.info("=" * 40)
            logging.info("GENERATING WORD CLOUDS")
            logging.info("=" * 40)

            word_cloud_files = generator.generate_cluster_word_clouds(
                clustering_results=clustering_results,
                output_dir=args.output_dir,
                min_word_length=args.min_word_length,
                max_words=args.max_words,
                stopwords=args.stopwords,
            )
            created_files.extend(word_cloud_files.values())

        # Create context networks
        if args.create_networks:
            logging.info("=" * 40)
            logging.info("CREATING CONTEXT NETWORKS")
            logging.info("=" * 40)

            network_file = generator.create_theme_context_network(
                clustering_results=clustering_results,
                output_dir=args.output_dir,
                min_connections=args.min_connections,
                layout_algorithm=args.layout,
            )
            if network_file:
                created_files.append(network_file)

        # Summary
        logging.info("=" * 60)
        logging.info("THEME NETWORK GENERATION COMPLETE")
        logging.info("=" * 60)
        logging.info(f"Created {len(created_files)} files:")
        for file_path in created_files:
            logging.info(f"  - {file_path}")
        logging.info(f"Results saved to: {args.output_dir}")

        return 0

    except Exception as e:
        logging.error(f"Error during theme network generation: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
