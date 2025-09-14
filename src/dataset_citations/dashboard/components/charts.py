"""
Chart generation component for dashboard.
"""

from typing import Dict, Any


class ChartGenerator:
    """Generate Plotly chart configurations."""

    def generate_all_charts(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate all chart configurations.

        Args:
            data: Aggregated data from DataAggregator

        Returns:
            Dictionary containing chart configurations
        """
        return {
            "quality_chart": self._generate_quality_chart(data),
            "growth_chart": self._generate_growth_chart(data),
            "modality_chart": self._generate_modality_chart(data),
        }

    def _generate_quality_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate citation quality bar chart configuration."""
        stats = data.get("summary_stats", {})
        high_conf = stats.get("high_confidence_citations", 0)
        total = stats.get("total_citations", 0)
        low_conf = total - high_conf

        return {
            "type": "bar",
            "data": {
                "x": ["High-Confidence\\n(≥0.4)", "Low-Confidence\\n(<0.4)"],
                "y": [high_conf, low_conf],
                "colors": ["#E94B3C", "#BDC3C7"],
            },
        }

    def _generate_growth_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate citation growth timeline chart."""
        # This would use temporal analysis data
        return {
            "type": "scatter",
            "data": {
                "x": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
                "y": [20, 65, 150, 370, 650, 950, 1040, 1140],
                "mode": "lines+markers",
            },
        }

    def _generate_modality_chart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data modality pie chart."""
        return {
            "type": "pie",
            "data": {
                "values": [120, 45, 25],
                "labels": ["EEG", "MEG", "iEEG"],
                "hole": 0.4,
            },
        }
