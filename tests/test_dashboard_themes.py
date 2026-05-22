"""Tests for the dashboard theme generator and template rendering.

Locks in the fix for issue #79: the Research Themes tab used to render four
empty cards because the template referenced wordcloud PNGs that no upstream
step produced, even though `top_words` were already in the payload. The
generator now materializes a PNG per theme from its `top_words` list at
dashboard-build time, and the template includes the words as a styled
fallback so the cards always have content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from dataset_citations.dashboard.components.themes import ThemeGenerator
from dataset_citations.dashboard.templates.nemar_simple import (
    generate_nemar_dashboard,
)


def _sample_themes_payload() -> Dict[str, Any]:
    """Minimal payload matching the live dashboard shape (issue #79 example)."""
    return {
        "theme_analysis": {
            "comprehensive_theme_analysis": {
                "themes": [
                    {
                        "id": 0,
                        "name": "Core EEG",
                        "size": 8187,
                        "top_words": [
                            "Brain Computer",
                            "computer interface",
                            "EEG based",
                            "motor imagery",
                            "EEG Signal",
                            "resting state",
                        ],
                    },
                    {
                        "id": 1,
                        "name": "Audio & Stimulation",
                        "size": 1432,
                        "top_words": ["auditory cortex", "speech", "music"],
                    },
                    {
                        "id": 2,
                        "name": "Task Performance",
                        "size": 945,
                        "top_words": ["cognitive load", "working memory"],
                    },
                    {
                        "id": 3,
                        "name": "Advanced Methods",
                        "size": 614,
                        "top_words": ["deep learning", "transformer", "CNN"],
                    },
                ]
            }
        }
    }


def test_generator_emits_one_entry_per_payload_theme():
    """All four themes from the payload must end up in the rendered list."""
    gen = ThemeGenerator()
    out = gen.generate_themes(_sample_themes_payload())

    assert len(out["themes"]) == 4
    titles = [t["title"] for t in out["themes"]]
    assert titles == [
        "Theme 1 - Core EEG",
        "Theme 2 - Audio & Stimulation",
        "Theme 3 - Task Performance",
        "Theme 4 - Advanced Methods",
    ]


def test_generator_passes_top_words_through():
    """`top_words` must reach the template so the tag-cloud fallback works."""
    gen = ThemeGenerator()
    out = gen.generate_themes(_sample_themes_payload())

    assert out["themes"][0]["top_words"][:2] == ["Brain Computer", "computer interface"]
    assert "transformer" in out["themes"][3]["top_words"]


def test_generator_writes_wordcloud_pngs(tmp_path: Path):
    """When given an output_dir, the generator writes one PNG per theme."""
    pytest.importorskip("wordcloud")
    gen = ThemeGenerator(output_dir=tmp_path)
    gen.generate_themes(_sample_themes_payload())

    themes_dir = tmp_path / "data" / "themes"
    assert themes_dir.is_dir()
    pngs = sorted(themes_dir.glob("theme_*_wordcloud.png"))
    assert len(pngs) == 4
    # PNGs must be non-empty and start with the PNG magic bytes.
    for png in pngs:
        contents = png.read_bytes()
        assert contents, f"empty file: {png}"
        assert contents[:8] == b"\x89PNG\r\n\x1a\n", f"not a PNG: {png}"


def test_generator_no_pngs_without_output_dir(tmp_path: Path):
    """The generator runs in metadata-only mode when output_dir is None."""
    gen = ThemeGenerator()
    out = gen.generate_themes(_sample_themes_payload())
    assert len(out["themes"]) == 4
    # No data/themes directory was created (we did not pass a path).
    assert not (tmp_path / "data" / "themes").exists()


def test_generator_skips_theme_with_empty_top_words(tmp_path: Path):
    """A theme with no top_words should still render (empty card) without
    crashing wordcloud generation."""
    pytest.importorskip("wordcloud")
    payload = {
        "theme_analysis": {
            "comprehensive_theme_analysis": {
                "themes": [
                    {"id": 0, "name": "Empty", "size": 0, "top_words": []},
                    {
                        "id": 1,
                        "name": "Has Words",
                        "size": 5,
                        "top_words": ["alpha", "beta"],
                    },
                ]
            }
        }
    }
    gen = ThemeGenerator(output_dir=tmp_path)
    out = gen.generate_themes(payload)
    assert len(out["themes"]) == 2
    # Only the second theme produced a PNG.
    pngs = list((tmp_path / "data" / "themes").glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].name == "theme_1_wordcloud.png"


def test_template_renders_all_four_top_words_as_tags():
    """The Research Themes tab must include every `top_words` phrase, so the
    tab is no longer empty even when the PNG isn't available."""
    gen = ThemeGenerator()
    themes_data = gen.generate_themes(_sample_themes_payload())
    html = generate_nemar_dashboard(
        stats={"cards": []},
        charts={},
        networks={},
        themes=themes_data,
        modals={},
        data=None,
        data_file=None,
        timestamp="2026-05-22 00:00:00",
    )

    # Every top word from every theme should be present in the rendered HTML.
    for theme in _sample_themes_payload()["theme_analysis"][
        "comprehensive_theme_analysis"
    ]["themes"]:
        for phrase in theme["top_words"]:
            assert phrase in html, (
                f"phrase {phrase!r} from theme {theme['name']!r} missing "
                f"from rendered Research Themes tab"
            )


def test_template_card_includes_theme_name_and_size():
    """Each rendered card must show the theme name and citation count."""
    gen = ThemeGenerator()
    themes_data = gen.generate_themes(_sample_themes_payload())
    html = generate_nemar_dashboard(
        stats={"cards": []},
        charts={},
        networks={},
        themes=themes_data,
        modals={},
        data=None,
        data_file=None,
        timestamp="2026-05-22 00:00:00",
    )

    assert "Theme 1 - Core EEG" in html
    assert "8187 citations in this cluster" in html
    assert "Theme 4 - Advanced Methods" in html


def test_template_renders_when_no_themes_in_payload():
    """An empty themes payload still renders the placeholder card without
    crashing."""
    gen = ThemeGenerator()
    themes_data = gen.generate_themes({})
    html = generate_nemar_dashboard(
        stats={"cards": []},
        charts={},
        networks={},
        themes=themes_data,
        modals={},
        data=None,
        data_file=None,
        timestamp="2026-05-22 00:00:00",
    )
    # Placeholder copy from the fallback themes entry.
    assert "Themes will be generated" in html


def test_template_does_not_emit_empty_card_body():
    """Regression guard for #79: previously the card body contained only an
    <img> tag pointing at a non-existent PNG, yielding a blank card. Now the
    card must contain either the tag cloud or a graceful empty-state notice."""
    gen = ThemeGenerator()
    themes_data = gen.generate_themes(_sample_themes_payload())
    html = generate_nemar_dashboard(
        stats={"cards": []},
        charts={},
        networks={},
        themes=themes_data,
        modals={},
        data=None,
        data_file=None,
        timestamp="2026-05-22 00:00:00",
    )

    # The tag cloud wrapper must appear once per theme.
    assert html.count('class="theme-words"') == 4


def test_smoke_full_dashboard_build(tmp_path: Path):
    """End-to-end smoke test covering BOTH bug fixes from this PR:

    - #79 (wordcloud): four real PNGs materialize and the HTML references
      each one.
    - #77 (growth chart): the growth chart's JS is embedded and its
      cumulative endpoint matches the per-year high_confidence_citations
      sum, NOT the hardcoded `[20, 65, ..., 1140]` placeholder.

    The previous smoke test passed `charts={}` and so left #77 uncovered;
    PR-#106 reviewer flagged that as a gap.
    """
    pytest.importorskip("wordcloud")

    # Avoid a circular-import-style dependency: defer the chart helpers
    # to runtime so this themes-test file stays self-contained.
    from dataset_citations.dashboard.components.charts import ChartGenerator
    from dataset_citations.dashboard.templates.components.charts import (
        generate_chart_javascript,
    )

    results_dir = tmp_path / "results"
    output_dir = tmp_path / "out"
    results_dir.mkdir()
    output_dir.mkdir()

    # Themes side of the smoke.
    gen = ThemeGenerator(output_dir=output_dir)
    themes_data = gen.generate_themes(_sample_themes_payload())

    # Charts side: realistic per-year rows with high_confidence_citations
    # so we can pin the endpoint against the headline.
    temporal_rows = [
        {
            "year": str(y),
            "total_citations": str(total),
            "high_confidence_citations": str(high_conf),
            "unique_datasets": str(d),
        }
        for y, total, high_conf, d in [
            (2020, 1800, 1100, 60),
            (2021, 3600, 2400, 120),
            (2022, 4500, 3500, 180),
            (2023, 4700, 3800, 210),
            (2024, 3300, 2592, 190),
        ]
    ]
    charts_data = ChartGenerator().generate_all_charts(
        {"temporal_analysis": {"temporal_summary": temporal_rows}}
    )
    expected_endpoint = sum(int(r["high_confidence_citations"]) for r in temporal_rows)

    html = generate_nemar_dashboard(
        stats={"cards": []},
        charts=charts_data,
        networks={},
        themes=themes_data,
        modals={},
        data=None,
        data_file=None,
        timestamp="2026-05-22 00:00:00",
    )

    # #79: PNGs materialized + HTML references each path.
    pngs = list((output_dir / "data" / "themes").glob("*.png"))
    assert len(pngs) == 4
    for theme_id in range(4):
        assert f"data/themes/theme_{theme_id}_wordcloud.png" in html
    assert html.strip().endswith("</html>")

    # #77: growth-chart JS is embedded with the right endpoint.
    js = generate_chart_javascript(stats={}, charts=charts_data)
    assert str(expected_endpoint) in js, (
        f"growth-chart JS does not embed the expected cumulative endpoint "
        f"{expected_endpoint}; chart binding may have regressed."
    )
    # Hardcoded fallback must NOT appear.
    assert "[20, 65, 150, 370, 650, 950, 1040, 1140]" not in js

    # Persist for downstream smoke inspection.
    out_html = output_dir / "dashboard.html"
    out_html.write_text(html, encoding="utf-8")
    assert out_html.stat().st_size > 1000
