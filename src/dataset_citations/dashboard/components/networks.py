"""
Network visualization component for dashboard.
"""

from pathlib import Path
from typing import Any, Dict, Optional

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
                        "background-color": "#FFA500",  # Orange like in reference
                        "width": "mapData(citations, 0, 80, 5, 25)",  # Much smaller: 5-25 pixels
                        "height": "mapData(citations, 0, 80, 5, 25)",
                        "border-width": 1,
                        "border-color": "#FF8C00",
                    },
                },
                {
                    "selector": "node[type='citation']",
                    "style": {
                        "background-color": "#FFA500",  # Orange for citations too
                        "width": "mapData(citations, 0, 600, 8, 32)",  # Larger: 8-32 pixels
                        "height": "mapData(citations, 0, 600, 8, 32)",
                        "border-width": 1,
                        "border-color": "#FF8C00",
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
                        "background-color": "#0074D9",  # Blue when selected
                        "border-width": 4,
                        "border-color": "#001f3f",
                    },
                },
                {
                    "selector": "node:active",
                    "style": {
                        "overlay-opacity": 0.2,
                        "overlay-color": "#0074D9",
                        "overlay-padding": 10,
                    },
                },
            ],
            "layout": {"name": "preset", "fit": True, "padding": 50},
        }
