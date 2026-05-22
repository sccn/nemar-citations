"""Tests for `dataset_citations.quality.anchor_judgment`.

No mocks. The LLM and opencite layers are replaced with real subclasses that
return hand-built records (the pattern used by
`tests/test_quality_llm_client.py::_FakeClient` and
`tests/test_core_opencite_pipeline.py::_StubBackend`).

Integration tests against a live Ollama daemon are gated behind
RUN_INTEGRATION_TESTS=1.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import TestCase, skipUnless

from dataset_citations.backends.opencite_backend import OpenCiteBackend
from dataset_citations.quality.anchor_judgment import (
    JudgmentRecord,
    is_judgment_fresh,
    judge_dataset_anchors,
    load_judgment_sidecar,
    save_judgment_sidecar,
)
from dataset_citations.quality.dataset_metadata import DatasetMetadataRetriever
from dataset_citations.quality.llm_client import OllamaJudgmentClient
from dataset_citations.sources.models import (
    Author,
    CitingWork,
    DoiReference,
    FetchError,
    FetchSuccess,
)


class _FakeClient(OllamaJudgmentClient):
    """OllamaJudgmentClient subclass that bypasses the HTTP step.

    Mirrors the `_FakeClient` in `test_quality_llm_client.py`. Each call to
    `judge_anchor` consumes one entry from `responses` (in order). If
    `responses` runs out, the last response is reused; this matches the
    behavior most tests need (single-anchor scenarios) while still letting
    multi-anchor tests script the LLM's per-call output.
    """

    def __init__(
        self,
        responses: list[str] | str = '{"classification": "data_paper", "reason": "ok"}',
    ) -> None:
        # Skip parent __init__ so no httpx.Client is constructed.
        self.base_url = "http://test"
        self.model = "test-model"
        self.timeout = 5
        if isinstance(responses, str):
            self._responses = [responses]
        else:
            self._responses = list(responses)
        self._call_index = 0

    def _generate(self, prompt: str) -> str:  # noqa: ARG002 - prompt unused
        if self._call_index < len(self._responses):
            response = self._responses[self._call_index]
            self._call_index += 1
            return response
        return self._responses[-1]

    def health_check(self) -> bool:  # override so tests don't touch network
        return True


class _StubBackend(OpenCiteBackend):
    """OpenCiteBackend test double that returns preset `get_paper` results."""

    def __init__(self, papers: dict[str, FetchSuccess | FetchError]) -> None:
        # Skip parent init so we don't read OPENCITE config.
        self._papers = papers
        self._config = None  # type: ignore[assignment]
        self._max_results_per_doi = 100
        self._concurrency = 1

    def get_paper(self, doi: str):  # type: ignore[override]
        return self._papers[doi]


class _StubSource:
    """Real source-shaped object returning a fixed FetchResult."""

    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def get_doi_references(self, dataset_id):  # noqa: ARG002
        return self._outcome


class _StubMetadataRetriever:
    """Real retriever-shaped object returning a canned dataset metadata dict."""

    def __init__(self, text: str = "Stub dataset description.") -> None:
        self._text = text

    def get_dataset_metadata(self, dataset_id: str) -> dict:
        return {
            "dataset_id": dataset_id,
            "dataset_description": {"Name": self._text},
            "readme_content": None,
            "github_info": {"description": None},
        }


def _make_work(
    *,
    title: str = "Sample paper",
    doi: str = "10.1234/example",
    venue: str | None = "Journal of Tests",
    year: int | None = 2024,
    abstract: str | None = "A stub abstract.",
    source_doi: str | None = None,
) -> CitingWork:
    return CitingWork(
        title=title,
        doi=doi,
        pmid=None,
        openalex_id=None,
        year=year,
        authors=(Author(name="A. Researcher"),),
        venue=venue,
        abstract=abstract,
        citation_count=10,
        source_doi=source_doi or doi,
        source_relation="References",
    )


class JudgeDatasetAnchorsTests(TestCase):
    def test_happy_path_produces_locked_schema(self) -> None:
        ref = DoiReference(
            identifier="10.1234/example",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        source = _StubSource(FetchSuccess([ref]))
        backend = _StubBackend(
            {ref.identifier: FetchSuccess(_make_work(source_doi=ref.identifier))}
        )
        client = _FakeClient(
            '{"classification": "umbrella", "reason": "broad initiative paper"}'
        )

        payload = judge_dataset_anchors(
            "nm000104",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=_StubSource(FetchError("not_found", "unused")),  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )

        # Top-level locked fields.
        self.assertEqual(payload["dataset_id"], "nm000104")
        self.assertEqual(payload["judgment_model"], "test-model")
        self.assertIn("judged_at", payload)
        self.assertEqual(len(payload["judgments"]), 1)

        judgment = payload["judgments"][0]
        self.assertEqual(judgment["anchor_identifier"], "10.1234/example")
        self.assertEqual(judgment["anchor_identifier_type"], "doi")
        self.assertEqual(judgment["source_relation"], "IsDerivedFrom")
        self.assertEqual(judgment["classification"], "umbrella")
        self.assertEqual(judgment["reason"], "broad initiative paper")
        self.assertEqual(judgment["paper_title"], "Sample paper")
        self.assertEqual(judgment["paper_year"], 2024)
        self.assertEqual(judgment["paper_venue"], "Journal of Tests")
        self.assertIsNone(judgment["error"])

    def test_ds_prefix_routes_to_bids_source(self) -> None:
        """ds-prefixed ids must consult `bids_source`, not `nemar_source`."""
        ref = DoiReference(
            identifier="10.5555/bids",
            identifier_type="doi",
            relation_type="References",
            source="openneuro_description",
        )
        bids = _StubSource(FetchSuccess([ref]))
        nemar = _StubSource(FetchError("not_found", "should not be called for ds"))
        backend = _StubBackend(
            {ref.identifier: FetchSuccess(_make_work(source_doi=ref.identifier))}
        )
        client = _FakeClient(
            '{"classification": "data_paper", "reason": "describes the dataset"}'
        )

        payload = judge_dataset_anchors(
            "ds000117",
            nemar_source=nemar,  # type: ignore[arg-type]
            bids_source=bids,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        self.assertEqual(len(payload["judgments"]), 1)
        self.assertEqual(payload["judgments"][0]["classification"], "data_paper")

    def test_source_error_produces_empty_judgments(self) -> None:
        source = _StubSource(FetchError("not_found", "missing metadata"))
        backend = _StubBackend({})
        client = _FakeClient()

        payload = judge_dataset_anchors(
            "nm999999",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=source,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        self.assertEqual(payload["judgments"], [])
        self.assertEqual(payload["dataset_id"], "nm999999")

    def test_no_doi_anchors_produces_empty_judgments(self) -> None:
        source = _StubSource(FetchSuccess([]))
        backend = _StubBackend({})
        client = _FakeClient()

        payload = judge_dataset_anchors(
            "nm000104",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=source,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        self.assertEqual(payload["judgments"], [])

    def test_paper_lookup_failure_records_error(self) -> None:
        ref = DoiReference(
            identifier="10.1234/missing",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        source = _StubSource(FetchSuccess([ref]))
        backend = _StubBackend(
            {ref.identifier: FetchError("not_found", "openalex 404")}
        )
        client = _FakeClient()

        payload = judge_dataset_anchors(
            "nm000104",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=source,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        self.assertEqual(len(payload["judgments"]), 1)
        judgment = payload["judgments"][0]
        self.assertIsNotNone(judgment["error"])
        self.assertIn("paper_lookup_failed", judgment["error"])
        self.assertIsNone(judgment["paper_title"])
        self.assertEqual(judgment["classification"], "")

    def test_llm_judgment_failure_records_error(self) -> None:
        """When the LLM returns out-of-taxonomy output, the record carries
        `error` but keeps the paper bib fields the lookup did fetch."""
        ref = DoiReference(
            identifier="10.1234/example",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        source = _StubSource(FetchSuccess([ref]))
        backend = _StubBackend(
            {ref.identifier: FetchSuccess(_make_work(source_doi=ref.identifier))}
        )
        client = _FakeClient('{"classification": "garbage_label", "reason": "bad"}')

        payload = judge_dataset_anchors(
            "nm000104",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=source,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        judgment = payload["judgments"][0]
        self.assertIsNotNone(judgment["error"])
        self.assertIn("llm_judgment_failed", judgment["error"])
        # paper bib survives even though judgment failed.
        self.assertEqual(judgment["paper_title"], "Sample paper")
        self.assertEqual(judgment["paper_year"], 2024)
        self.assertEqual(judgment["classification"], "")

    def test_multiple_anchors_judged_sequentially(self) -> None:
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
        source = _StubSource(FetchSuccess([ref_a, ref_b]))
        backend = _StubBackend(
            {
                ref_a.identifier: FetchSuccess(
                    _make_work(title="A paper", source_doi=ref_a.identifier)
                ),
                ref_b.identifier: FetchSuccess(
                    _make_work(title="B paper", source_doi=ref_b.identifier)
                ),
            }
        )
        client = _FakeClient(
            [
                '{"classification": "data_paper", "reason": "first"}',
                '{"classification": "methodology", "reason": "second"}',
            ]
        )

        payload = judge_dataset_anchors(
            "nm000104",
            nemar_source=source,  # type: ignore[arg-type]
            bids_source=source,  # type: ignore[arg-type]
            metadata_retriever=_StubMetadataRetriever(),  # type: ignore[arg-type]
            backend=backend,
            client=client,
        )
        self.assertEqual(len(payload["judgments"]), 2)
        classes = [j["classification"] for j in payload["judgments"]]
        self.assertEqual(classes, ["data_paper", "methodology"])


class SidecarRoundTripTests(TestCase):
    def test_round_trip_preserves_locked_fields(self) -> None:
        record = JudgmentRecord(
            anchor_identifier="10.1234/example",
            anchor_identifier_type="doi",
            source_relation="IsDerivedFrom",
            classification="umbrella",
            reason="broad initiative",
            paper_title="A paper",
            paper_year=2024,
            paper_venue="Journal of Tests",
            judged_at="2026-05-22T12:00:00+00:00",
            error=None,
        )
        payload = {
            "dataset_id": "nm000104",
            "judged_at": "2026-05-22T12:00:00+00:00",
            "judgment_model": "test-model",
            "judgments": [record.to_dict()],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nm000104.json"
            save_judgment_sidecar(path, payload)
            loaded = load_judgment_sidecar(path)
        self.assertEqual(loaded["dataset_id"], "nm000104")
        self.assertEqual(loaded["judgment_model"], "test-model")
        self.assertEqual(len(loaded["judgments"]), 1)
        judgment = loaded["judgments"][0]
        for field in (
            "anchor_identifier",
            "anchor_identifier_type",
            "source_relation",
            "classification",
            "reason",
            "paper_title",
            "paper_year",
            "paper_venue",
            "judged_at",
            "error",
        ):
            self.assertIn(field, judgment, f"{field} missing after round-trip")
        self.assertEqual(judgment["classification"], "umbrella")
        self.assertIsNone(judgment["error"])

    def test_save_writes_atomically_no_partial(self) -> None:
        """`save_judgment_sidecar` uses os.replace so the target file is
        either the new payload or the previous one — never a half-written
        file. We verify the cleanup-after-failure path keeps the target
        intact."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ds000117.json"
            # Seed an initial payload on disk.
            save_judgment_sidecar(path, {"dataset_id": "ds000117", "judgments": []})

            # Save again with a non-serializable value to force a failure
            # mid-write. The pre-existing file must remain valid JSON.
            bad_payload = {"dataset_id": "ds000117", "judgments": [{"x": object()}]}
            with self.assertRaises(TypeError):
                save_judgment_sidecar(path, bad_payload)

            # File still parses and matches the prior good payload.
            survivor = load_judgment_sidecar(path)
            self.assertEqual(survivor["dataset_id"], "ds000117")
            # No `.tmp` litter left behind in the parent directory.
            leftovers = [p for p in Path(tmp).iterdir() if p.suffix == ".tmp"]
            self.assertEqual(leftovers, [])

    def test_load_rejects_non_object_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(["not", "an", "object"]))
            with self.assertRaises(ValueError):
                load_judgment_sidecar(path)


