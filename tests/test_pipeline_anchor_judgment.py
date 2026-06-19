"""Tests for phase 3 pipeline integration with the anchor-judgment sidecar.

Real-data only: a `_StubBackend` (matching the pattern in
`tests/test_core_opencite_pipeline.py`) plus a `_StubSource` returning
hand-built `DoiReference` records, and on-disk sidecar JSONs written into a
per-test tempdir. No `unittest.mock` per `.rules/testing.md`.

The locked sidecar shape lives in epic #76's phase 2 contract (see issue
#86). Tests below construct the JSON manually so a phase 2 schema rename
breaks this file loudly instead of silently.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from dataset_citations.backends.opencite_backend import OpenCiteBackend
from dataset_citations.core.opencite_pipeline import (
    fetch_dataset_citations_via_opencite,
)
from dataset_citations.quality.anchor_judgment_io import (
    JudgmentSidecar,
    canonical_anchor_key,
    load_judgment_lookup,
    load_judgment_sidecar,
)
from dataset_citations.quality.llm_client import ALLOWED_CLASSIFICATIONS
from dataset_citations.sources.models import (
    Author,
    CitingWork,
    DoiReference,
    FetchSuccess,
)
from dataset_citations.sources.nemar_metadata import NemarDatasetMetadata

WHEN = datetime(2026, 5, 22, tzinfo=timezone.utc)


def _make_work(
    title: str,
    *,
    doi: str | None,
    source_doi: str,
    source_relation: str = "References",
    citation_count: int = 7,
) -> CitingWork:
    return CitingWork(
        title=title,
        doi=doi,
        pmid=None,
        openalex_id=None,
        year=2024,
        authors=(Author(name="A. Researcher"),),
        venue="Journal of Tests",
        abstract=None,
        citation_count=citation_count,
        source_doi=source_doi,
        source_relation=source_relation,  # type: ignore[arg-type]
    )


class _StubBackend(OpenCiteBackend):
    """OpenCiteBackend test double; records which anchors it received."""

    def __init__(self, batch_outcome):
        self._batch_outcome = batch_outcome
        self.calls: list[list[str]] = []
        self._config = None  # type: ignore[assignment]
        self._max_results_per_doi = 100
        self._concurrency = 1

    def get_citing_works_batch(self, refs):  # type: ignore[override]
        self.calls.append([r.identifier for r in refs])
        return {r.identifier: self._batch_outcome[r.identifier] for r in refs}


class _ExplodingBackend(OpenCiteBackend):
    """Backend that fails the test loudly if any anchor reaches it."""

    def __init__(self) -> None:
        self._config = None  # type: ignore[assignment]
        self._max_results_per_doi = 100
        self._concurrency = 1

    def get_citing_works_batch(self, refs):  # type: ignore[override]
        raise AssertionError(
            f"backend must not be called; received {[r.identifier for r in refs]}"
        )


class _StubSource:
    def __init__(self, outcome):
        self._outcome = outcome

    def get_doi_references(self, dataset_id):  # noqa: ARG002
        return self._outcome


class _RichStubSource(_StubSource):
    """`_StubSource` that also exposes the schema-v2.1 rich-metadata capability."""

    def __init__(self, outcome, metadata: NemarDatasetMetadata):
        super().__init__(outcome)
        self._metadata = metadata

    def get_dataset_metadata(self, dataset_id):  # noqa: ARG002
        return self._metadata


def _context_anchors(out: dict) -> list[dict]:
    """The kept=False subset of metadata.anchors[] (the old context_anchors)."""
    return [a for a in out["metadata"]["anchors"] if not a["kept"]]


def _write_sidecar(
    judgments_dir: Path,
    dataset_id: str,
    judgments: list[dict],
    *,
    model: str = "gemma4:31b",
) -> Path:
    """Write a sidecar JSON in the locked phase 2 shape."""
    judgments_dir.mkdir(parents=True, exist_ok=True)
    path = judgments_dir / f"{dataset_id}.json"
    payload = {
        "dataset_id": dataset_id,
        "judged_at": "2026-05-22T00:00:00Z",
        "judgment_model": model,
        "judgments": judgments,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _judgment(
    identifier: str,
    classification: str,
    *,
    identifier_type: str = "doi",
    source_relation: str = "IsDerivedFrom",
    reason: str = "stub reason",
    paper_title: str | None = "stub title",
    error: str | None = None,
) -> dict:
    return {
        "anchor_identifier": identifier,
        "anchor_identifier_type": identifier_type,
        "source_relation": source_relation,
        "classification": classification,
        "reason": reason,
        "paper_title": paper_title,
        "paper_year": 2024,
        "paper_venue": "Journal of Stubs",
        "judged_at": "2026-05-22T00:00:00Z",
        "error": error,
    }


class JudgmentLookupTests(TestCase):
    """Direct tests for the read-side sidecar helper."""

    def test_missing_sidecar_returns_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            judgments_dir = Path(tmp)
            sidecar = load_judgment_sidecar("nm000999", judgments_dir=judgments_dir)
            self.assertFalse(sidecar.present)
            self.assertEqual(sidecar.lookup, {})
            # The spec-named helper returns the same empty dict.
            self.assertEqual(
                load_judgment_lookup("nm000999", judgments_dir=judgments_dir),
                {},
            )

    def test_taxonomy_enforced_via_allowed_classifications(self) -> None:
        # If phase 1 adds a new class, this test should still pass: the loader
        # always trusts ALLOWED_CLASSIFICATIONS. Use a literal-bad string so
        # we never accidentally test against a future-valid name.
        bogus = "not_a_real_class"
        self.assertNotIn(bogus, ALLOWED_CLASSIFICATIONS)

        with TemporaryDirectory() as tmp:
            judgments_dir = Path(tmp)
            _write_sidecar(
                judgments_dir,
                "nm000001",
                [
                    _judgment("10.1234/data", "data_paper"),
                    _judgment("10.1234/bad", bogus),
                ],
            )
            sidecar = load_judgment_sidecar("nm000001", judgments_dir=judgments_dir)
            self.assertTrue(sidecar.present)
            self.assertEqual(sidecar.lookup, {"10.1234/data": "data_paper"})

    def test_errored_judgment_dropped(self) -> None:
        with TemporaryDirectory() as tmp:
            judgments_dir = Path(tmp)
            _write_sidecar(
                judgments_dir,
                "nm000002",
                [
                    _judgment(
                        "10.1234/timeout",
                        "data_paper",
                        error="ollama timed out",
                    ),
                    _judgment("10.1234/ok", "umbrella"),
                ],
            )
            sidecar = load_judgment_sidecar("nm000002", judgments_dir=judgments_dir)
            self.assertEqual(sidecar.lookup, {"10.1234/ok": "umbrella"})

    def test_canonical_anchor_key_doi_normalization(self) -> None:
        # The pipeline uses canonical_anchor_key to bridge DoiReference and
        # the sidecar; make sure the normalization rules round-trip.
        self.assertEqual(
            canonical_anchor_key("https://doi.org/10.1234/Abc", "doi"),
            "10.1234/abc",
        )
        self.assertEqual(canonical_anchor_key("pmid:12345", "pmid"), "pmid:12345")
        self.assertEqual(canonical_anchor_key("12345", "pmid"), "pmid:12345")


class PipelineBucketingTests(TestCase):
    """End-to-end pipeline tests with on-disk sidecars."""

    def setUp(self) -> None:
        self._tmp_ctx = TemporaryDirectory()
        self.judgments_dir = Path(self._tmp_ctx.name)

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def test_data_paper_anchor_alone_is_fetched(self) -> None:
        """Anchors classified `data_paper` reach the backend; others don't."""
        data_paper_ref = DoiReference(
            identifier="10.1038/data.paper",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        umbrella_ref = DoiReference(
            identifier="10.1038/hbn.umbrella",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([data_paper_ref, umbrella_ref]))
        backend = _StubBackend(
            {
                data_paper_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "Cites the data paper",
                            doi="10.5/cites",
                            source_doi=data_paper_ref.identifier,
                        )
                    ]
                )
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000010",
            [
                _judgment(data_paper_ref.identifier, "data_paper"),
                _judgment(
                    umbrella_ref.identifier,
                    "umbrella",
                    paper_title="HBN umbrella paper",
                    reason="describes broader initiative",
                ),
            ],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000010",
            backend=backend,
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        # Only the data_paper anchor reached the backend.
        self.assertEqual(backend.calls, [[data_paper_ref.identifier]])
        self.assertEqual(out["num_citations"], 1)
        self.assertEqual(out["metadata"]["anchor_count"], 1)
        self.assertEqual(out["metadata"]["fetch_status"], "success")
        self.assertEqual(out["metadata"]["anchor_judgment_model"], "gemma4:31b")
        # anchors[] is the full superset: both anchors, with kept flags.
        anchors = out["metadata"]["anchors"]
        self.assertEqual(len(anchors), 2)
        kept = {a["identifier"]: a for a in anchors if a["kept"]}
        self.assertEqual(set(kept), {data_paper_ref.identifier})
        self.assertEqual(
            kept[data_paper_ref.identifier]["classification"], "data_paper"
        )
        # context_details is populated for data_paper too, so the kept anchor
        # carries its own paper title (default "stub title" from _judgment()).
        self.assertEqual(kept[data_paper_ref.identifier]["paper_title"], "stub title")
        # searched_dois is the flat list of the fetched DOI anchor(s).
        self.assertEqual(out["metadata"]["searched_dois"], [data_paper_ref.identifier])
        # The context subset (kept=False) is the umbrella anchor.
        context = _context_anchors(out)
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["classification"], "umbrella")
        self.assertEqual(context[0]["identifier"], umbrella_ref.identifier)
        self.assertEqual(context[0]["paper_title"], "HBN umbrella paper")
        self.assertEqual(context[0]["source_relation"], "IsDerivedFrom")
        # paper_year + paper_venue forwarded from the sidecar so consumers can
        # render anchors without re-opening it. _judgment() defaults these to
        # 2024 / Journal of Stubs. judgment_model is stamped per anchor too.
        self.assertEqual(context[0]["paper_year"], 2024)
        self.assertEqual(context[0]["paper_venue"], "Journal of Stubs")
        self.assertEqual(context[0]["judgment_model"], "gemma4:31b")
        # _StubSource has no get_dataset_metadata -> empty rich-metadata keys.
        self.assertEqual(out["metadata"]["keywords"], [])
        self.assertIsNone(out["metadata"]["methods_description"])
        self.assertEqual(out["metadata"]["funding"], [])

    def test_no_sidecar_falls_back_to_fetch_all(self) -> None:
        """Without a sidecar, all anchors get fetched (legacy behavior)."""
        ref_a = DoiReference(
            identifier="10.1234/a",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        ref_b = DoiReference(
            identifier="10.1234/b",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([ref_a, ref_b]))
        backend = _StubBackend(
            {
                ref_a.identifier: FetchSuccess(
                    [_make_work("W1", doi="10.5/w1", source_doi=ref_a.identifier)]
                ),
                ref_b.identifier: FetchSuccess(
                    [_make_work("W2", doi="10.5/w2", source_doi=ref_b.identifier)]
                ),
            }
        )
        with self.assertLogs(
            "dataset_citations.core.opencite_pipeline", level="INFO"
        ) as logs:
            out = fetch_dataset_citations_via_opencite(
                "nm000011",
                backend=backend,
                nemar_source=nemar,
                fetch_date=WHEN,
                judgments_dir=self.judgments_dir,  # empty tempdir
            )
        # Single INFO log for the fallback path.
        fallback_logs = [r for r in logs.records if "sidecar missing" in r.getMessage()]
        self.assertEqual(len(fallback_logs), 1)
        # Both anchors went to the backend; both citations are present.
        self.assertEqual(backend.calls, [[ref_a.identifier, ref_b.identifier]])
        self.assertEqual(out["num_citations"], 2)
        self.assertEqual(out["metadata"]["anchor_count"], 2)
        self.assertIsNone(out["metadata"]["anchor_judgment_model"])
        # No sidecar -> every anchor is kept, with a null classification and
        # null judgment_model; nothing is bucketed to context.
        anchors = out["metadata"]["anchors"]
        self.assertEqual(len(anchors), 2)
        self.assertTrue(all(a["kept"] for a in anchors))
        self.assertTrue(all(a["classification"] is None for a in anchors))
        self.assertTrue(all(a["judgment_model"] is None for a in anchors))
        self.assertEqual(_context_anchors(out), [])
        self.assertEqual(
            out["metadata"]["searched_dois"], [ref_a.identifier, ref_b.identifier]
        )

    def test_out_of_taxonomy_entry_dropped_with_warning(self) -> None:
        """One bad entry doesn't sink the rest of the sidecar."""
        data_paper_ref = DoiReference(
            identifier="10.1234/good-data",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        umbrella_ref = DoiReference(
            identifier="10.1234/umbrella",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        broken_ref = DoiReference(
            identifier="10.1234/broken",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([data_paper_ref, umbrella_ref, broken_ref]))
        backend = _StubBackend(
            {
                data_paper_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "good",
                            doi="10.5/good",
                            source_doi=data_paper_ref.identifier,
                        )
                    ]
                ),
                # broken_ref will fall through to legacy fetch because it's
                # dropped from the lookup; backend must answer it.
                broken_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "broken-fallback",
                            doi="10.5/broken",
                            source_doi=broken_ref.identifier,
                        )
                    ]
                ),
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000012",
            [
                _judgment(data_paper_ref.identifier, "data_paper"),
                _judgment(umbrella_ref.identifier, "umbrella"),
                _judgment(broken_ref.identifier, "garbage_label"),
            ],
        )
        with self.assertLogs(
            "dataset_citations.quality.anchor_judgment_io",
            level=logging.WARNING,
        ) as logs:
            out = fetch_dataset_citations_via_opencite(
                "nm000012",
                backend=backend,
                nemar_source=nemar,
                fetch_date=WHEN,
                judgments_dir=self.judgments_dir,
            )
        self.assertTrue(any("out-of-taxonomy" in r.getMessage() for r in logs.records))
        # Data paper + dropped-fallback both fetch; umbrella becomes context.
        self.assertEqual(
            sorted(backend.calls[0]),
            sorted([data_paper_ref.identifier, broken_ref.identifier]),
        )
        self.assertEqual(out["num_citations"], 2)
        # umbrella is the only context (kept=False); the dropped garbage_label
        # anchor fell through to fetch (kept=True, classification None).
        classifications = {c["classification"] for c in _context_anchors(out)}
        self.assertEqual(classifications, {"umbrella"})
        broken = next(
            a
            for a in out["metadata"]["anchors"]
            if a["identifier"] == broken_ref.identifier
        )
        self.assertTrue(broken["kept"])
        self.assertIsNone(broken["classification"])

    def test_all_anchors_non_data_paper_zero_citations(self) -> None:
        """Every anchor classified as non-data_paper -> backend never called."""
        refs = [
            DoiReference(
                identifier=f"10.1234/{label}",
                identifier_type="doi",
                relation_type="IsDerivedFrom",
                source="nemar_metadata",
            )
            for label in ("umbrella", "method", "related", "junk")
        ]
        nemar = _StubSource(FetchSuccess(refs))
        _write_sidecar(
            self.judgments_dir,
            "nm000013",
            [
                _judgment(refs[0].identifier, "umbrella", paper_title="Umbrella"),
                _judgment(
                    refs[1].identifier,
                    "methodology",
                    paper_title="MNE-Python",
                ),
                _judgment(
                    refs[2].identifier,
                    "related_work",
                    paper_title="Related",
                ),
                _judgment(refs[3].identifier, "irrelevant", paper_title="Junk"),
            ],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000013",
            backend=_ExplodingBackend(),
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        self.assertEqual(out["num_citations"], 0)
        self.assertEqual(out["metadata"]["fetch_status"], "no_data_paper_anchor")
        self.assertEqual(out["metadata"]["anchor_count"], 4)
        # All four anchors are present, none kept (none reached the backend).
        self.assertEqual(len(out["metadata"]["anchors"]), 4)
        self.assertEqual(len(_context_anchors(out)), 4)
        self.assertEqual(out["metadata"]["searched_dois"], [])
        # The model name is still surfaced on the stub payload.
        self.assertEqual(out["metadata"]["anchor_judgment_model"], "gemma4:31b")

    def test_catalog_doi_anchor_respects_judgment(self) -> None:
        """A catalog DOI that's classified as umbrella should NOT fetch."""
        source_ref = DoiReference(
            identifier="10.1038/source-paper",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        catalog_doi = "10.82901/nemar.nm000777"
        nemar = _StubSource(FetchSuccess([source_ref]))
        backend = _StubBackend(
            {
                source_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "source paper citation",
                            doi="10.5/source",
                            source_doi=source_ref.identifier,
                        )
                    ]
                ),
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000014",
            [
                _judgment(source_ref.identifier, "data_paper"),
                _judgment(
                    catalog_doi,
                    "umbrella",
                    source_relation="References",
                    paper_title="catalog ref classified as umbrella",
                ),
            ],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000014",
            backend=backend,
            nemar_source=nemar,
            catalog_doi=catalog_doi,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        # Only the source_ref reaches the backend.
        self.assertEqual(backend.calls, [[source_ref.identifier]])
        self.assertEqual(out["metadata"]["anchor_count"], 1)
        catalog_records = [
            a for a in out["metadata"]["anchors"] if a["identifier"] == catalog_doi
        ]
        self.assertEqual(len(catalog_records), 1)
        self.assertEqual(catalog_records[0]["classification"], "umbrella")
        self.assertFalse(catalog_records[0]["kept"])

    def test_partial_sidecar_warns_per_dataset(self) -> None:
        """When the sidecar covers some but not all anchors, the uncovered
        anchors fall through to fetch AND a single per-dataset WARN logs
        the gap so operators see the drift."""
        judged_ref = DoiReference(
            identifier="10.1038/judged-paper",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        unjudged_ref = DoiReference(
            identifier="10.1038/unjudged-paper",
            identifier_type="doi",
            relation_type="References",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([judged_ref, unjudged_ref]))
        backend = _StubBackend(
            {
                judged_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "Cites judged",
                            doi="10.5/cj",
                            source_doi=judged_ref.identifier,
                        )
                    ]
                ),
                unjudged_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "Cites unjudged",
                            doi="10.5/cu",
                            source_doi=unjudged_ref.identifier,
                        )
                    ]
                ),
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000015",
            [_judgment(judged_ref.identifier, "data_paper")],
        )
        with self.assertLogs(
            "dataset_citations.core.opencite_pipeline", level="WARNING"
        ) as logs:
            out = fetch_dataset_citations_via_opencite(
                "nm000015",
                backend=backend,
                nemar_source=nemar,
                fetch_date=WHEN,
                judgments_dir=self.judgments_dir,
            )
        # Both anchors went to the backend (the judged one explicitly,
        # the unjudged one as fallback).
        self.assertEqual(
            sorted(backend.calls[0]),
            sorted([judged_ref.identifier, unjudged_ref.identifier]),
        )
        # Exactly one WARN per dataset, naming the gap count.
        warns = [
            r
            for r in logs.records
            if "have no judgment in the sidecar" in r.getMessage()
        ]
        self.assertEqual(len(warns), 1)
        self.assertIn("1/2 anchors", warns[0].getMessage())
        # Nothing bucketed to context: everything was fetched (both kept).
        self.assertEqual(_context_anchors(out), [])
        self.assertEqual(
            sorted(out["metadata"]["searched_dois"]),
            sorted([judged_ref.identifier, unjudged_ref.identifier]),
        )

    def test_rich_metadata_capability_lands_in_metadata(self) -> None:
        """A source exposing get_dataset_metadata populates the v2.1 keys."""
        data_paper_ref = DoiReference(
            identifier="10.1038/data.paper",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        metadata = NemarDatasetMetadata(
            keywords=("EEG", "BIDS"),
            methods_description="collected during cognitive tasks",
            funding=({"funder_name": "NIH", "award_number": "R01MH1"},),
        )
        nemar = _RichStubSource(FetchSuccess([data_paper_ref]), metadata)
        backend = _StubBackend(
            {
                data_paper_ref.identifier: FetchSuccess(
                    [
                        _make_work(
                            "cites",
                            doi="10.5/c",
                            source_doi=data_paper_ref.identifier,
                        )
                    ]
                )
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000016",
            [_judgment(data_paper_ref.identifier, "data_paper")],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000016",
            backend=backend,
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        self.assertEqual(out["metadata"]["keywords"], ["EEG", "BIDS"])
        self.assertEqual(
            out["metadata"]["methods_description"], "collected during cognitive tasks"
        )
        self.assertEqual(
            out["metadata"]["funding"],
            [{"funder_name": "NIH", "award_number": "R01MH1"}],
        )

    def test_rich_metadata_present_even_with_no_doi_references(self) -> None:
        """A DOI-less dataset still carries its rich metadata (parsed before
        the no_doi_references early-out)."""
        metadata = NemarDatasetMetadata(keywords=("MEG",), methods_description=None)
        nemar = _RichStubSource(FetchSuccess([]), metadata)
        out = fetch_dataset_citations_via_opencite(
            "nm000017",
            backend=_ExplodingBackend(),
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        self.assertEqual(out["metadata"]["fetch_status"], "no_doi_references")
        self.assertEqual(out["metadata"]["keywords"], ["MEG"])
        self.assertEqual(out["metadata"]["anchors"], [])
        self.assertEqual(out["metadata"]["searched_dois"], [])

    def test_no_data_paper_stub_carries_rich_metadata(self) -> None:
        """The no_data_paper_anchor stub still emits the dataset's rich metadata."""
        umbrella_ref = DoiReference(
            identifier="10.1/umbrella",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        metadata = NemarDatasetMetadata(
            keywords=("EEG",),
            methods_description="collected during tasks",
            funding=({"funder_name": "NIH"},),
        )
        nemar = _RichStubSource(FetchSuccess([umbrella_ref]), metadata)
        _write_sidecar(
            self.judgments_dir,
            "nm000018",
            [_judgment(umbrella_ref.identifier, "umbrella")],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000018",
            backend=_ExplodingBackend(),
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        self.assertEqual(out["metadata"]["fetch_status"], "no_data_paper_anchor")
        self.assertEqual(out["metadata"]["keywords"], ["EEG"])
        self.assertEqual(
            out["metadata"]["methods_description"], "collected during tasks"
        )
        self.assertEqual(out["metadata"]["funding"], [{"funder_name": "NIH"}])
        self.assertEqual(out["metadata"]["searched_dois"], [])
        self.assertEqual(len(_context_anchors(out)), 1)

    def test_pmid_kept_anchor_excluded_from_searched_dois(self) -> None:
        """A kept PMID anchor appears in anchors[] but not in searched_dois
        (which is DOI-only)."""
        pmid_ref = DoiReference(
            identifier="pmid:12345",
            identifier_type="pmid",
            relation_type="References",
            source="nemar_metadata",
        )
        doi_ref = DoiReference(
            identifier="10.1/d",
            identifier_type="doi",
            relation_type="IsDerivedFrom",
            source="nemar_metadata",
        )
        nemar = _StubSource(FetchSuccess([pmid_ref, doi_ref]))
        backend = _StubBackend(
            {
                pmid_ref.identifier: FetchSuccess(
                    [_make_work("p", doi="10.5/p", source_doi=pmid_ref.identifier)]
                ),
                doi_ref.identifier: FetchSuccess(
                    [_make_work("d", doi="10.5/d", source_doi=doi_ref.identifier)]
                ),
            }
        )
        _write_sidecar(
            self.judgments_dir,
            "nm000019",
            [
                _judgment(pmid_ref.identifier, "data_paper", identifier_type="pmid"),
                _judgment(doi_ref.identifier, "data_paper"),
            ],
        )
        out = fetch_dataset_citations_via_opencite(
            "nm000019",
            backend=backend,
            nemar_source=nemar,
            fetch_date=WHEN,
            judgments_dir=self.judgments_dir,
        )
        kept = {a["identifier"] for a in out["metadata"]["anchors"] if a["kept"]}
        self.assertEqual(kept, {pmid_ref.identifier, doi_ref.identifier})
        # searched_dois is DOI-only: the kept PMID anchor is excluded.
        self.assertEqual(out["metadata"]["searched_dois"], [doi_ref.identifier])


class SidecarShapeRegressionTests(TestCase):
    """Pin the schema contract phase 4 will consume."""

    def test_judgment_sidecar_is_frozen_dataclass(self) -> None:
        # If phase 4 starts mutating sidecar.lookup, this test fails loudly.
        sidecar = JudgmentSidecar(present=True, model="m", lookup={"a": "b"})
        with self.assertRaises(Exception):
            sidecar.lookup = {}  # type: ignore[misc]
