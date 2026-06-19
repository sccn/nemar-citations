"""Tests for run_prune_mirrored orchestration. Epic #180 phase 4, issue #126.

No network, no mocks: a fresh on-disk catalog cache short-circuits the catalog
fetch (`get_or_fetch_catalog` reads the cache when fresh), and real citation
JSON files live in a tempdir. The catalog-failure case swaps the module's
`get_or_fetch_catalog` for a real stub function (the pattern test_cli_find_mentions
uses for the backend), never `unittest.mock`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from dataset_citations.cli import prune_mirrored as cli
from dataset_citations.sources.models import FetchError

# Catalog cache shape = a JSON list of row dicts (what save_catalog_cache writes
# and load_cached_catalog reads). Two mirrored pairs.
_CATALOG = [
    {"dataset_id": "on005261", "source": "openneuro", "source_id": "ds005261"},
    {"dataset_id": "on005262", "source": "openneuro", "source_id": "ds005262"},
    {"dataset_id": "nm000207", "source": "nemar", "source_id": None},
]


def _seed(citations_dir: Path, dataset_id: str) -> Path:
    citations_dir.mkdir(parents=True, exist_ok=True)
    path = citations_dir / f"{dataset_id}_citations.json"
    path.write_text(
        json.dumps(
            {"dataset_id": dataset_id, "num_citations": 0, "citation_details": []}
        )
    )
    return path


def _args(citations_dir: Path, *, dry_run: bool = False, catalog=_CATALOG):
    cache = citations_dir.parent / "catalog.json"
    cache.write_text(json.dumps(catalog))  # fresh mtime -> no network
    return argparse.Namespace(
        citations_dir=str(citations_dir),
        catalog_cache=cache,
        catalog_cache_max_age=3600,
        dry_run=dry_run,
    )


class RunPruneMirroredTests(TestCase):
    def test_dry_run_deletes_nothing(self) -> None:
        with TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "ds005261")
            _seed(cdir, "on005261")
            cli.run_prune_mirrored(_args(cdir, dry_run=True))
            self.assertTrue((cdir / "ds005261_citations.json").exists())
            self.assertTrue((cdir / "on005261_citations.json").exists())

    def test_prunes_only_mirrored_ds_with_present_on(self) -> None:
        with TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "ds005261")  # mirrored, on present -> pruned
            _seed(cdir, "on005261")
            _seed(cdir, "ds005262")  # mirrored, but on005262 absent -> kept
            _seed(cdir, "ds999999")  # unmirrored -> kept
            _seed(cdir, "nm000207")  # nm -> kept
            cli.run_prune_mirrored(_args(cdir))
            self.assertFalse((cdir / "ds005261_citations.json").exists())
            self.assertTrue((cdir / "on005261_citations.json").exists())
            self.assertTrue((cdir / "ds005262_citations.json").exists())
            self.assertTrue((cdir / "ds999999_citations.json").exists())
            self.assertTrue((cdir / "nm000207_citations.json").exists())

    def test_idempotent_second_run_is_noop(self) -> None:
        with TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "ds005261")
            _seed(cdir, "on005261")
            cli.run_prune_mirrored(_args(cdir))
            self.assertFalse((cdir / "ds005261_citations.json").exists())
            # Second run: nothing left to prune, no error.
            cli.run_prune_mirrored(_args(cdir))
            self.assertTrue((cdir / "on005261_citations.json").exists())

    def test_catalog_failure_deletes_nothing(self) -> None:
        original = cli.get_or_fetch_catalog
        cli.get_or_fetch_catalog = lambda **_: FetchError("network", "boom")  # type: ignore[assignment]
        try:
            with TemporaryDirectory() as tmp:
                cdir = Path(tmp) / "json_opencite"
                _seed(cdir, "ds005261")
                _seed(cdir, "on005261")
                cli.run_prune_mirrored(_args(cdir))
                # Without a confirmed mirror map, prune nothing.
                self.assertTrue((cdir / "ds005261_citations.json").exists())
        finally:
            cli.get_or_fetch_catalog = original  # type: ignore[assignment]
