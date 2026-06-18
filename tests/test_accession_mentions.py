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


def _mention(doi: str | None, accession: str = "ds002718") -> dict:
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
        meta = merged["metadata"]
        self.assertEqual(meta["num_accession_mentions"], 1)
        # 1 References anchor (data paper) + 1 accession mention (dataset).
        self.assertEqual(meta["num_dataset_citations"], 1)
        self.assertEqual(meta["num_datapaper_citations"], 1)
        self.assertEqual(meta["searched_accessions"], ["ds002718"])

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

    def test_dedupes_on_openalex_id_when_doi_set_differs(self) -> None:
        # Anchor carries only a DOI; the mention copy of the SAME paper carries
        # only an OpenAlex id plus a (different) DOI. They must still dedup via
        # the shared OpenAlex id rather than double-count.
        anchor = _anchor("10.1/paper", "References")
        anchor["openalex_id"] = "W123"
        anchor["doi"] = None  # anchor has no DOI here, only the OpenAlex id
        mention = _mention("10.1/paper")
        mention["openalex_id"] = "W123"
        mention["doi"] = None
        merged = merge_accession_mentions(_base([anchor]), [mention], ["ds002718"])
        self.assertEqual(merged["num_citations"], 1)
        self.assertTrue(merged["citation_details"][0]["mentions_accession"])

    def test_dedupes_cross_identifier_doi_vs_openalex(self) -> None:
        # Anchor matched by DOI only; mention matched by OpenAlex id only; same
        # paper -> one entry.
        anchor = _anchor("10.1/paper", "References")
        anchor["openalex_id"] = "W999"
        mention = _mention(None)  # no DOI on the mention
        mention["openalex_id"] = "W999"
        merged = merge_accession_mentions(_base([anchor]), [mention], ["ds002718"])
        self.assertEqual(merged["num_citations"], 1)
        self.assertTrue(merged["citation_details"][0]["mentions_accession"])

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

    def test_existing_entry_with_no_identifier_is_left_alone(self) -> None:
        # A legacy entry with no doi/openalex_id/title can't be deduped against;
        # a real mention is still appended (no phantom, no corruption).
        empty = {"venue": "n/a", "source_relation": "References"}
        cj = _base([empty])
        merged = merge_accession_mentions(cj, [_mention("10.2/new")], ["ds002718"])
        self.assertEqual(merged["num_citations"], 2)

    def test_mention_with_no_identifier_is_dropped(self) -> None:
        cj = _base([_anchor("10.1/anchor")])
        empty_mention = {"discovery_method": "accession_mention", "venue": "n/a"}
        merged = merge_accession_mentions(cj, [empty_mention], ["ds002718"])
        self.assertEqual(merged["num_citations"], 1)  # nothing to dedup/display by
