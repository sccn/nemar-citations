"""Tests for accession-term derivation (no network, pure function). Issue #169."""

from __future__ import annotations

from unittest import TestCase

from dataset_citations.sources.accession import accession_search_terms


class AccessionSearchTermsTests(TestCase):
    def test_legacy_ds_returns_single_term(self) -> None:
        self.assertEqual(accession_search_terms("ds002718"), ["ds002718"])

    def test_on_dataset_includes_openneuro_ds_alias(self) -> None:
        # on-* carries its OpenNeuro ds-number in source_id; people cite the ds.
        self.assertEqual(
            accession_search_terms("on005964", "ds005964"),
            ["on005964", "ds005964"],
        )

    def test_nm_dataset(self) -> None:
        self.assertEqual(accession_search_terms("nm000207"), ["nm000207"])

    def test_dedupes_when_source_id_equals_dataset_id(self) -> None:
        self.assertEqual(accession_search_terms("ds002718", "ds002718"), ["ds002718"])

    def test_case_insensitive_and_stripped(self) -> None:
        self.assertEqual(accession_search_terms(" DS002718 "), ["ds002718"])

    def test_malformed_inputs_dropped(self) -> None:
        # Wrong prefix, wrong digit count, empty, or None are not searched.
        self.assertEqual(accession_search_terms("dataset-1"), [])
        self.assertEqual(accession_search_terms("ds123"), [])
        self.assertEqual(accession_search_terms("ds0027180"), [])
        self.assertEqual(accession_search_terms(""), [])
        self.assertEqual(accession_search_terms("on005964", None), ["on005964"])

    def test_malformed_source_id_dropped_keeps_valid_dataset_id(self) -> None:
        self.assertEqual(
            accession_search_terms("nm000207", "not-an-accession"), ["nm000207"]
        )
