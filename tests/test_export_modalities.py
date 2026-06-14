"""Tests for the modality export CLI.

Pure-function tests use real catalog rows parsed from a captured fixture (no
mocks, no network). The live fetch path is exercised by the catalog source's
own integration tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase

from dataset_citations.cli.export_modalities import (
    build_modality_map,
    main,
    primary_modality,
)
from dataset_citations.sources.nemar_catalog import (
    CatalogRow,
    parse_catalog_row,
    serialize_row,
)

FIXTURE = (
    Path(__file__).parent
    / "test_data"
    / "sources"
    / "catalog"
    / "page_offset0_limit5.json"
)


def real_rows():
    page = json.loads(FIXTURE.read_text())
    return [parse_catalog_row(r) for r in page["datasets"]]


class PrimaryModalityTests(TestCase):
    def test_recording_modality_wins_over_secondary_tags(self) -> None:
        # beh,meg -> meg ; anat,eeg,func -> eeg
        self.assertEqual(primary_modality(("beh", "meg")), "meg")
        self.assertEqual(primary_modality(("anat", "eeg", "func")), "eeg")

    def test_priority_order(self) -> None:
        # ieeg outranks meg outranks eeg
        self.assertEqual(primary_modality(("eeg", "ieeg", "meg")), "ieeg")
        self.assertEqual(primary_modality(("eeg", "meg")), "meg")

    def test_no_recording_modality_is_other(self) -> None:
        self.assertEqual(primary_modality(("beh",)), "other")
        self.assertEqual(primary_modality(()), "other")


class BuildModalityMapTests(TestCase):
    def setUp(self) -> None:
        self.rows = real_rows()

    def test_keyed_by_both_dataset_id_and_source_id(self) -> None:
        mapping = build_modality_map(self.rows)
        for row in self.rows:
            self.assertIn(row.dataset_id, mapping)
            if row.source_id:
                self.assertIn(row.source_id, mapping)
            # both ids resolve to the same primary modality
            if row.source_id:
                self.assertEqual(mapping[row.dataset_id], mapping[row.source_id])

    def test_values_match_primary_of_each_row(self) -> None:
        mapping = build_modality_map(self.rows)
        for row in self.rows:
            self.assertEqual(mapping[row.dataset_id], primary_modality(row.modalities))

    def test_row_without_source_id_keys_only_dataset_id(self) -> None:
        # nm-* catalog rows carry no source_id; the None guard must skip it
        # rather than write a {None: ...} entry.
        row = CatalogRow(
            dataset_id="nm000128",
            doi=None,
            concept_doi=None,
            source="nemar",
            source_id=None,
            github_repo="",
            modalities=("eeg",),
            name="Example",
            visibility="public",
        )
        self.assertEqual(build_modality_map([row]), {"nm000128": "eeg"})


class MainWritesFileTests(TestCase):
    def test_main_writes_modality_json_from_cached_catalog(self) -> None:
        import tempfile

        rows = real_rows()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Seed a fresh cache in the on-disk format the catalog source reads.
            cache = tmp_path / "catalog_cache.json"
            cache.write_text(json.dumps([serialize_row(r) for r in rows]))
            out_dir = tmp_path / "dashboard_data"

            rc = main(
                [
                    "--catalog-file",
                    str(cache),
                    "--output-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            written = json.loads((out_dir / "dataset_modalities.json").read_text())
            self.assertEqual(written["generated_from"], "api.nemar.org/datasets")
            self.assertEqual(written["modalities"], build_modality_map(rows))
