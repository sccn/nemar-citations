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

        # Count datasets with citations
        total_datasets = len(dataset_popularity)

        # Count datasets with actual high-confidence citations
        datasets_with_high_conf = len(
            [
                d
                for d in dataset_popularity
                if int(d.get("high_confidence_citations", 0) or 0) > 0
            ]
        )

        # Calculate coverage percentage based on high-confidence citations
        coverage = (
            f"{(datasets_with_high_conf / total_datasets * 100):.0f}%"
            if total_datasets > 0
            else "0%"
        )

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
                "total_datasets": total_datasets,
                "with_citations": datasets_with_high_conf,
                "coverage": coverage,
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

        # Get top cited papers from citation impact rankings
        network_data = data.get("network_analysis", {})
        citation_rankings = network_data.get("citation_impact_rankings", [])

        # Sort by citation impact and get top 5
        top_citations = sorted(
            citation_rankings,
            key=lambda x: int(x.get("citation_impact", 0)),
            reverse=True,
        )[:5]

        return {
            "title": "Citation Analysis",
            "content": {
                "high_confidence": high_conf,
                "low_confidence": low_conf,
                "total": total,
                "percentage": percentage,
                "threshold": 0.4,
                "quality_rate": percentage,  # Same as percentage for high-confidence
                "top_citations": top_citations,
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
            "title": "Confidence Threshold Information",
            "content": {
                "threshold": 0.4,
                "description": "Citations must have a confidence score of 0.4 or higher to be included in analysis.",
                "model": "Qwen3-Embedding-0.6B",
                "method": "Sentence-transformer similarity",
                "comparison": "Dataset descriptions vs citation abstracts",
                "validation": "Manual review sample",
                "quality_rate": stats["summary"].get("high_confidence_citations", 0)
                / stats["summary"].get("total_citations", 1)
                * 100
                if stats["summary"].get("total_citations", 0) > 0
                else 0,
            },
        }
