"""Tests for accession-mention merge + bucket logic (pure, no network). Issue #169."""

from __future__ import annotations

import copy
from unittest import TestCase

from dataset_citations.core.accession_mentions import (
    cites_dataset,
    merge_accession_mentions,
)


def _anchor(doi: str, relation: str = "References") -> dict:
    return {
        "title": f"Anchor {doi}",
        "doi": doi,
        "openalex_id": None,
        "source_doi": "10.0/anchor",
        "source_relation": relation,
        "discovery_backend": "opencite",
    }


def _mention(doi: str, accession: str = "ds002718") -> dict:
    return {
        "title": f"Mention {doi}",
        "doi": doi,
        "openalex_id": None,
        "source_doi": None,
        "source_relation": None,
        "discovery_backend": "openalex",
        "discovery_method": "accession_mention",
        "matched_accession": accession,
    }


def _base(details: list[dict]) -> dict:
    return {
        "dataset_id": "ds002718",
        "num_citations": len(details),
        "date_last_updated": "2026-06-18T00:00:00+00:00",
        "metadata": {"fetch_status": "success"},
        "citation_details": list(details),
    }


class CitesDatasetBucketTests(TestCase):
    def test_accession_mention_is_dataset(self) -> None:
        self.assertTrue(cites_dataset(_mention("10.1/a")))

    def test_isversionof_anchor_is_dataset(self) -> None:
        self.assertTrue(cites_dataset(_anchor("10.1/a", "IsVersionOf")))

    def test_isidenticalto_anchor_is_dataset(self) -> None:
        self.assertTrue(cites_dataset(_anchor("10.1/a", "IsIdenticalTo")))

    def test_references_anchor_is_data_paper(self) -> None:
        self.assertFalse(cites_dataset(_anchor("10.1/a", "References")))

    def test_isderivedfrom_anchor_is_data_paper(self) -> None:
        self.assertFalse(cites_dataset(_anchor("10.1/a", "IsDerivedFrom")))

    def test_anchor_flagged_with_mention_is_dataset(self) -> None:
        a = _anchor("10.1/a", "References")
        a["mentions_accession"] = True
        self.assertTrue(cites_dataset(a))


class MergeAccessionMentionsTests(TestCase):
    def test_appends_new_mention(self) -> None:
        cj = _base([_anchor("10.1/anchor")])
        merged = merge_accession_mentions(cj, [_mention("10.2/new")], ["ds002718"])
        self.assertEqual(merged["num_citations"], 2)
        dois = {c["doi"] for c in merged["citation_details"]}
        self.assertIn("10.2/new", dois)
        self.assertEqual(merged["metadata"]["num_accession_mentions"], 1)
        self.assertEqual(merged["metadata"]["num_anchor_citations"], 1)
        self.assertEqual(merged["metadata"]["searched_accessions"], ["ds002718"])

    def test_flags_existing_anchor_that_also_mentions(self) -> None:
        cj = _base([_anchor("10.1/both", "References")])
        merged = merge_accession_mentions(cj, [_mention("10.1/both")], ["ds002718"])
        # No new entry; the anchor is flagged so it lands in both buckets.
        self.assertEqual(merged["num_citations"], 1)
        anchor = merged["citation_details"][0]
        self.assertTrue(anchor["mentions_accession"])
        self.assertEqual(anchor["matched_accession"], "ds002718")
        self.assertTrue(cites_dataset(anchor))

    def test_dedupes_by_doi_case_insensitive(self) -> None:
        cj = _base([_anchor("10.1/Anchor")])
        merged = merge_accession_mentions(cj, [_mention("10.1/anchor")], ["ds002718"])
        self.assertEqual(merged["num_citations"], 1)  # same paper, different case

    def test_drops_confidence_scoring_when_new_mention_appended(self) -> None:
        cj = _base([_anchor("10.1/anchor")])
        cj["confidence_scoring"] = {"model_used": "m", "scoring_date": "x"}
        merged = merge_accession_mentions(cj, [_mention("10.2/new")], ["ds002718"])
        # New citation needs scoring; stale block dropped so score re-runs.
        self.assertNotIn("confidence_scoring", merged)

    def test_keeps_confidence_scoring_when_nothing_appended(self) -> None:
        cj = _base([_anchor("10.1/anchor")])
        cj["confidence_scoring"] = {"model_used": "m", "scoring_date": "x"}
        merge_accession_mentions(cj, [], ["ds002718"])
        self.assertIn("confidence_scoring", cj)

    def test_idempotent_on_rerun(self) -> None:
        cj = _base([_anchor("10.1/anchor", "References")])
        mentions = [_mention("10.2/new"), _mention("10.1/anchor")]
        first = merge_accession_mentions(cj, mentions, ["ds002718"])
        snapshot = copy.deepcopy(first)
        # Feed the same mentions back into the already-merged json.
        second = merge_accession_mentions(first, mentions, ["ds002718"])
        self.assertEqual(second, snapshot)
