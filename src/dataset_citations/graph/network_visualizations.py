"""
Network Visualizations for Dataset Citations

This module creates interactive network graphs showing actual citation relationships,
similar to what citation-graph produces, using Neo4j data and NetworkX/Plotly.
"""

import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path
import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jNetworkVisualizer:
    """Create interactive network visualizations from Neo4j graph data."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "dataset123",
    ):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        """Close Neo4j connection."""
        self.driver.close()

    def get_dataset_co_citation_network(
        self, min_shared_citations: int = 2
    ) -> nx.Graph:
        """
        Create a network where datasets are connected by shared citations.

        Args:
            min_shared_citations: Minimum number of shared citations to create edge

        Returns:
            NetworkX graph with datasets as nodes, shared citations as edges
        """
        query = """
        MATCH (d1:Dataset)-[:HAS_CITATION]->(c1:Citation)
        MATCH (d2:Dataset)-[:HAS_CITATION]->(c2:Citation)
        WHERE c1.title = c2.title 
        AND d1.uid < d2.uid
        AND c1.confidence_score >= 0.4
        WITH d1, d2, count(DISTINCT c1.title) as shared_count, 
             collect(DISTINCT c1.title) as shared_papers
        WHERE shared_count >= $min_shared
        RETURN d1.uid as dataset1, d1.name as name1, d1.total_cumulative_citations as citations1,
               d2.uid as dataset2, d2.name as name2, d2.total_cumulative_citations as citations2,
               shared_count, shared_papers
        """

        G = nx.Graph()

        with self.driver.session() as session:
            result = session.run(query, min_shared=min_shared_citations)

            for record in result:
                # Add nodes with attributes
                G.add_node(
                    record["dataset1"],
                    name=record["name1"],
                    total_citations=record["citations1"] or 0,
                    node_type="dataset",
                )
                G.add_node(
                    record["dataset2"],
                    name=record["name2"],
                    total_citations=record["citations2"] or 0,
                    node_type="dataset",
                )

                # Add edge with weight
                G.add_edge(
                    record["dataset1"],
                    record["dataset2"],
                    weight=record["shared_count"],
                    shared_papers=record["shared_papers"],
                )

        logger.info(
            f"Created co-citation network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )
        return G

    def get_author_dataset_network(self, min_datasets: int = 3) -> nx.Graph:
        """
        Create a bipartite network of authors and datasets they cite.

        Args:
            min_datasets: Minimum datasets cited by author to include

        Returns:
            NetworkX graph with authors and datasets as nodes
        """
        query = """
        MATCH (d:Dataset)-[:HAS_CITATION]->(c:Citation)
        WHERE c.confidence_score >= 0.4 AND c.author IS NOT NULL
        WITH c.author as author, collect(DISTINCT d.uid) as datasets, 
             count(DISTINCT d.uid) as num_datasets,
             sum(c.cited_by) as total_impact
        WHERE num_datasets >= $min_datasets
        RETURN author, datasets, num_datasets, total_impact
        ORDER BY num_datasets DESC
        """

        G = nx.Graph()

        with self.driver.session() as session:
            result = session.run(query, min_datasets=min_datasets)

            for record in result:
                author = record["author"]
                datasets = record["datasets"]

                # Add author node
                G.add_node(
                    f"author_{author}",
                    name=author,
                    node_type="author",
                    num_datasets=record["num_datasets"],
                    total_impact=record["total_impact"] or 0,
                )

                # Add dataset nodes and connections
                for dataset in datasets:
                    G.add_node(f"dataset_{dataset}", name=dataset, node_type="dataset")
                    G.add_edge(f"author_{author}", f"dataset_{dataset}")

        logger.info(
            f"Created author-dataset network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )
        return G

    def create_interactive_co_citation_network(
        self, output_path: Path, min_shared: int = 2
    ) -> None:
        """
        Create an interactive Plotly network visualization of dataset co-citations.

        Args:
            output_path: Path to save HTML file
            min_shared: Minimum shared citations for edge
        """
        G = self.get_dataset_co_citation_network(min_shared)

        if G.number_of_nodes() == 0:
            logger.warning("No co-citation network data found")
            return

        # Use spring layout for positioning
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

        # Prepare node data
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = G.nodes[node]
            citations = node_data.get("total_citations", 0)
            name = node_data.get("name", node)

            node_text.append(f"{node}<br>Citations: {citations}<br>{name[:50]}...")
            node_size.append(
                max(10, min(50, citations / 100))
            )  # Scale size by citations
            node_color.append(citations)

        # Prepare edge data
        edge_x = []
        edge_y = []
        edge_text = []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

            weight = G.edges[edge]["weight"]
            edge_text.append(f"Shared citations: {weight}")

        # Create Plotly figure
        fig = go.Figure()

        # Add edges
        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=2, color="lightgray"),
                hoverinfo="none",
                mode="lines",
                name="Co-citations",
            )
        )

        # Add nodes
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                marker=dict(
                    size=node_size,
                    color=node_color,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Total Citations"),
                    line=dict(width=2, color="white"),
                ),
                text=[node.replace("dataset_", "") for node in G.nodes()],
                textposition="middle center",
                textfont=dict(size=8),
                hovertext=node_text,
                hoverinfo="text",
                name="Datasets",
            )
        )

        fig.update_layout(
            title="BIDS Dataset Co-Citation Network<br>Datasets connected by shared citations",
            title_font_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Node size = total dataset citations<br>Edges = shared citations between datasets",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=12),
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
        )

        # Save interactive HTML
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        logger.info(f"Interactive co-citation network saved to {output_path}")

    def create_interactive_author_network(
        self, output_path: Path, min_datasets: int = 5
    ) -> None:
        """
        Create an interactive author-dataset bipartite network.

        Args:
            output_path: Path to save HTML file
            min_datasets: Minimum datasets per author
        """
        G = self.get_author_dataset_network(min_datasets)

        if G.number_of_nodes() == 0:
            logger.warning("No author network data found")
            return

        # Use bipartite layout
        author_nodes = [n for n in G.nodes() if G.nodes[n]["node_type"] == "author"]
        dataset_nodes = [n for n in G.nodes() if G.nodes[n]["node_type"] == "dataset"]

        pos = {}
        # Position authors on left, datasets on right
        for i, node in enumerate(author_nodes):
            pos[node] = (0, i)
        for i, node in enumerate(dataset_nodes):
            pos[node] = (2, i * len(author_nodes) / len(dataset_nodes))

        # Improve layout with spring
        pos = nx.spring_layout(
            G,
            pos=pos,
            fixed=author_nodes + dataset_nodes[: len(author_nodes)],
            iterations=20,
            k=1,
        )

        # Prepare data
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_symbol = []
        node_size = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = G.nodes[node]
            if node_data["node_type"] == "author":
                name = node_data["name"]
                num_datasets = node_data.get("num_datasets", 0)
                impact = node_data.get("total_impact", 0)
                node_text.append(
                    f"Author: {name}<br>Datasets: {num_datasets}<br>Impact: {impact}"
                )
                node_color.append("red")
                node_symbol.append("circle")
                node_size.append(max(15, min(40, num_datasets * 2)))
            else:
                name = node_data["name"]
                node_text.append(f"Dataset: {name}")
                node_color.append("blue")
                node_symbol.append("square")
                node_size.append(10)

        # Edge data
        edge_x = []
        edge_y = []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        # Create figure
        fig = go.Figure()

        # Add edges
        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=1, color="lightgray"),
                hoverinfo="none",
                mode="lines",
                name="Citations",
            )
        )

        # Add nodes
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers",
                marker=dict(
                    size=node_size,
                    color=node_color,
                    symbol=node_symbol,
                    line=dict(width=2, color="white"),
                ),
                hovertext=node_text,
                hoverinfo="text",
                name="Network",
            )
        )

        fig.update_layout(
            title="Author-Dataset Citation Network<br>Red circles = Authors, Blue squares = Datasets",
            title_font_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        logger.info(f"Interactive author network saved to {output_path}")


def create_static_network_graphs(results_dir: Path, output_dir: Path) -> None:
    """
    Create static network visualizations using exported CSV data.

    Args:
        results_dir: Directory with CSV exports
        output_dir: Directory to save network graphs
    """
    # Load co-citation data
    co_citations_path = results_dir / "csv_exports" / "dataset_co_citations.csv"
    if not co_citations_path.exists():
        logger.warning(f"Co-citations file not found: {co_citations_path}")
        return

    co_citations_df = pd.read_csv(co_citations_path)

    # Create NetworkX graph from co-citations
    G = nx.Graph()

    for _, row in co_citations_df.iterrows():
        G.add_node(
            row["dataset1"],
            name=row["dataset1_name"],
            total_citations=row["dataset1_total_citations"],
        )
        G.add_node(
            row["dataset2"],
            name=row["dataset2_name"],
            total_citations=row["dataset2_total_citations"],
        )
        G.add_edge(row["dataset1"], row["dataset2"], weight=row["shared_citations"])

    # Create layout
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Plot with matplotlib
    import matplotlib.pyplot as plt

    plt.figure(figsize=(16, 12))

    # Draw edges with varying thickness
    edges = G.edges()
    weights = [G[u][v]["weight"] for u, v in edges]
    nx.draw_networkx_edges(
        G, pos, width=[w * 0.5 for w in weights], alpha=0.6, edge_color="gray"
    )

    # Draw nodes with varying size
    node_sizes = [G.nodes[node].get("total_citations", 100) / 10 for node in G.nodes()]
    nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes, node_color="lightblue", alpha=0.8
    )

    # Add labels for significant nodes
    large_nodes = [
        node for node in G.nodes() if G.nodes[node].get("total_citations", 0) > 500
    ]
    labels = {node: node for node in large_nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)

    plt.title(
        "BIDS Dataset Co-Citation Network\n(Node size = total citations, Edge thickness = shared citations)",
        fontsize=16,
        fontweight="bold",
    )
    plt.axis("off")
    plt.tight_layout()

    output_path = output_dir / "dataset_co_citation_network.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Static co-citation network saved to {output_path}")
