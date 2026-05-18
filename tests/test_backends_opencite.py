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

    def test_classify_error_rate_limit(self) -> None:
        from dataset_citations.backends.opencite_backend import _classify_error

        err = _classify_error(RuntimeError("HTTP 429 too many requests"), "x")
        self.assertEqual(err.reason, "rate_limit")

    def test_classify_error_not_found(self) -> None:
        from dataset_citations.backends.opencite_backend import _classify_error

        err = _classify_error(RuntimeError("HTTP 404 not found"), "x")
        self.assertEqual(err.reason, "not_found")

    def test_classify_error_auth(self) -> None:
        from dataset_citations.backends.opencite_backend import _classify_error

        err = _classify_error(RuntimeError("HTTP 401 unauthorized"), "x")
        self.assertEqual(err.reason, "auth")

    def test_classify_error_network(self) -> None:
        from dataset_citations.backends.opencite_backend import _classify_error

        err = _classify_error(TimeoutError("connection timeout"), "x")
        self.assertEqual(err.reason, "network")

    def test_classify_error_other(self) -> None:
        from dataset_citations.backends.opencite_backend import _classify_error

        err = _classify_error(RuntimeError("totally unexpected"), "x")
        self.assertEqual(err.reason, "other")
