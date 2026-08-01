"""
Chart generation component for dashboard.
"""

from typing import Any


class ChartGenerator:
    """Generate Plotly chart configurations."""

    def generate_all_charts(self, data: dict[str, Any]) -> dict[str, Any]:
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

    def _generate_quality_chart(self, data: dict[str, Any]) -> dict[str, Any]:
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

    def _generate_growth_chart(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate citation growth timeline chart.

        Reads `temporal_analysis.temporal_summary` (list of per-year rows with
        `year` and `high_confidence_citations`), sorts by year, and emits a
        cumulative series whose endpoint matches the
        `summary_stats.high_confidence_citations` headline KPI.

        Closes #77: previously this returned a hardcoded array that capped
        near 1,200 even though the headline showed ~14k. The first fix
        bound the chart to `total_citations` instead, but `total_citations`
        is all citations regardless of confidence — distinct from the
        headline's high-confidence count. Binding to
        `high_confidence_citations` keeps the two quantities consistent
        (review finding on PR #106).
        """
        temporal = data.get("temporal_analysis", {})
        rows = temporal.get("temporal_summary", [])

        parsed: list[tuple[int, int]] = []
        for row in rows:
            try:
                year = int(row.get("year", 0))
                # Per-year high-confidence count so the cumulative endpoint
                # reconciles with summary_stats.high_confidence_citations.
                # `total_citations` (the previous binding) would over-count.
                count = int(row.get("high_confidence_citations", 0))
            except (TypeError, ValueError):
                continue
            if year <= 0:
                continue
            parsed.append((year, count))
        parsed.sort(key=lambda yc: yc[0])

        years: list[int] = []
        cumulative: list[int] = []
        running = 0
        for year, count in parsed:
            running += count
            years.append(year)
            cumulative.append(running)

        return {
            "type": "scatter",
            "data": {
                "x": years,
                "y": cumulative,
                "mode": "lines+markers",
            },
        }

    def _generate_modality_chart(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate data modality pie chart."""
        return {
            "type": "pie",
            "data": {
                "values": [120, 45, 25],
                "labels": ["EEG", "MEG", "iEEG"],
                "hole": 0.4,
            },
        }
