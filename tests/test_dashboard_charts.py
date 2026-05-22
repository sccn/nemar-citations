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


def test_growth_chart_reads_temporal_summary_total_citations():
    """The growth chart must compute cumulative `total_citations` per year."""
    data = _build_temporal_data(
        [
            {"year": "2018", "total_citations": "100", "unique_datasets": "5"},
            {"year": "2019", "total_citations": "200", "unique_datasets": "8"},
            {"year": "2020", "total_citations": "300", "unique_datasets": "12"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2018, 2019, 2020]
    # Cumulative: 100, 300, 600 — NOT the unique_datasets values (5, 13, 25).
    assert chart["data"]["y"] == [100, 300, 600]


def test_growth_chart_endpoint_matches_headline():
    """The cumulative endpoint must equal the high-confidence headline count.

    This is the exact failure mode reported in issue #77: the headline read
    14,198 high-confidence citations but the chart capped at ~1,200. The fix
    makes the final cumulative value match the sum across years.
    """
    rows = [
        {"year": "2018", "total_citations": "120", "unique_datasets": "10"},
        {"year": "2019", "total_citations": "480", "unique_datasets": "25"},
        {"year": "2020", "total_citations": "1100", "unique_datasets": "60"},
        {"year": "2021", "total_citations": "2400", "unique_datasets": "120"},
        {"year": "2022", "total_citations": "3500", "unique_datasets": "180"},
        {"year": "2023", "total_citations": "3800", "unique_datasets": "210"},
        {"year": "2024", "total_citations": "2798", "unique_datasets": "190"},
    ]
    expected_total = sum(int(r["total_citations"]) for r in rows)  # 14,198

    chart = ChartGenerator()._generate_growth_chart(
        _build_temporal_data(rows),
    )

    assert chart["data"]["y"][-1] == expected_total
    assert chart["data"]["x"][-1] == 2024


def test_growth_chart_sorts_by_year_when_csv_is_unordered():
    """CSV row order is not guaranteed; we sort by year before cumulating."""
    data = _build_temporal_data(
        [
            {"year": "2020", "total_citations": "50", "unique_datasets": "3"},
            {"year": "2018", "total_citations": "10", "unique_datasets": "1"},
            {"year": "2019", "total_citations": "30", "unique_datasets": "2"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2018, 2019, 2020]
    assert chart["data"]["y"] == [10, 40, 90]


def test_growth_chart_does_not_fall_back_to_unique_datasets():
    """Regression guard: chart must read `total_citations`, not the 10x-smaller
    `unique_datasets` field. This was the suspected root cause in #77."""
    data = _build_temporal_data(
        [
            {"year": "2023", "total_citations": "5000", "unique_datasets": "50"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["y"] == [5000]
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
            {"year": "2020", "total_citations": "100"},
            {"year": "not-a-year", "total_citations": "999"},
            {"year": "2021", "total_citations": "garbage"},
            {"year": "2022", "total_citations": "200"},
        ]
    )

    chart = ChartGenerator()._generate_growth_chart(data)

    assert chart["data"]["x"] == [2020, 2022]
    assert chart["data"]["y"] == [100, 300]


def test_chart_javascript_embeds_real_growth_series():
    """The HTML/JS template must embed the computed series, not defaults."""
    rows = [
        {"year": "2020", "total_citations": "1000", "unique_datasets": "10"},
        {"year": "2021", "total_citations": "4000", "unique_datasets": "40"},
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
    without raising and the growth series ends at the expected total."""
    # A small realistic shape based on the live dashboard payload.
    rows = [
        {"year": str(y), "total_citations": str(c), "unique_datasets": str(d)}
        for y, c, d in [
            (2018, 120, 10),
            (2019, 480, 25),
            (2020, 1100, 60),
            (2021, 2400, 120),
            (2022, 3500, 180),
            (2023, 3800, 210),
            (2024, 2798, 190),
        ]
    ]
    data = _build_temporal_data(rows)
    charts = ChartGenerator().generate_all_charts(data)

    js = generate_chart_javascript(stats={}, charts=charts)
    # Extract the y array literal that follows "y: " in createGrowthChart and
    # confirm its last value is 14,198 (matches the headline in #77).
    match = re.search(r"createGrowthChart\(\)\s*\{[\s\S]*?y:\s*(\[[^\]]*\])", js)
    assert match, "Could not locate growth chart y series in generated JS"
    series = json.loads(match.group(1))
    assert series[-1] == 14198, f"expected cumulative endpoint 14198, got {series[-1]}"

    # Smoke-write the JS to disk so a downstream HTML builder could embed it.
    out = tmp_path / "growth.js"
    out.write_text(js)
    assert out.stat().st_size > 0
