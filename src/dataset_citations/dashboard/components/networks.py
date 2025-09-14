"""
Network visualization component for dashboard.
"""

from typing import Dict, Any


class NetworkGenerator:
    """Generate network visualization configurations."""

    def generate_networks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate network visualization data.

        Args:
            data: Aggregated data from DataAggregator

        Returns:
            Dictionary containing network configurations
        """
        return {
            "dataset_network": self._generate_dataset_network(data),
            "citation_network": self._generate_citation_network(data),
        }

    def _generate_dataset_network(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dataset network configuration."""
        network_data = data.get("network_analysis", {})
        popularity = network_data.get("dataset_popularity", [])

        nodes = []
        for i, dataset in enumerate(popularity[:50]):  # Top 50 datasets
            nodes.append(
                {
                    "id": dataset.get("dataset_id", f"ds{i}"),
                    "label": dataset.get("dataset_name", ""),
                    "citations": int(dataset.get("citations", 0)),
                }
            )

        return {
            "nodes": nodes,
            "edges": [],  # No edges for dataset network in NEMAR dashboard
            "layout": "preset",  # Use UMAP coordinates
        }

    def _generate_citation_network(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate citation network configuration."""
        network_data = data.get("network_analysis", {})
        citations = network_data.get("citation_impact_rankings", [])

        nodes = []
        for i, citation in enumerate(citations[:100]):  # Top 100 citations
            nodes.append(
                {
                    "id": f"citation_{i}",
                    "title": citation.get("citation_title", ""),
                    "impact": int(citation.get("citation_impact", 0)),
                }
            )

        return {
            "nodes": nodes,
            "edges": [],  # Would be populated from similarity data
            "layout": "preset",
        }
