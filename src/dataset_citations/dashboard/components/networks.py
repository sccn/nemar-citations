"""
Network visualization component for dashboard.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from .network_data import NetworkDataExtractor


class NetworkGenerator:
    """Generate network visualization configurations."""

    def __init__(self, embeddings_dir: Optional[Path] = None):
        """
        Initialize the network generator.

        Args:
            embeddings_dir: Path to embeddings directory
        """
        self.data_extractor = NetworkDataExtractor(embeddings_dir)

    def generate_networks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate network visualization data with UMAP coordinates.

        Args:
            data: Aggregated data from DataAggregator

        Returns:
            Dictionary containing network configurations with Cytoscape.js format
        """
        # Use the new data extractor to get UMAP-enriched network data
        network_data = self.data_extractor.prepare_network_data(data)

        return {
            "dataset_network": network_data["dataset_network"],
            "citation_network": network_data["citation_network"],
            "umap_bounds": network_data["umap_bounds"],
            "cytoscape_config": self._generate_cytoscape_config(),
        }

    def _generate_cytoscape_config(self) -> Dict[str, Any]:
        """Generate Cytoscape.js configuration."""
        return {
            "style": [
                {
                    "selector": "node[type='dataset']",
                    "style": {
                        "background-color": "#4CAF50",
                        "label": "data(label)",
                        "width": "mapData(citations, 0, 100, 20, 60)",
                        "height": "mapData(citations, 0, 100, 20, 60)",
                        "font-size": "10px",
                        "text-valign": "center",
                        "text-halign": "center",
                        "text-outline-color": "#fff",
                        "text-outline-width": 2,
                        "text-wrap": "wrap",
                        "text-max-width": "80px",
                    },
                },
                {
                    "selector": "node[type='citation']",
                    "style": {
                        "background-color": "#2196F3",
                        "label": "data(label)",
                        "width": "mapData(impact, 0, 10, 15, 40)",
                        "height": "mapData(impact, 0, 10, 15, 40)",
                        "font-size": "9px",
                        "text-valign": "center",
                        "text-halign": "center",
                        "text-outline-color": "#fff",
                        "text-outline-width": 1,
                        "text-wrap": "wrap",
                        "text-max-width": "100px",
                    },
                },
                {
                    "selector": "edge",
                    "style": {
                        "width": "mapData(weight, 1, 10, 1, 5)",
                        "line-color": "#ccc",
                        "target-arrow-color": "#ccc",
                        "curve-style": "bezier",
                        "opacity": 0.6,
                    },
                },
                {
                    "selector": "node:selected",
                    "style": {
                        "background-color": "#FF5722",
                        "border-width": 3,
                        "border-color": "#000",
                    },
                },
            ],
            "layout": {"name": "preset", "fit": True, "padding": 50},
        }
