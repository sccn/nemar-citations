"""Tests for the GitHub-org routing in quality.dataset_metadata.

The retrieve-metadata pipeline was hardcoded to OpenNeuroDatasets/. nm-*
and on-* datasets live in nemarDatasets/; sending them to the wrong org
yielded 404s on every call and, combined with PyGithub's missing
timeout, multi-hour CLOSE_WAIT stalls in the cron pipeline.

Pure helper test, no network.
"""

from __future__ import annotations

from unittest import TestCase

from dataset_citations.quality.dataset_metadata import _org_for_dataset


class OrgForDatasetTests(TestCase):
    def test_ds_prefix_routes_to_openneurodatasets(self) -> None:
        # Legacy OpenNeuro tree.
        for did in ("ds000117", "ds002885", "ds007788"):
            self.assertEqual(_org_for_dataset(did), "OpenNeuroDatasets", did)

    def test_nm_prefix_routes_to_nemardatasets(self) -> None:
        # NEMAR-native datasets are in nemarDatasets, not OpenNeuroDatasets.
        for did in ("nm000103", "nm000115", "nm000999"):
            self.assertEqual(_org_for_dataset(did), "nemarDatasets", did)

    def test_on_prefix_routes_to_nemardatasets(self) -> None:
        # OpenNeuro datasets imported into NEMAR keep the on-* id and the
        # repo lives under nemarDatasets/, not OpenNeuroDatasets/.
        for did in ("on005261", "on007315"):
            self.assertEqual(_org_for_dataset(did), "nemarDatasets", did)

    def test_unrecognized_prefix_falls_through_to_openneuro(self) -> None:
        # Defensive default. xx-* datasets aren't a real prefix today, but
        # keep the legacy behaviour for unknown prefixes so this helper
        # doesn't silently route to a wrong NEMAR repo.
        self.assertEqual(_org_for_dataset("xx12345"), "OpenNeuroDatasets")

    def test_partial_word_match_does_not_misroute(self) -> None:
        # Tighter than startswith("nm"): the prefix must be followed by a
        # digit. Future ids like 'online-study-x' or 'nmr-phantom' must
        # NOT silently route to nemarDatasets/.
        for did in ("online-study-x", "nmr-phantom", "nm-no-digits"):
            self.assertEqual(
                _org_for_dataset(did),
                "OpenNeuroDatasets",
                f"{did!r} should not route to nemarDatasets",
            )

    def test_uppercase_prefix_normalized(self) -> None:
        # Case-insensitive on the prefix. NEMAR's canonical ids are
        # lowercase, but the helper should not silently misroute if a
        # stray uppercase id ever flows through.
        self.assertEqual(_org_for_dataset("NM000103"), "nemarDatasets")
        self.assertEqual(_org_for_dataset("ON005261"), "nemarDatasets")
        self.assertEqual(_org_for_dataset("DS000117"), "OpenNeuroDatasets")
