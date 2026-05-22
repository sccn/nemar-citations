"""Tests for the dashboard chart generator.

Locks in the fix for issue #77: the Growth Timeline chart used to return a
hardcoded series (capping near 1,200) that ignored the real temporal data.
The chart now reads `temporal_analysis.temporal_summary` and emits a
cumulative series whose endpoint matches the headline count.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dataset_citations.dashboard.components.charts import ChartGenerator
from dataset_citations.dashboard.templates.components.charts import (
    generate_chart_javascript,
)


def _build_temporal_data(rows: list[dict[str, str]]) -> dict[str, dict]:
    """Wrap CSV-style temporal rows in the aggregator's data shape."""
    return {"temporal_analysis": {"temporal_summary": rows}}


def test_growth_chart_reads_high_confidence_citations():
    """The growth chart must compute cumulative `high_confidence_citations`
    per year so the endpoint reconciles with the headline KPI."""
    data = _build_temporal_data(
        [
            {
                "year": "2018",
                "total_citations": "200",
                "high_confidence_citations": "100",
                "unique_datasets": "5",
            },
            {
                "year": "2019",
                "total_citations": "350",
                "high_confidence_citations": "200",
                "unique_datasets": "8",
            },
            {
                "year": "2020",
                "total_citations": "500",
                "high_confidence_citations": "300",
                "unique_datasets": "12",
            },
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2018, 2019, 2020]
    # Cumulative HIGH-CONF (100, 300, 600), NOT total_citations (200, 550, 1050)
    # and definitely NOT unique_datasets (5, 13, 25).
    assert chart["data"]["y"] == [100, 300, 600]


def test_growth_chart_endpoint_matches_high_confidence_headline():
    """The cumulative endpoint must equal `summary_stats.high_confidence_citations`.

    This is the exact reconciliation #77 was about: headline read 14k+ but
    chart capped at ~1.2k. The PR-#106 reviewer flagged that the initial
    fix bound to `total_citations` instead, which is a different quantity
    (all citations regardless of confidence). The chart now reads the
    per-year `high_confidence_citations` so the running sum matches the
    headline by construction.
    """
    rows = [
        {"year": "2018", "total_citations": "220", "high_confidence_citations": "120"},
        {"year": "2019", "total_citations": "750", "high_confidence_citations": "480"},
        {
            "year": "2020",
            "total_citations": "1800",
            "high_confidence_citations": "1100",
        },
        {
            "year": "2021",
            "total_citations": "3600",
            "high_confidence_citations": "2400",
        },
        {
            "year": "2022",
            "total_citations": "4500",
            "high_confidence_citations": "3500",
        },
        {
            "year": "2023",
            "total_citations": "4700",
            "high_confidence_citations": "3800",
        },
        {
            "year": "2024",
            "total_citations": "3300",
            "high_confidence_citations": "2592",
        },
    ]
    expected_headline = sum(int(r["high_confidence_citations"]) for r in rows)  # 13,992

    chart = ChartGenerator()._generate_growth_chart(_build_temporal_data(rows))

    assert chart["data"]["y"][-1] == expected_headline
    assert chart["data"]["x"][-1] == 2024
    # The endpoint must NOT pick up `total_citations` (which would be ~3000
    # higher and over-count by including low-confidence citations).
    assert chart["data"]["y"][-1] != sum(int(r["total_citations"]) for r in rows)


def test_growth_chart_sorts_by_year_when_csv_is_unordered():
    """CSV row order is not guaranteed; we sort by year before cumulating."""
    data = _build_temporal_data(
        [
            {"year": "2020", "high_confidence_citations": "50", "unique_datasets": "3"},
            {"year": "2018", "high_confidence_citations": "10", "unique_datasets": "1"},
            {"year": "2019", "high_confidence_citations": "30", "unique_datasets": "2"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2018, 2019, 2020]
    assert chart["data"]["y"] == [10, 40, 90]


def test_growth_chart_does_not_fall_back_to_other_fields():
    """Regression guard: chart must read `high_confidence_citations`. It must
    NOT fall back to `total_citations` (over-counts by including low-conf
    citations) or `unique_datasets` (the original 10x-smaller smell from #77).
    """
    data = _build_temporal_data(
        [
            {
                "year": "2023",
                "total_citations": "8000",
                "high_confidence_citations": "5000",
                "unique_datasets": "50",
            },
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["y"] == [5000]
    assert chart["data"]["y"] != [8000]
    assert chart["data"]["y"] != [50]


def test_growth_chart_handles_missing_temporal_data():
    """An empty payload yields empty arrays, NOT a hardcoded misleading curve."""
    chart = ChartGenerator()._generate_growth_chart({})

    assert chart["data"]["x"] == []
    assert chart["data"]["y"] == []


def test_growth_chart_skips_malformed_rows():
    """Rows with non-integer years/counts are skipped, not silently mangled."""
    data = _build_temporal_data(
        [
            {"year": "2020", "high_confidence_citations": "100"},
            {"year": "not-a-year", "high_confidence_citations": "999"},
            {"year": "2021", "high_confidence_citations": "garbage"},
            {"year": "2022", "high_confidence_citations": "200"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2020, 2022]
    assert chart["data"]["y"] == [100, 300]


def test_chart_javascript_embeds_real_growth_series():
    """The HTML/JS template must embed the computed series, not defaults."""
    rows = [
        {"year": "2020", "high_confidence_citations": "1000", "unique_datasets": "10"},
        {"year": "2021", "high_confidence_citations": "4000", "unique_datasets": "40"},
    ]
    data = _build_temporal_data(rows)
    charts = ChartGenerator().generate_all_charts(data)

    js = generate_chart_javascript(stats={}, charts=charts)

    # The embedded series should be the cumulative growth (1000, 5000), not
    # the old hardcoded [20, 65, 150, 370, ...] fallback.
    assert "[1000, 5000]" in js or "[1000,5000]" in js
    assert "[20, 65, 150, 370, 650, 950, 1040, 1140]" not in js


def test_chart_javascript_falls_back_to_empty_arrays_not_hardcoded_curve():
    """With no temporal data, the JS must NOT contain the old fake curve."""
    js = generate_chart_javascript(stats={}, charts={})

    # Locate the growth chart x/y plot calls and inspect their arguments.
    # The old defaults were x=[2018..2025], y=[20, 65, 150, ...].
    forbidden_y_sequences = [
        "[20, 65, 150",
        "[20,65,150",
    ]
    for needle in forbidden_y_sequences:
        assert needle not in js, (
            f"Growth chart still embeds hardcoded fallback series: {needle!r}"
        )


def test_smoke_dashboard_payload_roundtrip(tmp_path: Path):
    """Smoke test: a realistic payload flows through generate_chart_javascript
    without raising and the growth series ends at the headline total.

    Rows include both `total_citations` (all citations) and
    `high_confidence_citations` (the field the chart now sums) so the test
    proves the binding actually reads the right column — endpoint is
    13,992 (sum of high_confidence_citations) NOT 14,198 (sum of total).
    """
    rows = [
        {
            "year": str(y),
            "total_citations": str(total),
            "high_confidence_citations": str(high_conf),
            "unique_datasets": str(d),
        }
        for y, total, high_conf, d in [
            (2018, 220, 120, 10),
            (2019, 750, 480, 25),
            (2020, 1800, 1100, 60),
            (2021, 3600, 2400, 120),
            (2022, 4500, 3500, 180),
            (2023, 4700, 3800, 210),
            (2024, 3300, 2592, 190),
        ]
    ]
    data = _build_temporal_data(rows)
    charts = ChartGenerator().generate_all_charts(data)

    js = generate_chart_javascript(stats={}, charts=charts)
    # Extract the y array literal that follows "y: " in createGrowthChart.
    # The endpoint must equal sum(high_confidence_citations) so the chart
    # reconciles with summary_stats.high_confidence_citations.
    match = re.search(r"createGrowthChart\(\)\s*\{[\s\S]*?y:\s*(\[[^\]]*\])", js)
    assert match, "Could not locate growth chart y series in generated JS"
    series = json.loads(match.group(1))
    expected = sum(int(r["high_confidence_citations"]) for r in rows)  # 13,992
    assert series[-1] == expected, (
        f"expected cumulative endpoint {expected} (sum of "
        f"high_confidence_citations), got {series[-1]}"
    )

    # Smoke-write the JS to disk so a downstream HTML builder could embed it.
    out = tmp_path / "growth.js"
    out.write_text(js)
    assert out.stat().st_size > 0
