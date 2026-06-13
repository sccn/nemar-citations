"""Real-fixture tests for the temporal analysis generator.

Covers the two bugs in issue #115: the missing ``high_confidence_citations``
series (which left the dashboard growth chart flat) and the stale ``< 2025``
year cap (which dropped 2025/2026 citations). No mocks: real citation JSON
files are written to a tmp dir and the real CSV/JSON outputs are read back.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dataset_citations.analysis.generate_temporal import generate_temporal


def _cite(year, score=None):
    cit = {"year": year, "title": f"paper {year}/{score}"}
    if score is not None:
        cit["confidence_scoring"] = {"confidence_score": score}
    return cit


def _write_corpus(citations_dir: Path) -> None:
    citations_dir.mkdir(parents=True, exist_ok=True)
    (citations_dir / "ds_a_citations.json").write_text(
        json.dumps(
            {
                "dataset_id": "ds_a",
                "citation_details": [
                    _cite(2022, 0.8),  # high
                    _cite(2022, 0.2),  # low
                    _cite(1998, 0.9),  # excluded: before MIN_YEAR
                ],
            }
        )
    )
    (citations_dir / "ds_b_citations.json").write_text(
        json.dumps(
            {
                "dataset_id": "ds_b",
                "citation_details": [
                    _cite(2026, 0.5),  # high, recent year (was dropped by < 2025)
                    _cite(2022, None),  # no scoring block -> low
                    {"year": 2022, "confidence_scoring": None},  # None block -> low
                    _cite(0),  # excluded: no year
                ],
            }
        )
    )


def _read_summary(output_dir: Path) -> dict[int, dict]:
    rows = {}
    with open(output_dir / "temporal_summary.csv") as f:
        for row in csv.DictReader(f):
            rows[int(row["year"])] = row
    return rows


def test_high_confidence_column_present_and_correct(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    output_dir = tmp_path / "temporal"
    _write_corpus(citations_dir)

    generate_temporal(
        citations_dir, output_dir, confidence_threshold=0.4, max_year=2027
    )

    rows = _read_summary(output_dir)
    assert "high_confidence_citations" in rows[2022]
    # 2022: 4 total (0.8, 0.2, missing, None), 1 high-confidence (0.8), 2 datasets
    assert int(rows[2022]["total_citations"]) == 4
    assert int(rows[2022]["high_confidence_citations"]) == 1
    assert int(rows[2022]["unique_datasets"]) == 2


def test_recent_years_are_not_dropped(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    output_dir = tmp_path / "temporal"
    _write_corpus(citations_dir)

    generate_temporal(
        citations_dir, output_dir, confidence_threshold=0.4, max_year=2027
    )

    rows = _read_summary(output_dir)
    # 2026 used to be dropped by the hardcoded `< 2025` cap
    assert 2026 in rows
    assert int(rows[2026]["total_citations"]) == 1
    assert int(rows[2026]["high_confidence_citations"]) == 1
    # pre-2000 and yearless citations are excluded
    assert 1998 not in rows
    assert 0 not in rows


def test_json_output_carries_high_confidence(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    output_dir = tmp_path / "temporal"
    _write_corpus(citations_dir)

    generate_temporal(
        citations_dir, output_dir, confidence_threshold=0.4, max_year=2027
    )

    payload = json.loads((output_dir / "temporal_analysis.json").read_text())
    assert payload["yearly_high_confidence_citations"]["2022"] == 1
    assert payload["yearly_high_confidence_citations"]["2026"] == 1
    assert payload["confidence_threshold"] == 0.4


def test_threshold_is_respected(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    output_dir = tmp_path / "temporal"
    _write_corpus(citations_dir)

    # With a 0.1 threshold the 0.2 and 0.5 citations also count as high.
    generate_temporal(
        citations_dir, output_dir, confidence_threshold=0.1, max_year=2027
    )

    rows = _read_summary(output_dir)
    # 2022: 0.8 and 0.2 clear 0.1; missing/None stay 0.0 -> 2 high
    assert int(rows[2022]["high_confidence_citations"]) == 2


def test_default_max_year_excludes_far_future(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    output_dir = tmp_path / "temporal"
    citations_dir.mkdir(parents=True)
    (citations_dir / "ds_c_citations.json").write_text(
        json.dumps(
            {
                "dataset_id": "ds_c",
                "citation_details": [_cite(2023, 0.9), _cite(3000, 0.9)],
            }
        )
    )

    generate_temporal(citations_dir, output_dir)  # default max_year = now+1

    rows = _read_summary(output_dir)
    assert 2023 in rows
    assert 3000 not in rows
