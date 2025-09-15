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
        # Get top datasets from network analysis
        network_data = data.get("network_analysis", {})
        dataset_popularity = network_data.get("dataset_popularity", [])

        # Sort by high confidence citations and get top 20
        top_datasets = sorted(
            [
                d
                for d in dataset_popularity
                if int(d.get("high_confidence_citations", 0) or 0) > 0
            ],
            key=lambda x: int(x.get("high_confidence_citations", 0) or 0),
            reverse=True,
        )[:20]

        return {
            "title": "Dataset Analysis Details",
            "content": {
                "total_datasets": stats["summary"].get("unique_datasets", 0),
                "with_citations": stats["summary"].get("unique_datasets", 0),
                "coverage": "100%",
                "top_datasets": top_datasets,
                "description": "Datasets are analyzed from the BIDS (Brain Imaging Data Structure) repository, with citation data collected from Google Scholar and filtered by confidence scores.",
            },
        }

    def _generate_citation_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate citation details modal content."""
        high_conf = stats["summary"].get("high_confidence_citations", 0)
        total = stats["summary"].get("total_citations", 0)
        low_conf = total - high_conf
        percentage = round((high_conf / total * 100) if total > 0 else 0, 1)

        return {
            "title": "Citation Analysis",
            "content": {
                "high_confidence": high_conf,
                "low_confidence": low_conf,
                "total": total,
                "percentage": percentage,
                "threshold": 0.4,
            },
        }

    def _generate_bridge_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate bridge papers modal content."""
        network_data = data.get("network_analysis", {})
        bridge_papers = network_data.get("bridge_papers", [])

        # Sort by number of datasets bridged and get top 20
        top_papers = sorted(
            bridge_papers,
            key=lambda x: int(x.get("num_datasets_bridged", 0)),
            reverse=True,
        )[:20]

        return {
            "title": "Research Bridge Papers",
            "content": {
                "total": len(bridge_papers),
                "top_papers": top_papers,
                "description": "Bridge papers are publications that cite multiple BIDS datasets, connecting different research areas and facilitating cross-domain knowledge transfer in neuroscience.",
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
