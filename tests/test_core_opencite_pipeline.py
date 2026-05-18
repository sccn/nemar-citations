"""Tests for src/dataset_citations/core/opencite_pipeline.py.

The opencite backend is replaced in unit tests by a subclass that returns
hardcoded `FetchSuccess` / `FetchError` results. This is real code (no
unittest.mock), keeps the no-mocks rule, and lets us exercise the dedup,
error-propagation, and schema-shape branches without hitting the network.

Integration tests run live opencite lookups and are gated behind
RUN_INTEGRATION_TESTS=1.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest import TestCase, skipUnless

from dataset_citations.backends.opencite_backend import OpenCiteBackend
from dataset_citations.core.opencite_pipeline import (
    fetch_dataset_citations_via_opencite,
)
from dataset_citations.sources.models import (
    Author,
    CitingWork,
    DoiReference,
    FetchError,
    FetchSuccess,
)


def _make_work(
    title: str,
    *,
    doi: str | None,
    source_doi: str,
    source_relation: str = "References",
    citation_count: int = 10,
) -> CitingWork:
    return CitingWork(
        title=title,
        doi=doi,
        pmid=None,
        openalex_id=None,
        year=2020,
        authors=(Author(name="A. Researcher"),),
        venue="Journal of Tests",
        abstract=None,
        citation_count=citation_count,
        source_doi=source_doi,
        source_relation=source_relation,  # type: ignore[arg-type]
    )


class _StubBackend(OpenCiteBackend):
    """Real OpenCiteBackend subclass; overrides the batch method to return
    a hand-built map. Not a mock; this is the project's no-mocks pattern."""

    def __init__(self, batch_outcome: dict[str, FetchSuccess | FetchError]):
        # Skip parent init so we don't try to read OPENCITE config.
        self._batch_outcome = batch_outcome
        self._config = None  # type: ignore[assignment]
        self._max_results_per_doi = 100
        self._concurrency = 1

    def get_citing_works_batch(self, refs):  # type: ignore[override]
        return {r.identifier: self._batch_outcome[r.identifier] for r in refs}


class _StubSource:
    """Real source-shaped object returning a fixed FetchResult."""

    def __init__(self, outcome):
        self._outcome = outcome

    def get_doi_references(self, dataset_id):  # noqa: ARG002
        return self._outcome


WHEN = datetime(2026, 5, 18, tzinfo=timezone.utc)


class FetchViaOpenCiteTests(TestCase):
    def test_unsupported_prefix_returns_stub(self) -> None:
        out = fetch_dataset_citations_via_opencite(
            "xx123", fetch_date=WHEN, backend=_StubBackend({})
        )
        self.assertEqual(out["num_citations"], 0)
        self.assertIn("unsupported_prefix", out["metadata"]["fetch_status"])

    def test_source_error_propagated(self) -> None:
        bids = _StubSource(FetchError("not_found", "missing"))
        out = fetch_dataset_citations_via_opencite(
            "ds000999",
            backend=_StubBackend({}),
            bids_source=bids,
            fetch_date=WHEN,
        )
        self.assertEqual(out["metadata"]["fetch_status"], "not_found")
        self.assertEqual(out["citation_details"], [])

    def test_no_references_returns_no_doi_status(self) -> None:
        bids = _StubSource(FetchSuccess([]))
        out = fetch_dataset_citations_via_opencite(
            "ds000999",
            backend=_StubBackend({}),
            bids_source=bids,
            fetch_date=WHEN,
        )
        self.assertEqual(out["metadata"]["fetch_status"], "no_doi_references")

    def test_happy_path_produces_schema_v2(self) -> None:
        ref = DoiReference(
            identifier="10.1038/sdata.2015.1",
            identifier_type="doi",
            relation_type="References",
            source="openneuro_description",
            source_field="ReferencesAndLinks",
        )
        bids = _StubSource(FetchSuccess([ref]))
        backend = _StubBackend(
            {
                ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "Method paper",
                            doi="10.1234/method",
                            source_doi=ref.identifier,
                        )
                    ]
                )
            }
        )
        out = fetch_dataset_citations_via_opencite(
            "ds000117",
            backend=backend,
            bids_source=bids,
            fetch_date=WHEN,
        )
        self.assertEqual(out["dataset_id"], "ds000117")
        self.assertEqual(out["num_citations"], 1)
        self.assertEqual(out["metadata"]["schema_version"], "2.0")
        self.assertEqual(out["metadata"]["discovery_backend"], "opencite")
        self.assertEqual(out["metadata"]["anchor_count"], 1)
        entry = out["citation_details"][0]
        self.assertEqual(entry["title"], "Method paper")
        self.assertEqual(entry["source_doi"], "10.1038/sdata.2015.1")
        self.assertEqual(entry["source_relation"], "References")
        self.assertEqual(entry["discovery_backend"], "opencite")

    def test_dedup_across_anchors(self) -> None:
        ref_a = DoiReference(
            identifier="10.1234/A",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        ref_b = DoiReference(
            identifier="10.1234/B",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        shared_work = _make_work(
            "Same paper cites both", doi="10.5555/cited", source_doi=ref_a.identifier
        )
        unique_to_b = _make_work(
            "Only cites B", doi="10.5555/only-b", source_doi=ref_b.identifier
        )
        nemar = _StubSource(FetchSuccess([ref_a, ref_b]))
        backend = _StubBackend(
            {
                ref_a.identifier: FetchSuccess([shared_work]),
                ref_b.identifier: FetchSuccess([shared_work, unique_to_b]),
            }
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000103",
            backend=backend,
            nemar_source=nemar,
            fetch_date=WHEN,
        )
        self.assertEqual(out["num_citations"], 2)
        titles = {c["title"] for c in out["citation_details"]}
        self.assertEqual(titles, {"Same paper cites both", "Only cites B"})

    def test_all_anchors_rate_limited_surfaces_dominant_reason(self) -> None:
        ref = DoiReference(
            identifier="10.1234/A",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([ref]))
        backend = _StubBackend(
            {ref.identifier: FetchError("rate_limit", "429 too many")}
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000103",
            backend=backend,
            nemar_source=nemar,
            fetch_date=WHEN,
        )
        self.assertEqual(out["metadata"]["fetch_status"], "rate_limit")
        self.assertEqual(
            out["metadata"]["anchor_errors"], {ref.identifier: "rate_limit"}
        )
        self.assertEqual(out["citation_details"], [])


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live opencite lookup; set RUN_INTEGRATION_TESTS=1 to enable",
)
class FetchViaOpenCiteIntegration(TestCase):
    def test_ds000117_live(self) -> None:
        out = fetch_dataset_citations_via_opencite("ds000117")
        # Either we get real citations or a transient FetchError; both are
        # acceptable for the integration test as long as the schema is right.
        self.assertEqual(out["dataset_id"], "ds000117")
        self.assertEqual(out["metadata"]["schema_version"], "2.0")
        self.assertEqual(out["metadata"]["discovery_backend"], "opencite")
        if out["num_citations"] > 0:
            entry = out["citation_details"][0]
            self.assertTrue(entry.get("title"))
            self.assertEqual(entry.get("discovery_backend"), "opencite")
