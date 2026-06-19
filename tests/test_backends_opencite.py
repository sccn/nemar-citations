"""Tests for OpenCiteBackend.

Live opencite lookups are gated behind RUN_INTEGRATION_TESTS=1 because they
hit external APIs (OpenAlex, Semantic Scholar) and depend on network /
rate limits. The default test suite skips them.
"""

from __future__ import annotations

import os
from unittest import TestCase, skipUnless

from dataset_citations.backends import OpenCiteBackend
from dataset_citations.sources.models import (
    DoiReference,
    FetchError,
    FetchSuccess,
)


def _ref(identifier: str, identifier_type: str = "doi") -> DoiReference:
    return DoiReference(
        identifier=identifier,
        identifier_type=identifier_type,  # type: ignore[arg-type]
        relation_type="References",
        source="nemar_metadata",
        source_field="related_identifiers",
    )


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live opencite calls; set RUN_INTEGRATION_TESTS=1 to enable",
)
class OpenCiteBackendIntegration(TestCase):
    def setUp(self) -> None:
        self.backend = OpenCiteBackend(max_results_per_doi=10)

    def test_citing_works_for_known_doi(self) -> None:
        ref = _ref("10.1038/sdata.2015.1")
        result = self.backend.get_citing_works(ref)
        self.assertIsInstance(result, FetchSuccess)
        assert isinstance(result, FetchSuccess)
        self.assertGreater(len(result.value), 0)
        first = result.value[0]
        self.assertTrue(first.title)
        self.assertEqual(first.source_doi, ref.identifier)
        self.assertEqual(first.source_relation, "References")

    def test_unknown_identifier_returns_error(self) -> None:
        ref = _ref("10.99999/this-doi-does-not-exist-xyzabc")
        result = self.backend.get_citing_works(ref)
        self.assertIsInstance(result, FetchError)

    def test_batch_lookup(self) -> None:
        refs = [
            _ref("10.1038/sdata.2015.1"),
            _ref("10.1038/sdata.2017.181"),
        ]
        out = self.backend.get_citing_works_batch(refs)
        self.assertEqual(set(out.keys()), {r.identifier for r in refs})

    def test_get_paper_returns_anchor_metadata(self) -> None:
        # Real OpenAlex lookup of a well-indexed anchor paper.
        result = self.backend.get_paper("10.1038/sdata.2015.1")
        self.assertIsInstance(result, FetchSuccess)
        assert isinstance(result, FetchSuccess)
        paper = result.value
        self.assertTrue(paper.title)
        self.assertEqual(paper.source_doi, "10.1038/sdata.2015.1")

    def test_get_paper_unknown_doi_returns_error(self) -> None:
        result = self.backend.get_paper("10.99999/never-existed-zzz")
        self.assertIsInstance(result, FetchError)


class OpenCiteBackendUnitTests(TestCase):
    """Cheap tests that exercise the backend's error-classification path
    without hitting the network."""

    def test_empty_batch_returns_empty_dict(self) -> None:
        backend = OpenCiteBackend()
        self.assertEqual(backend.get_citing_works_batch([]), {})

    def testclassify_error_rate_limit(self) -> None:
        from dataset_citations.backends.opencite_backend import classify_error

        err = classify_error(RuntimeError("HTTP 429 too many requests"), "x")
        self.assertEqual(err.reason, "rate_limit")

    def testclassify_error_not_found(self) -> None:
        from dataset_citations.backends.opencite_backend import classify_error

        err = classify_error(RuntimeError("HTTP 404 not found"), "x")
        self.assertEqual(err.reason, "not_found")

    def testclassify_error_auth(self) -> None:
        from dataset_citations.backends.opencite_backend import classify_error

        err = classify_error(RuntimeError("HTTP 401 unauthorized"), "x")
        self.assertEqual(err.reason, "auth")

    def testclassify_error_network(self) -> None:
        from dataset_citations.backends.opencite_backend import classify_error

        err = classify_error(TimeoutError("connection timeout"), "x")
        self.assertEqual(err.reason, "network")

    def testclassify_error_other(self) -> None:
        from dataset_citations.backends.opencite_backend import classify_error

        err = classify_error(RuntimeError("totally unexpected"), "x")
        self.assertEqual(err.reason, "other")


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live opencite calls; set RUN_INTEGRATION_TESTS=1 to enable",
)
class DelegatedPathIntegration(TestCase):
    """All anchors flow through opencite's `CitationExplorer`.

    Real network. The backend no longer routes anchors per-DOI-prefix;
    source selection and rate limiting are delegated to opencite (see the
    module docstring of `opencite_backend`). These tests prove the single
    delegated path completes the round-trip without crashing for both a
    data-record DOI and a journal DOI.
    """

    def test_data_record_doi_resolves(self) -> None:
        # A Zenodo data record (formerly an S2-skip family). The delegated
        # path must handle it without special-casing. Either FetchSuccess or
        # a typed FetchError is acceptable since OpenAlex's catalog may or may
        # not cover the DOI; the contract is that it does not crash.
        backend = OpenCiteBackend(max_results_per_doi=5)
        ref = _ref("10.5281/zenodo.17287903")
        result = backend.get_citing_works(ref)
        self.assertIsInstance(result, (FetchSuccess, FetchError))
        if isinstance(result, FetchSuccess):
            for work in result.value:
                self.assertTrue(work.title)
                self.assertEqual(work.source_doi, ref.identifier)

    def test_disabled_sources_runs_openalex_only(self) -> None:
        # Config-driven source selection: disabling S2 via opencite's
        # `disabled_sources` must still yield a working OpenAlex-only fetch,
        # with no local routing involved.
        prior = os.environ.get("OPENCITE_DISABLED_SOURCES")
        os.environ["OPENCITE_DISABLED_SOURCES"] = "s2"
        try:
            backend = OpenCiteBackend(max_results_per_doi=5)
            result = backend.get_citing_works(_ref("10.1038/sdata.2015.1"))
            self.assertIsInstance(result, (FetchSuccess, FetchError))
        finally:
            if prior is None:
                os.environ.pop("OPENCITE_DISABLED_SOURCES", None)
            else:
                os.environ["OPENCITE_DISABLED_SOURCES"] = prior
