"""Tests for the api.nemar.org/datasets catalog source.

Parser tests use real catalog fixtures captured from the live API (no
mocks, no network). Live fetch tests are gated behind RUN_INTEGRATION_TESTS=1
because they depend on api.nemar.org availability.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest import TestCase, skipUnless

from dataset_citations.sources.models import FetchError, FetchSuccess
from dataset_citations.sources.nemar_catalog import (
    CatalogRow,
    fetch_catalog,
    filter_by_modality,
    get_or_fetch_catalog,
    load_cached_catalog,
    parse_catalog_row,
    save_catalog_cache,
    serialize_row,
)

FIXTURE_DIR = Path(__file__).parent / "test_data" / "sources" / "catalog"


def load_page(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


class ParseRowTests(TestCase):
    """Pure parser against a real catalog payload."""

    def setUp(self) -> None:
        page = load_page("page_offset0_limit5.json")
        self.raw_rows = page["datasets"]

    def test_first_row_parses(self) -> None:
        row = parse_catalog_row(self.raw_rows[0])
        self.assertIsInstance(row, CatalogRow)
        self.assertTrue(row.dataset_id)

    def test_modalities_normalized_to_sorted_lower_tuple(self) -> None:
        # Pick any row that has at least one modality.
        with_mods = [r for r in self.raw_rows if r.get("modalities")]
        self.assertTrue(with_mods, "fixture must contain at least one modality row")
        row = parse_catalog_row(with_mods[0])
        self.assertIsInstance(row.modalities, tuple)
        for m in row.modalities:
            self.assertEqual(m, m.lower())
        self.assertEqual(list(row.modalities), sorted(row.modalities))

    def test_missing_dataset_id_raises(self) -> None:
        with self.assertRaises(KeyError):
            parse_catalog_row({"doi": "10.x/y"})

    def test_empty_optional_fields_become_none(self) -> None:
        row = parse_catalog_row(
            {
                "dataset_id": "test001",
                "doi": "",
                "concept_doi": None,
                "name": "",
            }
        )
        self.assertIsNone(row.doi)
        self.assertIsNone(row.concept_doi)
        self.assertIsNone(row.name)


class RoundTripTests(TestCase):
    """parse_catalog_row(serialize_row(row)) == row for every fixture row."""

    def test_roundtrip_preserves_rows(self) -> None:
        page = load_page("page_offset0_limit5.json")
        for raw in page["datasets"]:
            original = parse_catalog_row(raw)
            roundtripped = parse_catalog_row(serialize_row(original))
            self.assertEqual(original, roundtripped)


class FilterByModalityTests(TestCase):
    def setUp(self) -> None:
        page = load_page("page_offset0_limit5.json")
        self.rows = [parse_catalog_row(r) for r in page["datasets"]]

    def test_filter_returns_subset_with_target_modality(self) -> None:
        filtered = filter_by_modality(self.rows, ["meg"])
        for row in filtered:
            self.assertIn("meg", row.modalities)

    def test_empty_target_returns_empty(self) -> None:
        self.assertEqual(filter_by_modality(self.rows, []), [])

    def test_case_insensitive(self) -> None:
        lower = filter_by_modality(self.rows, ["meg"])
        upper = filter_by_modality(self.rows, ["MEG"])
        self.assertEqual([r.dataset_id for r in lower], [r.dataset_id for r in upper])


class CacheTests(TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(__file__).parent / "test_data" / "sources" / "_tmp_cache"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.tmp_dir / "catalog.json"
        if self.cache_path.exists():
            self.cache_path.unlink()
        page = load_page("page_offset0_limit5.json")
        self.rows = [parse_catalog_row(r) for r in page["datasets"]]

    def tearDown(self) -> None:
        if self.cache_path.exists():
            self.cache_path.unlink()

    def test_save_then_load_returns_equal_rows(self) -> None:
        save_catalog_cache(self.cache_path, self.rows)
        loaded = load_cached_catalog(self.cache_path)
        self.assertEqual(loaded, self.rows)

    def test_load_missing_returns_none(self) -> None:
        self.assertIsNone(load_cached_catalog(self.cache_path))

    def test_load_stale_returns_none(self) -> None:
        save_catalog_cache(self.cache_path, self.rows)
        # Backdate the file so it's older than the freshness window.
        old = time.time() - 7200
        os.utime(self.cache_path, (old, old))
        self.assertIsNone(load_cached_catalog(self.cache_path, max_age_seconds=3600))

    def test_load_malformed_returns_none(self) -> None:
        self.cache_path.write_text("not json")
        self.assertIsNone(load_cached_catalog(self.cache_path))


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live api.nemar.org calls; set RUN_INTEGRATION_TESTS=1 to enable",
)
class LiveCatalogIntegration(TestCase):
    """Hits api.nemar.org/datasets. Real network, no mocks."""

    def test_fetch_catalog_returns_many_rows(self) -> None:
        result = fetch_catalog(page_size=200)
        self.assertIsInstance(result, FetchSuccess)
        assert isinstance(result, FetchSuccess)
        rows = result.value
        self.assertGreater(len(rows), 100, "expected hundreds of rows")
        # Spot-check the first row's shape.
        first = rows[0]
        self.assertTrue(first.dataset_id)
        self.assertIn(first.source, {"openneuro", "nemar", "unknown"})

    def test_get_or_fetch_with_cache(self) -> None:
        tmp_dir = Path(__file__).parent / "test_data" / "sources" / "_tmp_cache"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        cache_path = tmp_dir / "live_cache.json"
        if cache_path.exists():
            cache_path.unlink()
        try:
            first = get_or_fetch_catalog(cache_path=cache_path)
            self.assertIsInstance(first, FetchSuccess)
            assert isinstance(first, FetchSuccess)
            self.assertTrue(cache_path.exists())
            second = get_or_fetch_catalog(cache_path=cache_path)
            self.assertIsInstance(second, FetchSuccess)
            assert isinstance(second, FetchSuccess)
            self.assertEqual(first.value, second.value)
        finally:
            if cache_path.exists():
                cache_path.unlink()

    def test_bad_url_returns_fetch_error(self) -> None:
        result = fetch_catalog(base_url="https://api.nemar.org/does-not-exist")
        self.assertIsInstance(result, FetchError)
