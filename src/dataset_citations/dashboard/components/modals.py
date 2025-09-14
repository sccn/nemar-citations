"""
Modal content generation component for dashboard.
"""

from typing import Dict, Any


class ModalGenerator:
    """Generate modal dialog content."""

    def generate_modals(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate modal content for detail views.

        Args:
            data: Aggregated data from DataAggregator
            stats: Generated statistics

        Returns:
            Dictionary containing modal configurations
        """
        return {
            "datasets": self._generate_dataset_modal(data, stats),
            "citations": self._generate_citation_modal(data, stats),
            "bridges": self._generate_bridge_modal(data, stats),
            "threshold": self._generate_threshold_modal(stats),
        }

    def _generate_dataset_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate dataset details modal content."""
        return {
            "title": "Dataset Analysis Details",
            "content": {
                "total_datasets": stats["summary"]["total_citations"],
                "with_citations": stats["summary"]["datasets_with_citations"],
                "coverage": "100%",
                "description": "Datasets are analyzed from the BIDS (Brain Imaging Data Structure) repository, with citation data collected from Google Scholar and filtered by confidence scores.",
            },
        }

    def _generate_citation_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate citation details modal content."""
        return {
            "title": "Citation Details",
            "content": {
                "high_confidence": stats["cards"][1]["value"],
                "total": stats["summary"]["total_citations"],
                "threshold": stats["cards"][3]["value"],
            },
        }

    def _generate_bridge_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate bridge papers modal content."""
        network_data = data.get("network_analysis", {})
        bridge_papers = network_data.get("bridge_papers", [])

        return {
            "title": "Research Bridge Papers",
            "content": {
                "total": len(bridge_papers),
                "top_papers": bridge_papers[:5] if bridge_papers else [],
            },
        }

    def _generate_threshold_modal(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Generate confidence threshold explanation modal."""
        return {
            "title": "Confidence Scoring",
            "content": {
                "threshold": 0.4,
                "description": "Citations are scored using AI-based relevance matching. Only citations with confidence ≥0.4 are included in the analysis.",
            },
        }
