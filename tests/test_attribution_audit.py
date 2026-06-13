"""Real-fixture tests for the cross-dataset attribution audit.

Reproduces the umbrella-anchor inflation: a shared anchor (MNE-BIDS-like DOI)
listed in several datasets attributes its citers to every one of them, while a
per-dataset data-paper anchor contributes unique citers. No mocks: records are
real schema-v2 shapes and the IO path writes/reads real JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

from dataset_citations.analysis.attribution_audit import (
    build_report,
    load_corpus,
    run_audit,
)

UMBRELLA = "10.21105/joss.01896"


def _cite(doi: str, source_doi: str) -> dict:
    return {
        "title": f"Paper {doi}",
        "doi": doi,
        "pmid": None,
        "openalex_id": None,
        "source_doi": source_doi,
        "source_relation": "References",
        "cited_by": 1,
    }


def _record(dataset_id: str, citations: list[dict], context: list[dict] | None = None):
    return {
        "dataset_id": dataset_id,
        "num_citations": len(citations),
        "citation_details": citations,
        "metadata": {"schema_version": "2.0", "context_anchors": context or []},
    }


def _three_sharing_datasets() -> list[dict]:
    # Each dataset shares the umbrella anchor's citers p1/p2 and has one
    # unique citer via its own data-paper anchor. ds003 uses an UPPERCASE
    # umbrella DOI to exercise case-insensitive anchor keying.
    return [
        _record(
            "ds001",
            [
                _cite("10.x/p1", UMBRELLA),
                _cite("10.x/p2", UMBRELLA),
                _cite("10.x/p3", "10.1/data1"),
            ],
        ),
        _record(
            "ds002",
            [
                _cite("10.x/p1", UMBRELLA),
                _cite("10.x/p2", UMBRELLA),
                _cite("10.x/p4", "10.1/data2"),
            ],
        ),
        _record(
            "ds003",
            [
                _cite("10.x/p1", "10.21105/JOSS.01896"),
                _cite("10.x/p2", "10.21105/JOSS.01896"),
                _cite("10.x/p5", "10.1/data3"),
            ],
        ),
    ]


def test_summed_vs_unique_counts():
    report = build_report(_three_sharing_datasets(), max_datasets_per_anchor=2)
    assert report.summed_citations == 9
    # p1..p5 distinct -> 5 unique despite 9 summed rows
    assert report.unique_citations == 5
    assert round(report.inflation_ratio, 2) == 1.80


def test_umbrella_anchor_flagged_as_violation():
    report = build_report(_three_sharing_datasets(), max_datasets_per_anchor=2)
    by_anchor = {a.anchor: a for a in report.anchor_spreads}
    # uppercase ds003 merges into the same normalized anchor key
    assert by_anchor[UMBRELLA].dataset_count == 3
    assert by_anchor[UMBRELLA].total_attributed == 6
    violation_anchors = {a.anchor for a in report.violations}
    assert UMBRELLA in violation_anchors
    # the per-dataset data anchors stay below threshold
    assert "10.1/data1" not in violation_anchors


def test_estimated_true_total_drops_violation_rows():
    report = build_report(_three_sharing_datasets(), max_datasets_per_anchor=2)
    # only the 3 data-paper citers (p3/p4/p5) survive
    assert report.estimated_true_total == 3
    assert report.per_dataset["ds001"] == {"summed": 3, "cleaned": 1}


def test_context_anchors_excluded_and_paren_normalized():
    records = _three_sharing_datasets()
    # ds004 buckets the umbrella into context with a trailing-paren identifier;
    # it must NOT raise the anchor's fetched spread and must normalize to the
    # same key, incrementing context_classified.
    records.append(
        _record(
            "ds004",
            [_cite("10.x/p6", "10.1/data4")],
            context=[
                {
                    "anchor_identifier": "10.21105/joss.01896)",
                    "anchor_identifier_type": "doi",
                    "classification": "umbrella",
                    "paper_title": "MNE-BIDS",
                }
            ],
        )
    )
    report = build_report(records, max_datasets_per_anchor=2)
    by_anchor = {a.anchor: a for a in report.anchor_spreads}
    # spread stays 3 (ds004 did not fetch the umbrella's citers)
    assert by_anchor[UMBRELLA].dataset_count == 3
    assert by_anchor[UMBRELLA].context_classified == 1
    assert by_anchor[UMBRELLA].paper_title == "MNE-BIDS"


def test_no_violation_when_threshold_high():
    report = build_report(_three_sharing_datasets(), max_datasets_per_anchor=5)
    assert report.violations == []
    # nothing dropped, so cleaned == summed everywhere
    assert report.estimated_true_total == report.summed_citations


def test_run_audit_reads_files_and_writes_json(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    citations_dir.mkdir()
    for rec in _three_sharing_datasets():
        (citations_dir / f"{rec['dataset_id']}_citations.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )
    # a non-citation json must be ignored by the glob
    (citations_dir / "notes.json").write_text("{}", encoding="utf-8")

    assert len(load_corpus(citations_dir)) == 3

    report_json = tmp_path / "report.json"
    report = run_audit(
        citations_dir=citations_dir,
        max_datasets_per_anchor=2,
        report_json=report_json,
    )
    assert report.summed_citations == 9
    assert report.unique_citations == 5

    written = json.loads(report_json.read_text(encoding="utf-8"))
    assert written["summed_citations"] == 9
    assert written["n_violations"] == 1
