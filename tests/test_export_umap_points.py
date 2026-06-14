"""Real-fixture tests for the UMAP coord-export CLI (#140).

No mocks: synthetic-but-real pickle + registry + dataset/citation JSON files are
written to a tmp dir, the CLI's main() runs against them, and the real JSON
output is read back. Exercises the three-way join (pkl ids -> registry titles,
dataset names + counts) that would otherwise fail silently.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import pytest

from dataset_citations.cli import export_umap_points as exporter


def _make_inputs(root: Path) -> dict[str, Path]:
    proj = root / "proj"
    proj.mkdir()
    pkl = proj / "both_umap_2d_v1_20260101_000000.pkl"
    with open(pkl, "wb") as f:
        pickle.dump(
            {
                "embedding_ids": [
                    "dataset_ds0001",
                    "citation_abc123",
                    "citation_missing",
                ],
                "umap_embeddings": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
            },
            f,
        )

    registry = root / "registry.json"
    registry.write_text(
        json.dumps({"citations": {"abc123": {"title": "A citing paper"}}}),
        encoding="utf-8",
    )

    datasets = root / "datasets"
    datasets.mkdir()
    (datasets / "ds0001_datasets.json").write_text(
        json.dumps(
            {"dataset_id": "ds0001", "dataset_description": {"Name": "Test DS"}}
        ),
        encoding="utf-8",
    )

    citations = root / "citations"
    citations.mkdir()
    (citations / "ds0001_citations.json").write_text(
        json.dumps(
            {"dataset_id": "ds0001", "num_citations": 5, "citation_details": []}
        ),
        encoding="utf-8",
    )

    return {
        "proj": proj,
        "registry": registry,
        "datasets": datasets,
        "citations": citations,
        "out": root / "umap_points.json",
    }


def _run(monkeypatch, p: dict[str, Path]) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "export-umap-points",
            "--projections-dir",
            str(p["proj"]),
            "--registry",
            str(p["registry"]),
            "--datasets-dir",
            str(p["datasets"]),
            "--citations-dir",
            str(p["citations"]),
            "--output",
            str(p["out"]),
        ],
    )
    exporter.main()


def test_export_joins_names_titles_counts(tmp_path: Path, monkeypatch):
    p = _make_inputs(tmp_path)
    _run(monkeypatch, p)

    out = json.loads(p["out"].read_text())
    assert out["generated_from"] == "both_umap_2d_v1_20260101_000000.pkl"

    assert len(out["datasets"]) == 1
    ds = out["datasets"][0]
    assert ds == {"id": "ds0001", "x": 1.0, "y": 2.0, "name": "Test DS", "count": 5}

    assert len(out["citations"]) == 2
    by_id = {c["id"]: c for c in out["citations"]}
    assert by_id["abc123"]["title"] == "A citing paper"
    assert by_id["abc123"]["x"] == 3.0 and by_id["abc123"]["y"] == 4.0
    # a hash absent from the registry yields an empty title, not a crash
    assert by_id["missing"]["title"] == ""


def test_missing_projections_dir_exits(tmp_path: Path, monkeypatch):
    p = _make_inputs(tmp_path)
    p["proj"] = tmp_path / "does_not_exist"
    with pytest.raises(SystemExit):
        _run(monkeypatch, p)


def test_latest_pkl_prefers_both(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "citations_umap_2d_v1_20260201_000000.pkl").write_bytes(b"x")
    (proj / "both_umap_2d_v1_20260101_000000.pkl").write_bytes(b"x")
    chosen = exporter.latest_pkl(proj)
    assert chosen is not None and chosen.name.startswith("both_")
