"""
Statistics generation component for dashboard.
"""

from typing import Any, Dict


class StatisticsGenerator:
    """Generate statistics cards and summary information."""

    def generate_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics from aggregated data.

        Args:
            data: Aggregated data from DataAggregator

        Returns:
            Dictionary containing statistics for display
        """
        stats = data.get("summary_stats", {})

        return {
            "cards": [
                {
                    "id": "datasets",
                    "icon": "fas fa-database",
                    "value": stats.get("total_datasets", 0),
                    "label": "Datasets Analyzed",
                    "detail": "Click for details",
                },
                {
                    "id": "citations",
                    "icon": "fas fa-quote-left",
                    "value": stats.get("high_confidence_citations", 0),
                    "label": "High-Confidence Citations",
                    "detail": f"*Confidence ≥{stats.get('confidence_threshold', 0.4)} • Click for details",
                },
                {
                    "id": "bridges",
                    "icon": "fas fa-bridge",
                    "value": stats.get("bridge_papers", 0),
                    "label": "Research Bridge Papers",
                    "detail": "Click for details",
                },
                {
                    "id": "threshold",
                    "icon": "fas fa-filter",
                    "value": f"≥{stats.get('confidence_threshold', 0.4)}",
                    "label": "Confidence Threshold",
                    "detail": "Click for details",
                },
            ],
            "summary": {
                "total_citations": stats.get("total_citations", 0),
                "high_confidence_citations": stats.get("high_confidence_citations", 0),
                "analysis_date": stats.get("analysis_date", ""),
                "datasets_with_citations": self._count_datasets_with_citations(data),
                "unique_datasets": stats.get("total_datasets", 0),
            },
        }

    def _count_datasets_with_citations(self, data: Dict[str, Any]) -> int:
        """Count datasets that have at least one citation."""
        # This would be calculated from the actual data
        return data.get("summary_stats", {}).get("total_datasets", 0)
