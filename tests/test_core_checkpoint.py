"""Tests for the per-anchor opencite checkpoint store.

Real filesystem, no mocks. Each test gets a fresh temp dir and cleans up.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest import TestCase

from dataset_citations.core.checkpoint import (
    AnchorOutcome,
    Checkpoint,
    CheckpointStore,
    reason_for_status,
)
from dataset_citations.sources.models import (
    Author,
    CitingWork,
    FetchError,
    FetchSuccess,
    RelationType,
)


def _make_work(
    *,
    title: str = "Test paper",
    doi: str | None = "10.1038/test.1",
    source_doi: str = "10.1038/anchor.1",
    source_relation: RelationType = "References",
) -> CitingWork:
    return CitingWork(
        title=title,
        doi=doi,
        pmid=None,
        openalex_id=None,
        year=2024,
        authors=(Author(name="A. Researcher"),),
        venue="Test Journal",
        abstract="…",
        citation_count=5,
        source_doi=source_doi,
        source_relation=source_relation,
    )


class StoreRoundTrip(TestCase):
    def setUp(self) -> None:
        self.tmp = Path(__file__).parent / "test_data" / "_tmp_checkpoint"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.store = CheckpointStore(base_dir=self.tmp)

    def tearDown(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_load_missing_returns_empty(self) -> None:
        loaded = self.store.load("nm000001")
        self.assertEqual(loaded.dataset_id, "nm000001")
        self.assertEqual(loaded.anchors, {})

    def test_record_anchor_success_roundtrip(self) -> None:
        work = _make_work()
        self.store.record_anchor(
            "nm000001",
            "10.1038/anchor.1",
            FetchSuccess([work]),
        )
        loaded = self.store.load("nm000001")
        self.assertTrue(loaded.is_success("10.1038/anchor.1"))
        works = loaded.successful_works("10.1038/anchor.1")
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0], work)

    def test_isdescribedby_relation_roundtrips(self) -> None:
        # IsDescribedBy (the data-paper relation, #181) must survive
        # _validate_relation on load, not be dropped as an unknown relation.
        work = _make_work(source_relation="IsDescribedBy")
        self.store.record_anchor("nm000001", "10.1038/anchor.1", FetchSuccess([work]))
        loaded = self.store.load("nm000001")
        works = loaded.successful_works("10.1038/anchor.1")
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0].source_relation, "IsDescribedBy")

    def test_record_anchor_error_marks_non_success(self) -> None:
        self.store.record_anchor(
            "nm000001",
            "10.1038/anchor.1",
            FetchError("rate_limit", "S2 throttled"),
        )
        loaded = self.store.load("nm000001")
        self.assertFalse(loaded.is_success("10.1038/anchor.1"))
        self.assertEqual(loaded.successful_works("10.1038/anchor.1"), [])
        self.assertEqual(loaded.anchors["10.1038/anchor.1"].status, "rate_limit")

    def test_multiple_anchors_persist_independently(self) -> None:
        work_a = _make_work(title="A", source_doi="10.x/a")
        work_b = _make_work(title="B", source_doi="10.x/b")
        self.store.record_anchor("nm0", "10.x/a", FetchSuccess([work_a]))
        self.store.record_anchor("nm0", "10.x/b", FetchSuccess([work_b]))
        loaded = self.store.load("nm0")
        self.assertEqual(set(loaded.anchors.keys()), {"10.x/a", "10.x/b"})
        self.assertEqual(loaded.successful_works("10.x/a")[0].title, "A")
        self.assertEqual(loaded.successful_works("10.x/b")[0].title, "B")

    def test_clear_removes_file(self) -> None:
        self.store.record_anchor("nm000001", "10.x/a", FetchSuccess([_make_work()]))
        self.assertTrue(self.store.path_for("nm000001").exists())
        self.store.clear("nm000001")
        self.assertFalse(self.store.path_for("nm000001").exists())

    def test_unreadable_file_treated_as_empty(self) -> None:
        path = self.store.path_for("nm000001")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json")
        loaded = self.store.load("nm000001")
        self.assertEqual(loaded.anchors, {})

    def test_malformed_work_in_checkpoint_skipped(self) -> None:
        # Hand-craft a payload that mixes a valid and a malformed work.
        path = self.store.path_for("nm000001")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"dataset_id":"nm000001","schema_version":"1.0","anchors":{'
            '"10.x/a":{"status":"success","fetched_at":"t","works":['
            '{"title":"good","doi":null,"pmid":null,"openalex_id":null,'
            '"year":2024,"authors":[],"venue":null,"abstract":null,'
            '"citation_count":null,"source_doi":"10.x/a",'
            '"source_relation":"References"},'
            '{"title":"bad","source_doi":"10.x/a","source_relation":"NotAllowed"}]}'
            "}}"
        )
        loaded = self.store.load("nm000001")
        works = loaded.successful_works("10.x/a")
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0].title, "good")


class CheckpointOps(TestCase):
    def test_is_success_for_nonexistent_anchor_false(self) -> None:
        cp = Checkpoint(dataset_id="x")
        self.assertFalse(cp.is_success("anything"))
        self.assertEqual(cp.successful_works("anything"), [])

    def test_outcome_default_fields(self) -> None:
        outcome = AnchorOutcome(status="success")
        self.assertEqual(outcome.works, [])
        self.assertEqual(outcome.fetched_at, "")


class ReasonForStatus(TestCase):
    def test_success_maps_to_none(self) -> None:
        self.assertIsNone(reason_for_status("success"))

    def test_known_reasons_pass_through(self) -> None:
        for r in ("not_found", "auth", "network", "parse", "rate_limit", "other"):
            self.assertEqual(reason_for_status(r), r)

    def test_unknown_status_maps_to_other(self) -> None:
        self.assertEqual(reason_for_status("weird"), "other")
