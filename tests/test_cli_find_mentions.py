"""Tests for run_find_mentions orchestration. Issue #169.

No network, no Mocks: an empty catalog cache file short-circuits the catalog
fetch, and a real substitute backend (`_FakeBackend`) returns canned mentions in
place of OpenAlex. Real files on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from pathlib import Path
from unittest import TestCase

from dataset_citations.cli import find_mentions as cli


class _FakeBackend:
    """Real substitute for AccessionSearchBackend (no network)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def search(self, terms: list[str]) -> list[dict]:
        return []


def _args(
    citations_dir: Path,
    *,
    dataset_list_file: str | None = None,
    max_results: int = 0,
) -> argparse.Namespace:
    cache = citations_dir.parent / "catalog.json"
    cache.write_text("[]")  # empty catalog -> _load_source_id_map hits no network
    return argparse.Namespace(
        citations_dir=str(citations_dir),
        dataset_list_file=dataset_list_file,
        catalog_cache=cache,
        catalog_cache_max_age=3600,
        max_results=max_results,
    )


def _seed(citations_dir: Path, dataset_id: str) -> Path:
    citations_dir.mkdir(parents=True, exist_ok=True)
    path = citations_dir / f"{dataset_id}_citations.json"
    path.write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "num_citations": 0,
                "date_last_updated": "2026-06-18T00:00:00+00:00",
                "metadata": {"fetch_status": "success"},
                "citation_details": [],
            },
            indent=2,
        )
    )
    return path


class RunFindMentionsTests(TestCase):
    def setUp(self) -> None:
        self._orig_backend = cli.AccessionSearchBackend
        cli.AccessionSearchBackend = _FakeBackend  # type: ignore[misc,assignment]

    def tearDown(self) -> None:
        cli.AccessionSearchBackend = self._orig_backend  # type: ignore[misc]

    def test_processes_valid_datasets_via_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "ds002718")
            _seed(cdir, "nm000207")
            cli.run_find_mentions(_args(cdir))
            # Processed datasets gain the searched_accessions marker.
            for did, acc in (("ds002718", "ds002718"), ("nm000207", "nm000207")):
                data = json.loads((cdir / f"{did}_citations.json").read_text())
                self.assertEqual(data["metadata"]["searched_accessions"], [acc])

    def test_dataset_list_file_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "ds002718")
            _seed(cdir, "ds000247")  # present but NOT in the list -> untouched
            list_file = Path(tmp) / "list.txt"
            list_file.write_text("ds002718\n")
            cli.run_find_mentions(_args(cdir, dataset_list_file=str(list_file)))
            listed = json.loads((cdir / "ds002718_citations.json").read_text())
            self.assertIn("searched_accessions", listed["metadata"])
            unlisted = json.loads((cdir / "ds000247_citations.json").read_text())
            self.assertNotIn("searched_accessions", unlisted["metadata"])

    def test_skips_missing_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            cdir.mkdir(parents=True)
            list_file = Path(tmp) / "list.txt"
            list_file.write_text("ds999999\n")  # no JSON on disk
            # Should return normally (nothing processed), no exit.
            cli.run_find_mentions(_args(cdir, dataset_list_file=str(list_file)))
            self.assertFalse((cdir / "ds999999_citations.json").exists())

    def test_skips_dataset_with_no_valid_accession(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            _seed(cdir, "experiment-1")  # fails the accession regex
            cli.run_find_mentions(_args(cdir))
            data = json.loads((cdir / "experiment-1_citations.json").read_text())
            # Skipped before merge -> no marker written.
            self.assertNotIn("searched_accessions", data["metadata"])

    def test_all_writes_fail_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            path = _seed(cdir, "ds002718")
            os.chmod(path, stat.S_IRUSR)  # read-only file -> open('w') raises
            try:
                with self.assertRaises(SystemExit) as ctx:
                    cli.run_find_mentions(_args(cdir))
                self.assertEqual(ctx.exception.code, 2)
            finally:
                os.chmod(path, stat.S_IRWXU)

    def test_idempotent_second_run_leaves_file_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "json_opencite"
            path = _seed(cdir, "ds002718")
            cli.run_find_mentions(_args(cdir))
            after_first = path.read_text()
            cli.run_find_mentions(_args(cdir))
            self.assertEqual(path.read_text(), after_first)
