"""Tests for bids_metadata parsing.

Loads real dataset_description.json snapshots from
tests/test_data/sources/bids/ and runs them through the pure
parse_bids_description function. No mocks, no network.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import ClassVar
from unittest import TestCase

from dataset_citations.sources.bids_metadata import (
    BidsMetadataSource,
    parse_bids_description,
)
from dataset_citations.sources.models import FetchError, FetchSuccess

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
        # ds000117's DatasetDOI is 10.18112/openneuro.ds000117.*; not indexed
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
    """ds002001 has only DatasetDOI (OpenNeuro); the output should be empty
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


# --- Real substitute objects (NOT Mocks) for the GitHub fetch path. They mirror
# the shapes BidsMetadataSource.get_doi_references touches so the decode guard
# can be exercised without network. See issue #168.


class _RaisingContent:
    """Stand-in for a PyGithub ContentFile whose blob exceeds 1MB. The real
    ContentFile.decoded_content property asserts encoding == "base64" and raises
    AssertionError when GitHub returns encoding=None for a large blob."""

    @property
    def decoded_content(self) -> bytes:
        raise AssertionError("unsupported encoding: None")


class _NoneContent:
    """ContentFile stand-in whose decoded_content is None (defensive branch)."""

    @property
    def decoded_content(self) -> bytes | None:
        return None


class _BytesContent:
    """ContentFile stand-in whose decoded_content is real JSON bytes."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    @property
    def decoded_content(self) -> bytes:
        return self._data


class _FakeRepo:
    def __init__(self, content: object) -> None:
        self._content = content

    def get_contents(self, path: str) -> object:
        return self._content


class _FakeGithub:
    def __init__(self, content: object) -> None:
        self._content = content

    def get_repo(self, full_name: str) -> _FakeRepo:
        return _FakeRepo(self._content)


class GetDoiReferencesDecodeGuard(TestCase):
    """get_doi_references must turn an undecodable dataset_description.json blob
    into a per-dataset FetchError, never let AssertionError abort the pipeline
    (the 06-16/06-17 cron failure). Issue #168."""

    def _source_returning(self, content: object) -> BidsMetadataSource:
        # Bypass __init__ (which builds a real Github client) and inject a real
        # fake; with no local cache configured these tests exercise the GitHub
        # decode path.
        src = BidsMetadataSource.__new__(BidsMetadataSource)
        src.github = _FakeGithub(content)  # type: ignore[attr-defined]
        src._local_metadata_dir = None  # type: ignore[attr-defined]
        return src

    def test_undecodable_blob_returns_parse_error_not_raises(self) -> None:
        result = self._source_returning(_RaisingContent()).get_doi_references(
            "ds999999"
        )
        assert isinstance(result, FetchError)
        self.assertEqual(result.reason, "parse")

    def test_none_blob_returns_parse_error(self) -> None:
        result = self._source_returning(_NoneContent()).get_doi_references("ds999999")
        assert isinstance(result, FetchError)
        self.assertEqual(result.reason, "parse")

    def test_valid_blob_returns_success(self) -> None:
        payload = json.dumps(
            {"ReferencesAndLinks": ["https://doi.org/10.1038/sdata.2015.1"]}
        ).encode("utf-8")
        result = self._source_returning(_BytesContent(payload)).get_doi_references(
            "ds999999"
        )
        assert isinstance(result, FetchSuccess)
        self.assertEqual(len(result.value), 1)
        self.assertEqual(result.value[0].identifier, "10.1038/sdata.2015.1")


class _ExplodingGithub:
    """GitHub client that fails if touched -- proves the cache path skips it."""

    def get_repo(self, full_name: str) -> object:
        raise AssertionError("GitHub must not be called when the cache is present")


class GetDoiReferencesCacheTests(TestCase):
    """get_doi_references parses the cached dataset_description from
    local_metadata_dir instead of hitting GitHub, avoiding the cold-start
    rate-limit storm; it falls back to GitHub when the cache is absent. #174."""

    _DESC: ClassVar[dict[str, list[str]]] = {
        "ReferencesAndLinks": ["https://doi.org/10.1038/sdata.2015.1"]
    }

    def _source(self, github: object, local_dir: str | None) -> BidsMetadataSource:
        src = BidsMetadataSource.__new__(BidsMetadataSource)
        src.github = github  # type: ignore[attr-defined]
        src._local_metadata_dir = local_dir  # type: ignore[attr-defined]
        return src

    def _write_cache(self, tmp: str, dataset_id: str, body: dict) -> None:
        (Path(tmp) / f"{dataset_id}_datasets.json").write_text(json.dumps(body))

    def test_uses_cache_without_calling_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_cache(tmp, "ds002718", {"dataset_description": self._DESC})
            result = self._source(_ExplodingGithub(), tmp).get_doi_references(
                "ds002718"
            )
            assert isinstance(result, FetchSuccess)
            self.assertEqual(result.value[0].identifier, "10.1038/sdata.2015.1")

    def test_falls_back_to_github_when_cache_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = json.dumps(self._DESC).encode("utf-8")
            result = self._source(_FakeGithub(_BytesContent(payload)), tmp)
            self.assertEqual(len(result.get_doi_references("ds999999").value), 1)  # type: ignore[union-attr]

    def test_falls_back_when_cache_has_no_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_cache(tmp, "ds002718", {"dataset_id": "ds002718"})
            payload = json.dumps(self._DESC).encode("utf-8")
            result = self._source(_FakeGithub(_BytesContent(payload)), tmp)
            self.assertEqual(len(result.get_doi_references("ds002718").value), 1)  # type: ignore[union-attr]

    def test_no_local_dir_configured_uses_github(self) -> None:
        payload = json.dumps(self._DESC).encode("utf-8")
        result = self._source(_FakeGithub(_BytesContent(payload)), None)
        self.assertEqual(len(result.get_doi_references("ds002718").value), 1)  # type: ignore[union-attr]
