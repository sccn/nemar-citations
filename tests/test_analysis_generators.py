"""Real-fixture tests for the theme and network analysis generators (#122).

No mocks: real citation JSON files are written to a tmp dir and the real
CSV / JSON / PNG outputs are read back. Confirms the generators produce the
shapes the dashboard consumes, so a restored nightly run yields proper
UMAP-adjacent portions (wordcloud themes, network CSVs).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dataset_citations.analysis.generate_network import generate_network
from dataset_citations.analysis.generate_themes import generate_themes


def _cite(title, author, score, year=2022):
    return {
        "title": title,
        "author": author,
        "year": year,
        "confidence_scoring": {"confidence_score": score},
    }


def _write(citations_dir: Path, dataset_id: str, citations: list[dict]) -> None:
    citations_dir.mkdir(parents=True, exist_ok=True)
    (citations_dir / f"{dataset_id}_citations.json").write_text(
        json.dumps({"dataset_id": dataset_id, "citation_details": citations})
    )


def _read_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def test_network_popularity_bridge_and_cocitation(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    out = tmp_path / "network"
    # "Bridge paper X" by "Lee K" cites both ds_a and ds_b -> a bridge paper.
    _write(
        citations_dir,
        "ds_a",
        [
            _cite("EEG study A", "Smith J", 0.8),
            _cite("Bridge paper X", "Lee K", 0.9),
            _cite("low conf noise", "Noise", 0.1),  # excluded from high_conf
        ],
    )
    _write(
        citations_dir,
        "ds_b",
        [
            _cite("Bridge paper X", "Lee K", 0.9),
            _cite("benchmark comparison work", "Jones", 0.7),
        ],
    )

    generate_network(citations_dir, out)

    pop = {r["dataset_id"]: r for r in _read_csv(out / "dataset_popularity.csv")}
    assert pop["ds_a"]["high_conf_citations"] == "2"
    assert pop["ds_a"]["total_citations"] == "3"
    assert pop["ds_b"]["high_conf_citations"] == "2"

    bridges = _read_csv(out / "bridge_papers.csv")
    bridge_x = [b for b in bridges if b["title"] == "Bridge paper X"]
    assert bridge_x and bridge_x[0]["num_datasets"] == "2"
    assert "ds_a" in bridge_x[0]["datasets_bridged"]
    assert "ds_b" in bridge_x[0]["datasets_bridged"]

    coc = _read_csv(out / "dataset_co_citations.csv")
    assert any({r["dataset1"], r["dataset2"]} == {"ds_a", "ds_b"} for r in coc)


def test_network_low_confidence_excluded_from_bridges(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    out = tmp_path / "network"
    # Same paper in two datasets but BOTH low-confidence -> not a bridge.
    _write(citations_dir, "ds_a", [_cite("Weak link", "X Y", 0.2)])
    _write(citations_dir, "ds_b", [_cite("Weak link", "X Y", 0.2)])

    generate_network(citations_dir, out)

    bridges = _read_csv(out / "bridge_papers.csv")
    assert all(b["title"] != "Weak link" for b in bridges)


def test_themes_emit_themes_keyed_json_and_wordcloud(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    out = tmp_path / "themes"
    _write(
        citations_dir,
        "ds_a",
        [
            _cite("EEG electrode brain dynamics", "A", 0.8),
            _cite("audio sound music perception", "B", 0.8),
            _cite("cognitive memory attention task", "C", 0.8),
            _cite("novel method algorithm analysis", "D", 0.8),
            _cite("ignored low confidence", "E", 0.1),
        ],
    )

    generate_themes(citations_dir, out)

    payload = json.loads((out / "comprehensive_theme_analysis.json").read_text())
    # The dashboard ThemeGenerator consumes the themes-keyed schema.
    assert "themes" in payload
    assert payload["themes"], "expected at least one theme"
    first = payload["themes"][0]
    assert {"id", "name", "size", "top_words"} <= set(first)
    # At least one wordcloud PNG was produced.
    assert list(out.glob("theme_*_wordcloud.png"))


def test_themes_empty_when_no_high_confidence(tmp_path: Path):
    citations_dir = tmp_path / "json_opencite"
    out = tmp_path / "themes"
    _write(citations_dir, "ds_a", [_cite("EEG brain study", "A", 0.1)])

    generate_themes(citations_dir, out)

    payload = json.loads((out / "comprehensive_theme_analysis.json").read_text())
    assert payload["themes"] == []
