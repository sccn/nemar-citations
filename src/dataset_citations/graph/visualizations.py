"""
Dataset Citations Visualization Module

This module provides visualization functions for citation analysis results,
creating publication-ready charts and network diagrams.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from pathlib import Path
from typing import Tuple
import logging

# Set up matplotlib for better-looking plots
plt.style.use("default")
sns.set_palette("husl")

logger = logging.getLogger(__name__)


def create_temporal_growth_chart(
    temporal_df: pd.DataFrame,
    output_path: Path,
    title: str = "BIDS Dataset Citation Growth Over Time",
    figsize: Tuple[int, int] = (12, 8),
) -> None:
    """
    Create a temporal growth chart showing citation evolution over years.

    Args:
        temporal_df: DataFrame with temporal evolution data
        output_path: Path to save the visualization
        title: Chart title
        figsize: Figure size (width, height)
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])

    # Main growth chart
    years = temporal_df["year"]
    citations = temporal_df["citations_count"]
    datasets_active = temporal_df["datasets_with_citations"]

    # Citation count line with area fill
    ax1.fill_between(years, citations, alpha=0.3, color="#2E86AB", label="Citations")
    ax1.plot(years, citations, marker="o", linewidth=3, color="#2E86AB", markersize=6)

    # Add dataset count as secondary line
    ax1_twin = ax1.twinx()
    ax1_twin.plot(
        years,
        datasets_active,
        marker="s",
        linewidth=2,
        color="#F24236",
        alpha=0.8,
        markersize=5,
        label="Active Datasets",
    )

    # Styling for main plot
    ax1.set_xlabel("Year", fontsize=12, fontweight="bold")
    ax1.set_ylabel(
        "Number of Citations", fontsize=12, fontweight="bold", color="#2E86AB"
    )
    ax1_twin.set_ylabel(
        "Datasets with Citations", fontsize=12, fontweight="bold", color="#F24236"
    )
    ax1.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax1.grid(True, alpha=0.3)

    # Add growth annotations for key years
    if len(temporal_df) > 5:
        recent_year = temporal_df.iloc[-2]  # Second to last (2024)
        early_year = temporal_df.iloc[0]  # First year

        growth_rate = (
            (recent_year["citations_count"] / early_year["citations_count"])
            ** (1 / (recent_year["year"] - early_year["year"]))
            - 1
        ) * 100

        ax1.annotate(
            f"{growth_rate:.0f}% annual growth\n({early_year['year']}-{recent_year['year']})",
            xy=(recent_year["year"], recent_year["citations_count"]),
            xytext=(0.7, 0.85),
            textcoords="axes fraction",
            fontsize=11,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2"),
        )

    # Confidence score trend (bottom subplot)
    if "avg_confidence" in temporal_df.columns:
        ax2.plot(
            years,
            temporal_df["avg_confidence"],
            marker="d",
            color="#A23B72",
            linewidth=2,
            markersize=4,
        )
        ax2.set_xlabel("Year", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Avg Confidence Score", fontsize=11, fontweight="bold")
        ax2.set_title("Citation Quality Over Time", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0.4, 1.0)  # Confidence score range

    # Add legends
    ax1.legend(loc="upper left")
    ax1_twin.legend(loc="upper right")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Temporal growth chart saved to {output_path}")


def create_citation_impact_dashboard(
    impact_df: pd.DataFrame,
    popularity_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 10,
    figsize: Tuple[int, int] = (15, 10),
) -> None:
    """
    Create a comprehensive citation impact dashboard.

    Args:
        impact_df: DataFrame with citation impact rankings
        popularity_df: DataFrame with dataset popularity data
        output_path: Path to save the visualization
        top_n: Number of top items to show
        figsize: Figure size (width, height)
    """
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # Top Citations by Impact (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    top_citations = impact_df.head(top_n)

    # Truncate long titles for display
    titles = [
        title[:50] + "..." if len(title) > 50 else title
        for title in top_citations["citation_title"]
    ]

    bars1 = ax1.barh(
        range(len(titles)),
        top_citations["citation_impact"],
        color=sns.color_palette("viridis", len(titles)),
    )
    ax1.set_yticks(range(len(titles)))
    ax1.set_yticklabels(titles, fontsize=9)
    ax1.set_xlabel("Citation Impact (cited_by count)", fontsize=11, fontweight="bold")
    ax1.set_title(f"Top {top_n} Most Cited Papers", fontsize=12, fontweight="bold")
    ax1.grid(axis="x", alpha=0.3)

    # Add value labels on bars
    for i, bar in enumerate(bars1):
        width = bar.get_width()
        ax1.text(
            width + width * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width)}",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    # Top Datasets by Popularity (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    top_datasets = popularity_df.nlargest(top_n, "cumulative_citations")

    bars2 = ax2.barh(
        range(len(top_datasets)),
        top_datasets["cumulative_citations"],
        color=sns.color_palette("plasma", len(top_datasets)),
    )
    ax2.set_yticks(range(len(top_datasets)))
    ax2.set_yticklabels(top_datasets["dataset_id"], fontsize=10)
    ax2.set_xlabel("Total Cumulative Citations", fontsize=11, fontweight="bold")
    ax2.set_title(f"Top {top_n} Most Popular Datasets", fontsize=12, fontweight="bold")
    ax2.grid(axis="x", alpha=0.3)

    # Add value labels
    for i, bar in enumerate(bars2):
        width = bar.get_width()
        ax2.text(
            width + width * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width)}",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    # Citation Impact Distribution (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(
        impact_df["citation_impact"],
        bins=20,
        alpha=0.7,
        color="skyblue",
        edgecolor="black",
    )
    ax3.set_xlabel("Citation Impact", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Number of Papers", fontsize=11, fontweight="bold")
    ax3.set_title("Citation Impact Distribution", fontsize=12, fontweight="bold")
    ax3.grid(alpha=0.3)

    # Dataset Citation Count Distribution (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.hist(
        popularity_df["total_citations"],
        bins=20,
        alpha=0.7,
        color="lightcoral",
        edgecolor="black",
    )
    ax4.set_xlabel("Number of Citations per Dataset", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Number of Datasets", fontsize=11, fontweight="bold")
    ax4.set_title("Dataset Citation Count Distribution", fontsize=12, fontweight="bold")
    ax4.grid(alpha=0.3)

    plt.suptitle(
        "BIDS Dataset Citation Impact Analysis", fontsize=16, fontweight="bold", y=0.98
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Citation impact dashboard saved to {output_path}")


def create_author_network_diagram(
    author_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 20,
    figsize: Tuple[int, int] = (14, 10),
) -> None:
    """
    Create a network diagram showing influential authors and their dataset connections.

    Args:
        author_df: DataFrame with author influence data
        output_path: Path to save the visualization
        top_n: Number of top authors to include
        figsize: Figure size (width, height)
    """
    plt.figure(figsize=figsize)

    # Select top authors
    top_authors = author_df.head(top_n)

    # Create network graph
    G = nx.Graph()

    # Add nodes and edges
    for _, author_row in top_authors.iterrows():
        author_name = author_row["author"]
        datasets = (
            eval(author_row["datasets_cited"])
            if isinstance(author_row["datasets_cited"], str)
            else author_row["datasets_cited"]
        )

        # Add author node
        G.add_node(
            author_name,
            node_type="author",
            num_datasets=author_row["num_datasets_cited"],
            impact=author_row["total_citation_impact"],
        )

        # Add dataset nodes and connections
        for dataset in datasets[:5]:  # Limit to top 5 datasets per author for clarity
            G.add_node(dataset, node_type="dataset")
            G.add_edge(author_name, dataset)

    # Layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Separate node types
    author_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "author"]
    dataset_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "dataset"
    ]

    # Draw dataset nodes (smaller, gray)
    nx.draw_networkx_nodes(
        G, pos, nodelist=dataset_nodes, node_color="lightgray", node_size=200, alpha=0.6
    )

    # Draw author nodes (larger, colored by number of datasets)
    author_sizes = [G.nodes[node].get("num_datasets", 1) * 50 for node in author_nodes]
    author_colors = [G.nodes[node].get("num_datasets", 1) for node in author_nodes]

    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=author_nodes,
        node_color=author_colors,
        node_size=author_sizes,
        cmap="viridis",
        alpha=0.8,
    )

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.3, width=0.5)

    # Add labels for top authors only
    author_labels = {
        node: node.split(",")[0] if "," in node else node[:15]
        for node in author_nodes[:10]
    }  # Top 10 authors only
    nx.draw_networkx_labels(
        G, pos, labels=author_labels, font_size=8, font_weight="bold"
    )

    plt.title(
        "Influential Authors and Their Dataset Citations Network",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    plt.figtext(
        0.02,
        0.02,
        "Node size = number of datasets cited by author\nColor intensity = citation influence",
        fontsize=10,
        style="italic",
    )

    plt.axis("off")
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Author network diagram saved to {output_path}")


def create_dataset_popularity_ranking(
    popularity_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 15,
    figsize: Tuple[int, int] = (12, 8),
) -> None:
    """
    Create a dataset popularity ranking visualization.

    Args:
        popularity_df: DataFrame with dataset popularity data
        output_path: Path to save the visualization
        top_n: Number of top datasets to show
        figsize: Figure size (width, height)
    """
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=figsize, gridspec_kw={"width_ratios": [2, 1]}
    )

    # Top datasets ranking (left panel)
    top_datasets = popularity_df.nlargest(top_n, "cumulative_citations")

    colors = sns.color_palette("rocket", len(top_datasets))
    bars = ax1.barh(
        range(len(top_datasets)), top_datasets["cumulative_citations"], color=colors
    )

    ax1.set_yticks(range(len(top_datasets)))
    ax1.set_yticklabels(top_datasets["dataset_id"], fontsize=10)
    ax1.set_xlabel("Total Cumulative Citations", fontsize=12, fontweight="bold")
    ax1.set_title(
        f"Top {top_n} BIDS Datasets by Popularity", fontsize=14, fontweight="bold"
    )
    ax1.grid(axis="x", alpha=0.3)

    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax1.text(
            width + width * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width)}",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
        )

    # Popularity distribution (right panel)
    ax2.hist(
        popularity_df["cumulative_citations"],
        bins=30,
        alpha=0.7,
        color="steelblue",
        edgecolor="black",
    )
    ax2.set_xlabel("Total Cumulative Citations", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Number of Datasets", fontsize=11, fontweight="bold")
    ax2.set_title("Popularity Distribution", fontsize=12, fontweight="bold")
    ax2.grid(alpha=0.3)

    # Add summary statistics
    mean_citations = popularity_df["cumulative_citations"].mean()
    median_citations = popularity_df["cumulative_citations"].median()

    ax2.axvline(
        mean_citations,
        color="red",
        linestyle="--",
        alpha=0.7,
        label=f"Mean: {mean_citations:.0f}",
    )
    ax2.axvline(
        median_citations,
        color="orange",
        linestyle="--",
        alpha=0.7,
        label=f"Median: {median_citations:.0f}",
    )
    ax2.legend()

    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"Dataset popularity ranking saved to {output_path}")
