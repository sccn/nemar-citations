"""Tests for the ds->on citation dedup logic. Epic #180 phase 4, issue #126.

Real catalog fixture (`page_offset0_limit5.json`, on-* rows with ds-* source_id)
parsed through the real `parse_catalog_row`, plus real temp files. No mocks.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from dataset_citations.core.ds_on_dedup import (
    ds_to_on_mirror_map,
    find_mirrored_duplicates,
)
from dataset_citations.sources.nemar_catalog import parse_catalog_row

FIXTURE = (
    Path(__file__).parent
    / "test_data"
    / "sources"
    / "catalog"
    / "page_offset0_limit5.json"
)


def _fixture_rows():
    payload = json.loads(FIXTURE.read_text())
    return [parse_catalog_row(r) for r in payload["datasets"]]


def _seed(directory: Path, dataset_id: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{dataset_id}_citations.json"
    path.write_text(
        json.dumps(
            {"dataset_id": dataset_id, "num_citations": 0, "citation_details": []}
        )
    )
    return path


class MirrorMapTests(TestCase):
    def test_maps_ds_alias_to_on_id(self) -> None:
        mapping = ds_to_on_mirror_map(_fixture_rows())
        self.assertEqual(mapping["ds005261"], "on005261")
        self.assertEqual(mapping["ds002778"], "on002778")
        # Keys are always ds-*, values always on-*.
        self.assertTrue(
            all(k.startswith("ds") and v.startswith("on") for k, v in mapping.items())
        )

    def test_ignores_rows_without_ds_source_id(self) -> None:
        rows = _fixture_rows() + [
            parse_catalog_row({"dataset_id": "nm000207", "source": "nemar"}),
            # on-* with no source_id (NEMAR-native) -> not a mirror.
            parse_catalog_row({"dataset_id": "on000001", "source": "nemar"}),
            # a standalone ds-* catalog row contributes nothing (it's not on-*).
            parse_catalog_row({"dataset_id": "ds999999", "source": "openneuro"}),
        ]
        mapping = ds_to_on_mirror_map(rows)
        self.assertNotIn("nm000207", mapping)
        self.assertNotIn(None, mapping)
        self.assertNotIn("on000001", mapping.values())


class FindDuplicatesTests(TestCase):
    def setUp(self) -> None:
        self.mapping = ds_to_on_mirror_map(_fixture_rows())

    def test_returns_mirrored_ds_only_when_on_present(self) -> None:
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            _seed(d, "ds005261")
            _seed(d, "on005261")  # mirrored pair -> ds005261 is prunable
            _seed(d, "ds999999")  # unmirrored ds-* -> keep
            _seed(d, "nm000207")  # nm-* -> keep
            _seed(d, "on002778")  # on-* whose ds mirror is absent -> nothing
            dups = find_mirrored_duplicates(d, self.mapping)
            self.assertEqual([p.name for p in dups], ["ds005261_citations.json"])

    def test_keeps_mirrored_ds_when_on_file_missing(self) -> None:
        # Safety invariant: never delete a ds-* before its on-* replacement exists.
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            _seed(d, "ds005261")  # on005261 deliberately NOT seeded
            self.assertEqual(find_mirrored_duplicates(d, self.mapping), [])

    def test_empty_dir_returns_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            self.assertEqual(find_mirrored_duplicates(Path(tmp), self.mapping), [])

    def test_result_is_sorted(self) -> None:
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            for ds in ("ds005262", "ds005261", "ds002778"):
                _seed(d, ds)
                _seed(d, self.mapping[ds])
            names = [p.name for p in find_mirrored_duplicates(d, self.mapping)]
            self.assertEqual(names, sorted(names))
            self.assertEqual(len(names), 3)
