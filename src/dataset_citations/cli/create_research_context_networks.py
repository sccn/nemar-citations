"""
CLI command for creating research context networks that visualize connections between papers and datasets.

This module creates network visualizations showing how papers and datasets are connected
through embedding similarity, identifying research bridges and thematic relationships.
"""

import argparse
import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from collections import defaultdict
import hashlib

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from ..embeddings.storage_manager import EmbeddingStorageManager
from ..core.citation_utils import load_citations_from_json


def setup_logging(verbose: bool):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


class ResearchContextNetworkAnalyzer:
    """
    Analyzer for creating research context networks using embedding similarity.
    """

    def __init__(self, embeddings_dir: Path, citations_dir: Path, datasets_dir: Path):
        """Initialize the research context network analyzer."""
        self.embeddings_dir = embeddings_dir
        self.citations_dir = citations_dir
        self.datasets_dir = datasets_dir
        self.storage_manager = EmbeddingStorageManager(embeddings_dir)

    def load_embedding_metadata(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Load metadata for all available embeddings.

        Returns:
            Tuple of (dataset_metadata, citation_metadata)
        """
        logging.info("Loading embedding metadata...")

        dataset_metadata = {}
        citation_metadata = {}

        # Load dataset metadata
        registry = self.storage_manager.registry.registry
        for dataset_id in registry.get("datasets", {}):
            dataset_embeddings = registry["datasets"][dataset_id]["embeddings"]
            if dataset_embeddings:
                # Get most recent embedding
                latest = max(dataset_embeddings, key=lambda x: x["created"])
                if latest["status"] == "current":
                    dataset_metadata[dataset_id] = {
                        "embedding_id": f"dataset_{dataset_id}",
                        "type": "dataset",
                        "created": latest["created"],
                        "file": latest["file"],
                    }

        # Load citation metadata with temporal data
        for citation_hash in registry.get("citations", {}):
            citation_embeddings = registry["citations"][citation_hash]["embeddings"]
            if citation_embeddings:
                latest = max(citation_embeddings, key=lambda x: x["created"])
                if latest["status"] == "current":
                    citation_metadata[citation_hash] = {
                        "embedding_id": f"citation_{citation_hash}",
                        "type": "citation",
                        "created": latest["created"],
                        "file": latest["file"],
                    }

        logging.info(
            f"Loaded metadata for {len(dataset_metadata)} datasets, {len(citation_metadata)} citations"
        )
        return dataset_metadata, citation_metadata

    def calculate_embedding_similarities(
        self,
        dataset_metadata: Dict[str, Any],
        citation_metadata: Dict[str, Any],
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Calculate similarities between all embeddings to identify connections.

        Args:
            dataset_metadata: Dataset embedding metadata
            citation_metadata: Citation embedding metadata
            similarity_threshold: Minimum similarity for creating connections

        Returns:
            List of connection records with similarity scores
        """
        logging.info("Calculating embedding similarities...")

        connections = []

        # Load all embeddings
        all_embeddings = {}
        all_metadata = {}

        # Load dataset embeddings
        for dataset_id, meta in dataset_metadata.items():
            embedding = self.storage_manager.load_dataset_embedding(dataset_id)
            if embedding is not None:
                all_embeddings[meta["embedding_id"]] = embedding
                all_metadata[meta["embedding_id"]] = {**meta, "source_id": dataset_id}

        # Load citation embeddings
        for citation_hash, meta in citation_metadata.items():
            embedding = self.storage_manager.load_citation_embedding(citation_hash)
            if embedding is not None:
                all_embeddings[meta["embedding_id"]] = embedding
                all_metadata[meta["embedding_id"]] = {
                    **meta,
                    "source_id": citation_hash,
                }

        logging.info(
            f"Loaded {len(all_embeddings)} embeddings for similarity calculation"
        )

        # Calculate pairwise similarities
        embedding_ids = list(all_embeddings.keys())
        for i, id1 in enumerate(embedding_ids):
            for j, id2 in enumerate(embedding_ids[i + 1 :], i + 1):
                # Calculate cosine similarity
                emb1 = all_embeddings[id1]
                emb2 = all_embeddings[id2]

                # Normalize embeddings
                emb1_norm = emb1 / np.linalg.norm(emb1)
                emb2_norm = emb2 / np.linalg.norm(emb2)

                similarity = np.dot(emb1_norm, emb2_norm)

                if similarity >= similarity_threshold:
                    connection = {
                        "source": id1,
                        "target": id2,
                        "similarity": float(similarity),
                        "source_type": all_metadata[id1]["type"],
                        "target_type": all_metadata[id2]["type"],
                        "source_id": all_metadata[id1]["source_id"],
                        "target_id": all_metadata[id2]["source_id"],
                        "connection_type": f"{all_metadata[id1]['type']}_to_{all_metadata[id2]['type']}",
                    }
                    connections.append(connection)

        logging.info(
            f"Found {len(connections)} connections above threshold {similarity_threshold}"
        )
        return connections

    def identify_research_bridges(
        self, connections: List[Dict[str, Any]], min_connections: int = 3
    ) -> Dict[str, Dict[str, Any]]:
        """
        Identify research bridge papers/datasets that connect multiple research areas.

        Args:
            connections: List of similarity connections
            min_connections: Minimum connections to be considered a bridge

        Returns:
            Dict of bridge entities with their connection information
        """
        logging.info("Identifying research bridges...")

        # Count connections for each entity
        connection_counts = defaultdict(list)

        for conn in connections:
            connection_counts[conn["source"]].append(conn)
            connection_counts[conn["target"]].append(conn)

        # Identify bridges (entities with many connections)
        bridges = {}
        for entity_id, entity_connections in connection_counts.items():
            if len(entity_connections) >= min_connections:
                # Analyze the diversity of connections
                connected_types = set()
                connected_datasets = set()
                avg_similarity = 0.0

                for conn in entity_connections:
                    if conn["source"] == entity_id:
                        connected_types.add(conn["target_type"])
                        if conn["target_type"] == "dataset":
                            connected_datasets.add(conn["target_id"])
                    else:
                        connected_types.add(conn["source_type"])
                        if conn["source_type"] == "dataset":
                            connected_datasets.add(conn["source_id"])

                    avg_similarity += conn["similarity"]

                avg_similarity /= len(entity_connections)

                # Determine entity type
                entity_type = (
                    "dataset" if entity_id.startswith("dataset_") else "citation"
                )
                source_id = entity_id.replace("dataset_", "").replace("citation_", "")

                bridges[entity_id] = {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "source_id": source_id,
                    "total_connections": len(entity_connections),
                    "connected_types": list(connected_types),
                    "connected_datasets": list(connected_datasets),
                    "avg_similarity": avg_similarity,
                    "bridge_score": len(entity_connections)
                    * len(connected_types)
                    * avg_similarity,
                    "connections": entity_connections,
                }

        logging.info(f"Identified {len(bridges)} research bridges")
        return bridges

    def enrich_with_citation_data(
        self, connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich connections with citation and dataset metadata.

        Args:
            connections: List of similarity connections

        Returns:
            Enriched connections with metadata
        """
        logging.info("Enriching connections with citation data...")

        # Load citation data for enrichment
        citation_data_cache = {}
        dataset_data_cache = {}

        # Load citation files
        citation_files = list((self.citations_dir / "json").glob("ds*_citations.json"))
        for citation_file in citation_files:
            try:
                data = load_citations_from_json(citation_file)
                dataset_id = citation_file.stem.replace("_citations", "")
                citation_data_cache[dataset_id] = data
            except Exception as e:
                logging.warning(f"Error loading {citation_file}: {e}")

        # Load dataset metadata files
        dataset_files = list(self.datasets_dir.glob("ds*_datasets.json"))
        for dataset_file in dataset_files:
            try:
                with open(dataset_file, "r") as f:
                    data = json.load(f)
                dataset_id = dataset_file.stem.replace("_datasets", "")
                dataset_data_cache[dataset_id] = data
            except Exception as e:
                logging.warning(f"Error loading {dataset_file}: {e}")

        # Enrich connections
        enriched_connections = []
        for conn in connections:
            enriched_conn = conn.copy()

            # Enrich source
            if conn["source_type"] == "citation":
                enriched_conn["source_info"] = self._get_citation_info(
                    conn["source_id"], citation_data_cache
                )
            else:
                enriched_conn["source_info"] = self._get_dataset_info(
                    conn["source_id"], dataset_data_cache
                )

            # Enrich target
            if conn["target_type"] == "citation":
                enriched_conn["target_info"] = self._get_citation_info(
                    conn["target_id"], citation_data_cache
                )
            else:
                enriched_conn["target_info"] = self._get_dataset_info(
                    conn["target_id"], dataset_data_cache
                )

            enriched_connections.append(enriched_conn)

        return enriched_connections

    def _get_citation_info(
        self, citation_hash: str, citation_data_cache: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get citation information from cache."""
        for dataset_id, data in citation_data_cache.items():
            for citation in data.get("citation_details", []):
                # Generate citation hash
                title = citation.get("title", "")
                abstract = citation.get("abstract", "")
                citation_text = f"{title} {abstract}".strip()

                if citation_text:
                    hash_check = hashlib.sha256(citation_text.encode()).hexdigest()[:8]
                    if hash_check == citation_hash:
                        confidence_data = citation.get("confidence_scoring", {})
                        return {
                            "title": title,
                            "abstract": abstract[:200] + "..."
                            if len(abstract) > 200
                            else abstract,
                            "author": citation.get("author", ""),
                            "year": citation.get("year"),
                            "venue": citation.get("venue", ""),
                            "confidence_score": confidence_data.get(
                                "confidence_score", 0.0
                            ),
                            "cited_by": citation.get("cited_by", 0),
                            "dataset_id": dataset_id,
                        }

        return {"title": "Unknown Citation", "confidence_score": 0.0}

    def _get_dataset_info(
        self, dataset_id: str, dataset_data_cache: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get dataset information from cache."""
        if dataset_id in dataset_data_cache:
            data = dataset_data_cache[dataset_id]
            desc = data.get("dataset_description", {})
            return {
                "name": desc.get("Name", dataset_id),
                "description": (
                    desc.get("BIDSVersion", "")
                    + " "
                    + desc.get("DatasetType", "")
                    + " dataset"
                ).strip(),
                "authors": desc.get("Authors", []),
                "bids_version": desc.get("BIDSVersion", ""),
                "license": desc.get("License", ""),
            }

        return {"name": dataset_id, "description": "BIDS Dataset"}

    def create_network_visualizations(
        self,
        connections: List[Dict[str, Any]],
        bridges: Dict[str, Dict[str, Any]],
        output_dir: Path,
        confidence_threshold: float = 0.4,
    ) -> List[Path]:
        """
        Create network visualizations for research context networks.

        Args:
            connections: Enriched connection data
            bridges: Research bridge information
            output_dir: Output directory for visualizations
            confidence_threshold: Minimum confidence for citation filtering

        Returns:
            List of created visualization files
        """
        if not NETWORKX_AVAILABLE:
            logging.error("NetworkX not available for visualization")
            return []

        logging.info("Creating research context network visualizations...")
        output_dir.mkdir(parents=True, exist_ok=True)
        created_files = []

        # Filter connections by confidence
        filtered_connections = []
        for conn in connections:
            include = True

            # Check source confidence
            if conn["source_type"] == "citation":
                source_conf = conn.get("source_info", {}).get("confidence_score", 0.0)
                if source_conf < confidence_threshold:
                    include = False

            # Check target confidence
            if conn["target_type"] == "citation":
                target_conf = conn.get("target_info", {}).get("confidence_score", 0.0)
                if target_conf < confidence_threshold:
                    include = False

            if include:
                filtered_connections.append(conn)

        logging.info(
            f"Using {len(filtered_connections)} connections after confidence filtering"
        )

        # Create NetworkX graph
        G = nx.Graph()

        # Add nodes and edges
        for conn in filtered_connections:
            # Add source node
            G.add_node(
                conn["source"],
                type=conn["source_type"],
                info=conn.get("source_info", {}),
                is_bridge=conn["source"] in bridges,
            )

            # Add target node
            G.add_node(
                conn["target"],
                type=conn["target_type"],
                info=conn.get("target_info", {}),
                is_bridge=conn["target"] in bridges,
            )

            # Add edge
            G.add_edge(
                conn["source"],
                conn["target"],
                similarity=conn["similarity"],
                connection_type=conn["connection_type"],
            )

        logging.info(
            f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges"
        )

        # Create static visualization
        static_file = self._create_static_network_plot(G, bridges, output_dir)
        if static_file:
            created_files.append(static_file)

        # Create interactive visualization
        if PLOTLY_AVAILABLE:
            interactive_file = self._create_interactive_network_plot(
                G, bridges, output_dir
            )
            if interactive_file:
                created_files.append(interactive_file)

        # Create bridge analysis
        bridge_file = self._create_bridge_analysis(bridges, output_dir)
        if bridge_file:
            created_files.append(bridge_file)

        return created_files

    def _create_static_network_plot(
        self, G: nx.Graph, bridges: Dict[str, Any], output_dir: Path
    ) -> Optional[Path]:
        """Create static network plot with matplotlib."""
        try:
            fig, ax = plt.subplots(figsize=(16, 12))

            # Layout
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)

            # Node colors and sizes
            node_colors = []
            node_sizes = []
            for node in G.nodes():
                node_data = G.nodes[node]

                if node_data["type"] == "dataset":
                    node_colors.append(
                        "lightblue" if not node_data["is_bridge"] else "blue"
                    )
                    node_sizes.append(300 if not node_data["is_bridge"] else 600)
                else:
                    node_colors.append(
                        "lightcoral" if not node_data["is_bridge"] else "red"
                    )
                    node_sizes.append(100 if not node_data["is_bridge"] else 400)

            # Draw network
            nx.draw_networkx_nodes(
                G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.7, ax=ax
            )

            nx.draw_networkx_edges(
                G, pos, alpha=0.3, width=0.5, edge_color="gray", ax=ax
            )

            # Add labels for bridges only
            bridge_labels = {}
            for node in G.nodes():
                if G.nodes[node]["is_bridge"]:
                    info = G.nodes[node]["info"]
                    if G.nodes[node]["type"] == "dataset":
                        bridge_labels[node] = info.get("name", node)[:15]
                    else:
                        bridge_labels[node] = info.get("title", node)[:20]

            nx.draw_networkx_labels(
                G, pos, bridge_labels, font_size=8, font_weight="bold", ax=ax
            )

            # Legend
            legend_elements = [
                mpatches.Patch(color="lightblue", label="Dataset"),
                mpatches.Patch(color="lightcoral", label="Citation"),
                mpatches.Patch(color="blue", label="Dataset Bridge"),
                mpatches.Patch(color="red", label="Citation Bridge"),
            ]
            ax.legend(handles=legend_elements, loc="upper right")

            ax.set_title(
                f"Research Context Network\n{G.number_of_nodes()} nodes, {G.number_of_edges()} connections, {len(bridges)} bridges",
                fontsize=14,
                fontweight="bold",
            )
            ax.axis("off")

            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_file = output_dir / f"research_context_network_{timestamp}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches="tight")
            plt.close()

            logging.info(f"Created static network plot: {plot_file}")
            return plot_file

        except Exception as e:
            logging.error(f"Error creating static network plot: {e}")
            return None

    def _create_interactive_network_plot(
        self, G: nx.Graph, bridges: Dict[str, Any], output_dir: Path
    ) -> Optional[Path]:
        """Create interactive network plot with plotly."""
        try:
            # Layout
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)

            # Prepare edges
            edge_x = []
            edge_y = []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=0.5, color="#888"),
                hoverinfo="none",
                mode="lines",
            )

            # Prepare nodes
            node_trace = go.Scatter(
                x=[],
                y=[],
                mode="markers+text",
                hoverinfo="text",
                text=[],
                textposition="middle center",
                marker=dict(
                    size=[],
                    color=[],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Node Type"),
                ),
            )

            for node in G.nodes():
                x, y = pos[node]
                node_trace["x"] += tuple([x])
                node_trace["y"] += tuple([y])

                node_data = G.nodes[node]
                info = node_data["info"]

                if node_data["type"] == "dataset":
                    hover_text = f"Dataset: {info.get('name', node)}<br>"
                    hover_text += f"Description: {info.get('description', 'N/A')}<br>"
                    hover_text += f"BIDS Version: {info.get('bids_version', 'N/A')}"
                    node_trace["marker"]["color"] += tuple([1])
                    node_trace["marker"]["size"] += tuple(
                        [20 if not node_data["is_bridge"] else 40]
                    )
                    node_trace["text"] += tuple(
                        [info.get("name", node)[:10] if node_data["is_bridge"] else ""]
                    )
                else:
                    hover_text = f"Citation: {info.get('title', node)}<br>"
                    hover_text += f"Author: {info.get('author', 'N/A')}<br>"
                    hover_text += f"Year: {info.get('year', 'N/A')}<br>"
                    hover_text += (
                        f"Confidence: {info.get('confidence_score', 0.0):.3f}<br>"
                    )
                    hover_text += f"Cited by: {info.get('cited_by', 0)}"
                    node_trace["marker"]["color"] += tuple([0])
                    node_trace["marker"]["size"] += tuple(
                        [10 if not node_data["is_bridge"] else 30]
                    )
                    node_trace["text"] += tuple(
                        [info.get("title", node)[:15] if node_data["is_bridge"] else ""]
                    )

                if node_data["is_bridge"]:
                    hover_text += "<br><b>RESEARCH BRIDGE</b>"

                node_trace["hovertext"] = getattr(node_trace, "hovertext", []) + [
                    hover_text
                ]

            # Create figure
            fig = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title=f"Interactive Research Context Network<br>{G.number_of_nodes()} nodes, {G.number_of_edges()} connections",
                    titlefont_size=16,
                    showlegend=False,
                    hovermode="closest",
                    margin=dict(b=20, l=5, r=5, t=40),
                    annotations=[
                        dict(
                            text="Blue=Dataset, Red=Citation, Larger=Bridge",
                            showarrow=False,
                            xref="paper",
                            yref="paper",
                            x=0.005,
                            y=-0.002,
                            xanchor="left",
                            yanchor="bottom",
                            font=dict(color="gray", size=12),
                        )
                    ],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                ),
            )

            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = (
                output_dir / f"research_context_network_interactive_{timestamp}.html"
            )
            fig.write_html(html_file)

            logging.info(f"Created interactive network plot: {html_file}")
            return html_file

        except Exception as e:
            logging.error(f"Error creating interactive network plot: {e}")
            return None

    def _create_bridge_analysis(
        self, bridges: Dict[str, Any], output_dir: Path
    ) -> Optional[Path]:
        """Create bridge analysis report."""
        try:
            # Sort bridges by bridge score
            sorted_bridges = sorted(
                bridges.values(), key=lambda x: x["bridge_score"], reverse=True
            )

            # Create analysis
            analysis = {
                "bridge_analysis": {
                    "total_bridges": len(bridges),
                    "bridge_types": {
                        "datasets": len(
                            [
                                b
                                for b in bridges.values()
                                if b["entity_type"] == "dataset"
                            ]
                        ),
                        "citations": len(
                            [
                                b
                                for b in bridges.values()
                                if b["entity_type"] == "citation"
                            ]
                        ),
                    },
                    "top_bridges": [],
                },
                "created": datetime.now().isoformat(),
                "analysis_metadata": {
                    "min_connections_threshold": 3,
                    "scoring_method": "connections * types * avg_similarity",
                },
            }

            # Add top bridges
            for bridge in sorted_bridges[:20]:  # Top 20 bridges
                bridge_info = {
                    "entity_id": bridge["entity_id"],
                    "entity_type": bridge["entity_type"],
                    "source_id": bridge["source_id"],
                    "bridge_score": bridge["bridge_score"],
                    "total_connections": bridge["total_connections"],
                    "connected_types": bridge["connected_types"],
                    "connected_datasets": bridge["connected_datasets"],
                    "avg_similarity": bridge["avg_similarity"],
                }
                analysis["bridge_analysis"]["top_bridges"].append(bridge_info)

            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_file = output_dir / f"research_bridge_analysis_{timestamp}.json"
            with open(analysis_file, "w") as f:
                json.dump(analysis, f, indent=2, default=str)

            logging.info(f"Created bridge analysis: {analysis_file}")
            return analysis_file

        except Exception as e:
            logging.error(f"Error creating bridge analysis: {e}")
            return None


def main() -> int:
    """Main function for research context networks CLI."""
    parser = argparse.ArgumentParser(
        description="Create research context networks that visualize connections between papers and datasets",
        epilog="""
Examples:
  # Create research context networks with default settings
  dataset-citations-create-research-context-networks

  # Use custom similarity threshold
  dataset-citations-create-research-context-networks --similarity-threshold 0.8

  # Focus on high-confidence citations only
  dataset-citations-create-research-context-networks --confidence-threshold 0.6

  # Create networks with fewer bridge requirements
  dataset-citations-create-research-context-networks --min-bridge-connections 2
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
        default="results/research_context_networks",
        help="Output directory for results (default: results/research_context_networks)",
    )

    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.7,
        help="Minimum similarity threshold for connections (default: 0.7)",
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Minimum confidence score for citations (default: 0.4)",
    )

    parser.add_argument(
        "--min-bridge-connections",
        type=int,
        default=3,
        help="Minimum connections to be considered a research bridge (default: 3)",
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
        logging.info("RESEARCH CONTEXT NETWORK ANALYSIS")
        logging.info("=" * 60)

        # Initialize analyzer
        analyzer = ResearchContextNetworkAnalyzer(
            embeddings_dir=args.embeddings_dir,
            citations_dir=args.citations_dir,
            datasets_dir=args.datasets_dir,
        )

        # Load embedding metadata
        dataset_metadata, citation_metadata = analyzer.load_embedding_metadata()

        if not dataset_metadata and not citation_metadata:
            logging.error("No embeddings found. Run embedding generation first.")
            return 1

        # Calculate similarities
        connections = analyzer.calculate_embedding_similarities(
            dataset_metadata=dataset_metadata,
            citation_metadata=citation_metadata,
            similarity_threshold=args.similarity_threshold,
        )

        if not connections:
            logging.warning(
                f"No connections found above similarity threshold {args.similarity_threshold}"
            )
            return 0

        # Identify research bridges
        bridges = analyzer.identify_research_bridges(
            connections=connections,
            min_connections=args.min_bridge_connections,
        )

        # Enrich with citation data
        enriched_connections = analyzer.enrich_with_citation_data(connections)

        # Create visualizations
        created_files = analyzer.create_network_visualizations(
            connections=enriched_connections,
            bridges=bridges,
            output_dir=args.output_dir,
            confidence_threshold=args.confidence_threshold,
        )

        # Summary
        print("\n" + "=" * 50)
        print("RESEARCH CONTEXT NETWORK RESULTS")
        print("=" * 50)
        print("📊 Analysis Summary:")
        print(f"   • Total connections: {len(connections)}")
        print(f"   • High-confidence connections: {len(enriched_connections)}")
        print(f"   • Research bridges identified: {len(bridges)}")
        print(f"   • Similarity threshold: {args.similarity_threshold}")
        print(f"   • Confidence threshold: {args.confidence_threshold}")

        if bridges:
            print("\n🌉 Top Research Bridges:")
            sorted_bridges = sorted(
                bridges.values(), key=lambda x: x["bridge_score"], reverse=True
            )
            for i, bridge in enumerate(sorted_bridges[:5], 1):
                bridge_type = (
                    "Dataset" if bridge["entity_type"] == "dataset" else "Citation"
                )
                print(f"   {i}. {bridge_type}: {bridge['source_id']}")
                print(f"      • {bridge['total_connections']} connections")
                print(f"      • Bridge score: {bridge['bridge_score']:.2f}")

        if created_files:
            print(f"\n📁 Created {len(created_files)} visualization files:")
            for file in created_files:
                print(f"   • {file}")

        logging.info("Research context network analysis completed successfully")
        return 0

    except Exception as e:
        logging.error(f"Error during research context network analysis: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
