"""Tests for src/dataset_citations/sources/doi.py helpers.

Pure-function unit tests. No network, no mocks.
"""

from __future__ import annotations

from unittest import TestCase

from dataset_citations.sources.doi import (
    extract_identifiers,
    is_openneuro_dataset_doi,
    normalize_doi,
    validate_identifier,
)


class NormalizeDoiTests(TestCase):
    def test_strips_doi_prefix(self) -> None:
        self.assertEqual(
            normalize_doi("doi:10.1038/SDATA.2015.1"), "10.1038/sdata.2015.1"
        )

    def test_strips_full_url(self) -> None:
        self.assertEqual(
            normalize_doi("https://doi.org/10.1038/sdata.2015.1"),
            "10.1038/sdata.2015.1",
        )
        self.assertEqual(
            normalize_doi("http://dx.doi.org/10.1038/sdata.2015.1"),
            "10.1038/sdata.2015.1",
        )

    def test_trims_trailing_punctuation(self) -> None:
        self.assertEqual(normalize_doi("10.1038/sdata.2015.1."), "10.1038/sdata.2015.1")
        self.assertEqual(normalize_doi("10.1038/sdata.2015.1,"), "10.1038/sdata.2015.1")
        self.assertEqual(normalize_doi("10.1038/sdata.2015.1;"), "10.1038/sdata.2015.1")

    def test_balances_trailing_parens(self) -> None:
        # "see (10.1038/sdata.2015.1)" parsed; the trailing `)` should drop.
        self.assertEqual(normalize_doi("10.1038/sdata.2015.1)"), "10.1038/sdata.2015.1")

    def test_keeps_internal_parens(self) -> None:
        self.assertEqual(normalize_doi("10.1234/foo(bar)baz"), "10.1234/foo(bar)baz")


class ValidateIdentifierTests(TestCase):
    def test_accepts_valid_doi(self) -> None:
        self.assertTrue(validate_identifier("10.1038/sdata.2015.1"))

    def test_accepts_pmid(self) -> None:
        self.assertTrue(validate_identifier("pmid:25977808"))

    def test_accepts_arxiv_with_version(self) -> None:
        self.assertTrue(validate_identifier("arxiv:2106.15928v2"))

    def test_rejects_newline(self) -> None:
        self.assertFalse(validate_identifier("10.1038/sdata\n.2015.1"))

    def test_rejects_carriage_return(self) -> None:
        self.assertFalse(validate_identifier("10.1038/sdata.2015.1\r"))

    def test_rejects_empty(self) -> None:
        self.assertFalse(validate_identifier(""))

    def test_rejects_oversized(self) -> None:
        self.assertFalse(validate_identifier("10.1234/" + "x" * 300))

    def test_rejects_garbage(self) -> None:
        self.assertFalse(validate_identifier("not a doi"))


class IsOpenneuroDatasetDoiTests(TestCase):
    def test_matches_openneuro_pattern(self) -> None:
        self.assertTrue(is_openneuro_dataset_doi("10.18112/openneuro.ds000117.v1.1.0"))

    def test_rejects_regular_doi(self) -> None:
        self.assertFalse(is_openneuro_dataset_doi("10.1038/sdata.2015.1"))


class ExtractIdentifiersTests(TestCase):
    def test_extracts_doi(self) -> None:
        results = extract_identifiers("See 10.1038/sdata.2015.1 for details.")
        self.assertIn(("10.1038/sdata.2015.1", "doi"), results)

    def test_extracts_pmid_from_url(self) -> None:
        text = "Cite https://www.ncbi.nlm.nih.gov/pubmed/25977808"
        self.assertEqual(extract_identifiers(text), [("pmid:25977808", "pmid")])

    def test_extracts_pmid_from_short_url(self) -> None:
        self.assertEqual(
            extract_identifiers("pubmed/12345678"),
            [("pmid:12345678", "pmid")],
        )

    def test_extracts_arxiv_from_tag(self) -> None:
        self.assertIn(
            ("arxiv:2106.15928v2", "arxiv"),
            extract_identifiers("see arxiv:2106.15928v2"),
        )

    def test_extracts_arxiv_from_doi_shorthand(self) -> None:
        # 10.48550/arxiv.X is the canonical arXiv DOI; we should record it as
        # arxiv:X and not double-extract as a bare DOI.
        results = extract_identifiers("arxiv: 10.48550/arxiv.1602.00904")
        kinds = {kind for _, kind in results}
        self.assertIn("arxiv", kinds)
        self.assertNotIn("doi", kinds)

    def test_deduplicates(self) -> None:
        text = "see 10.1038/sdata.2015.1 and again https://doi.org/10.1038/sdata.2015.1"
        results = extract_identifiers(text)
        self.assertEqual(len([r for r in results if r[1] == "doi"]), 1)

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(extract_identifiers(""), [])
        self.assertEqual(extract_identifiers(None), [])
