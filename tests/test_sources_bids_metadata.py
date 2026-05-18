"""Tests for bids_metadata parsing.

Loads real dataset_description.json snapshots from
tests/test_data/sources/bids/ and runs them through the pure
parse_bids_description function. No mocks, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase

from dataset_citations.sources.bids_metadata import parse_bids_description

FIXTURE_DIR = Path(__file__).parent / "test_data" / "sources" / "bids"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


class ParseDs000117(TestCase):
    """ds000117 has DatasetDOI, HowToAcknowledge with a PubMed link, and
    ReferencesAndLinks with a DOI URL."""

    def setUp(self) -> None:
        self.payload = load_fixture("ds000117.description.json")
        self.refs = parse_bids_description(self.payload)

    def test_emits_at_least_one_doi_or_pmid(self) -> None:
        self.assertGreater(len(self.refs), 0)

    def test_openneuro_dataset_doi_dropped(self) -> None:
        # ds000117's DatasetDOI is 10.18112/openneuro.ds000117.* — not indexed
        # in OpenAlex, must not appear in the output.
        identifiers = {r.identifier for r in self.refs}
        for ident in identifiers:
            self.assertFalse(
                ident.startswith("10.18112/openneuro."),
                f"OpenNeuro DatasetDOI {ident} should be excluded",
            )

    def test_pmid_extracted_from_howtoacknowledge(self) -> None:
        # ds000117 references pmid:25977808 in both HowToAcknowledge and
        # ReferencesAndLinks, so we expect the PMID to surface twice with
        # different relation tags. The HowToAcknowledge -> IsDerivedFrom
        # mapping must show up at least once.
        pmid_refs = [
            r
            for r in self.refs
            if r.identifier_type == "pmid" and r.identifier == "pmid:25977808"
        ]
        self.assertGreater(len(pmid_refs), 0)
        howto_refs = [r for r in pmid_refs if r.source_field == "HowToAcknowledge"]
        self.assertEqual(len(howto_refs), 1)
        self.assertEqual(howto_refs[0].relation_type, "IsDerivedFrom")

    def test_source_is_openneuro_description(self) -> None:
        for ref in self.refs:
            self.assertEqual(ref.source, "openneuro_description")


class ParseDs002001(TestCase):
    """ds002001 has only DatasetDOI (OpenNeuro) — the output should be empty
    once we strip OpenNeuro DOIs that aren't indexed in OpenAlex."""

    def setUp(self) -> None:
        self.payload = load_fixture("ds002001.description.json")
        self.refs = parse_bids_description(self.payload)

    def test_no_extractable_references(self) -> None:
        self.assertEqual(self.refs, [])


class ParseSyntheticEdgeCases(TestCase):
    def test_dataset_doi_inferred_as_isidenticalto(self) -> None:
        # Non-OpenNeuro DatasetDOI: should be kept as IsIdenticalTo.
        refs = parse_bids_description(
            {
                "DatasetDOI": "doi:10.5281/zenodo.1234567",
            }
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].relation_type, "IsIdenticalTo")
        self.assertEqual(refs[0].source_field, "DatasetDOI")

    def test_referencesandlinks_inferred_as_references(self) -> None:
        refs = parse_bids_description(
            {
                "ReferencesAndLinks": [
                    "https://doi.org/10.1038/sdata.2015.1",
                    "https://example.com/no-doi-here",
                ],
            }
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].identifier, "10.1038/sdata.2015.1")
        self.assertEqual(refs[0].relation_type, "References")
        self.assertEqual(refs[0].source_field, "ReferencesAndLinks")

    def test_deduplicates_across_fields_within_same_relation(self) -> None:
        # Same DOI showing up in multiple ReferencesAndLinks entries should
        # only emit one DoiReference for that (identifier, relation) pair.
        refs = parse_bids_description(
            {
                "ReferencesAndLinks": [
                    "10.1038/sdata.2015.1",
                    "doi:10.1038/sdata.2015.1",
                ],
            }
        )
        self.assertEqual(len(refs), 1)

    def test_pmid_in_referencesandlinks(self) -> None:
        refs = parse_bids_description(
            {
                "ReferencesAndLinks": [
                    "https://www.ncbi.nlm.nih.gov/pubmed/25977808",
                ],
            }
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].identifier, "pmid:25977808")
        self.assertEqual(refs[0].relation_type, "References")

    def test_empty_description(self) -> None:
        self.assertEqual(parse_bids_description({}), [])

    def test_recurses_into_dict_valued_field(self) -> None:
        # Some BIDS authors put structured content in HowToAcknowledge.
        refs = parse_bids_description(
            {
                "HowToAcknowledge": {
                    "text": "Please cite this paper",
                    "citation": "https://doi.org/10.1038/sdata.2015.1",
                },
            }
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].identifier, "10.1038/sdata.2015.1")
        self.assertEqual(refs[0].relation_type, "IsDerivedFrom")
