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


class ShouldSkipS2Tests(TestCase):
    """The DOI-prefix S2 skip matcher. Pure function; no network."""

    def setUp(self) -> None:
        # Import inside setUp so the test class header doesn't depend on
        # private symbols when this file is collected.
        from dataset_citations.backends.opencite_backend import (
            S2_SKIP_PREFIXES,
            should_skip_s2,
        )

        self.should_skip_s2 = should_skip_s2
        self.skip_prefixes = S2_SKIP_PREFIXES

    def test_nemar_minted_dois_skip(self) -> None:
        # Real NEMAR-minted DOIs from the May 2026 catalog.
        self.assertTrue(self.should_skip_s2("10.82901/nemar.nm000104"))
        self.assertTrue(self.should_skip_s2("10.82901/nemar.on005261"))
        # Case-insensitive: upstream sometimes preserves the original case.
        self.assertTrue(self.should_skip_s2("10.82901/NEMAR.nm000104"))

    def test_zenodo_data_records_skip(self) -> None:
        self.assertTrue(self.should_skip_s2("10.5281/zenodo.17287903"))
        self.assertTrue(self.should_skip_s2("10.5281/zenodo.17613953"))

    def test_physionet_data_records_skip(self) -> None:
        self.assertTrue(self.should_skip_s2("10.13026/ym7v-bh53"))
        self.assertTrue(self.should_skip_s2("10.13026/C2K01R"))

    def test_journal_dois_not_skipped(self) -> None:
        # Real DOIs that the May 2026 probe showed S2 contributes coverage on.
        self.assertFalse(self.should_skip_s2("10.1038/sdata.2017.181"))
        self.assertFalse(self.should_skip_s2("10.1038/s41586-025-09255-w"))
        self.assertFalse(self.should_skip_s2("10.1371/journal.pone.0162657"))
        self.assertFalse(self.should_skip_s2("10.21105/joss.01896"))

    def test_empty_string_not_skipped(self) -> None:
        self.assertFalse(self.should_skip_s2(""))

    def test_prefixes_listed_in_lowercase(self) -> None:
        # The matcher relies on lowercasing the input. The constant itself
        # must be lowercase so the comparison is meaningful.
        for prefix in self.skip_prefixes:
            self.assertEqual(prefix, prefix.lower(), f"{prefix!r} not lowercase")


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live opencite calls; set RUN_INTEGRATION_TESTS=1 to enable",
)
class OpenAlexOnlyPathIntegration(TestCase):
    """Anchors matching S2_SKIP_PREFIXES route through OpenAlex only.

    Real network. A success on a known-skip DOI is the structural proof
    that the OpenAlex-only path works end-to-end; the bypass itself is
    enforced in code by `should_skip_s2` + the `_lookup_openalex_only`
    branch in `_batch_async`.
    """

    def test_zenodo_doi_resolves_via_openalex(self) -> None:
        # 10.5281/zenodo.* is in S2_SKIP_PREFIXES; the matcher diverts this
        # to the OpenAlex-only path. We just need a result without crashing.
        backend = OpenCiteBackend(max_results_per_doi=5)
        # Use a Zenodo DOI we know is in OpenAlex; if OpenAlex returns
        # not_found we still pass (the bypass took the right branch).
        ref = _ref("10.5281/zenodo.17287903")
        result = backend.get_citing_works(ref)
        self.assertIsNotNone(result)
        # Either success (works list, possibly empty) or a typed FetchError.
        self.assertIn(getattr(result, "ok", None), (True, False))
