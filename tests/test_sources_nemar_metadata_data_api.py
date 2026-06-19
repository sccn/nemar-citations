"""Tests for the data.nemar.org fetch path of NemarMetadataSource.

A captured live response from data.nemar.org/nm000104/metadata.json sits in
tests/test_data/sources/nemar/nm000104.data_api.json and exercises the
parse path. Live network tests are gated behind RUN_INTEGRATION_TESTS=1.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import get_args
from unittest import TestCase, skipUnless

from dataset_citations.sources.models import FetchError, FetchSuccess, RelationType
from dataset_citations.sources.nemar_metadata import (
    NemarMetadataSource,
    parse_nemar_metadata,
)

FIXTURE = (
    Path(__file__).parent / "test_data" / "sources" / "nemar" / "nm000104.data_api.json"
)


class ParseDataApiPayload(TestCase):
    """parse_nemar_metadata on a live data.nemar.org payload."""

    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE.read_text())
        self.refs = parse_nemar_metadata(self.payload)

    def test_payload_carries_related_identifiers(self) -> None:
        self.assertIn("related_identifiers", self.payload)
        self.assertGreater(len(self.payload["related_identifiers"]), 0)

    def test_emits_only_doi_refs(self) -> None:
        for ref in self.refs:
            self.assertEqual(ref.identifier_type, "doi")
            self.assertTrue(ref.identifier.startswith("10."))

    def test_relation_types_in_allow_list(self) -> None:
        # Derived from RelationType (now includes IsDescribedBy since #181) so it
        # tracks the source of truth instead of a hand-maintained copy.
        allowed = set(get_args(RelationType))
        for ref in self.refs:
            self.assertIn(ref.relation_type, allowed)

    def test_source_field(self) -> None:
        for ref in self.refs:
            self.assertEqual(ref.source, "nemar_metadata")
            self.assertEqual(ref.source_field, "related_identifiers")


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live data.nemar.org calls; set RUN_INTEGRATION_TESTS=1 to enable",
)
class LiveDataApiFetch(TestCase):
    """Hits data.nemar.org directly. Real network, no mocks."""

    def test_known_nm_id_returns_doi_references(self) -> None:
        source = NemarMetadataSource(prefer_data_api=True)
        result = source.get_doi_references("nm000104")
        self.assertIsInstance(result, FetchSuccess)
        assert isinstance(result, FetchSuccess)
        # nm000104 is well-populated; should yield at least one DOI ref.
        self.assertGreater(len(result.value), 0)

    def test_missing_id_returns_not_found_or_falls_back(self) -> None:
        # An obviously bogus ID. Without GH credentials the fallback also 404s,
        # so we accept FetchError of any reason.
        source = NemarMetadataSource(prefer_data_api=True)
        result = source.get_doi_references("nm999999999")
        self.assertIsInstance(result, FetchError)

    def test_prefer_data_api_skips_github_when_data_api_succeeds(self) -> None:
        # Use a non-existent GH org so any fallback would 404 audibly; the
        # data-api success must short-circuit before the fallback runs.
        source = NemarMetadataSource(prefer_data_api=True)
        result = source.get_doi_references("nm000104", org="not-a-real-org")
        self.assertIsInstance(result, FetchSuccess)