class IsJudgmentFreshTests(TestCase):
    def test_fresh_payload_returns_true(self) -> None:
        payload = {
            "judged_at": datetime.now(timezone.utc).isoformat(),
        }
        self.assertTrue(is_judgment_fresh(payload, max_age_days=7))

    def test_stale_payload_returns_false(self) -> None:
        stale = datetime.now(timezone.utc) - timedelta(days=30)
        payload = {"judged_at": stale.isoformat()}
        self.assertFalse(is_judgment_fresh(payload, max_age_days=7))

    def test_zero_max_age_days_returns_false(self) -> None:
        payload = {"judged_at": datetime.now(timezone.utc).isoformat()}
        self.assertFalse(is_judgment_fresh(payload, max_age_days=0))

    def test_negative_max_age_days_returns_false(self) -> None:
        payload = {"judged_at": datetime.now(timezone.utc).isoformat()}
        self.assertFalse(is_judgment_fresh(payload, max_age_days=-1))

    def test_missing_judged_at_returns_false(self) -> None:
        self.assertFalse(is_judgment_fresh({}, max_age_days=7))

    def test_malformed_judged_at_returns_false(self) -> None:
        self.assertFalse(is_judgment_fresh({"judged_at": "not-a-date"}, max_age_days=7))

    def test_naive_timestamp_treated_as_utc(self) -> None:
        naive_now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        self.assertTrue(is_judgment_fresh({"judged_at": naive_now}, max_age_days=7))


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live ollama call; set RUN_INTEGRATION_TESTS=1 to enable",
)
class AnchorJudgmentIntegration(TestCase):
    """Live integration test: builds a sidecar for one dataset against a
    real Ollama daemon. Uses a hand-built DoiReference to avoid hitting
    GitHub/NEMAR catalog rate limits during CI."""

    def test_round_trip_via_real_ollama(self) -> None:
        ref = DoiReference(
            identifier="10.3389/fnins.2013.00267",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="openneuro_description",
        )

        class _OneRefSource:
            def get_doi_references(self, dataset_id):  # noqa: ARG002
                return FetchSuccess([ref])

        with OllamaJudgmentClient() as client:
            if not client.health_check():
                self.skipTest("ollama daemon not reachable")
            backend = OpenCiteBackend(max_results_per_doi=1)
            retriever = DatasetMetadataRetriever()
            payload = judge_dataset_anchors(
                "ds000117",
                nemar_source=_OneRefSource(),  # type: ignore[arg-type]
                bids_source=_OneRefSource(),  # type: ignore[arg-type]
                metadata_retriever=retriever,
                backend=backend,
                client=client,
            )
        self.assertEqual(payload["dataset_id"], "ds000117")
        self.assertEqual(len(payload["judgments"]), 1)
