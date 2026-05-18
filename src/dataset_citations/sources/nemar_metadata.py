"""Fetch and parse `.nemar/metadata.json` for nm-prefixed nemarDatasets repos.

The file follows a DataCite-style schema (v2.0) with a `related_identifiers`
block. We honor a fixed allow-list of `relation_type` values that map to
"citations of related work belong to this dataset" semantics: References,
IsDerivedFrom, IsIdenticalTo, IsVersionOf. We skip URL-typed identifiers
(they exist for human navigation, not literature lookup).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from github import Github
from github.GithubException import GithubException

from dataset_citations.sources.doi import (
    is_openneuro_dataset_doi,
    normalize_doi,
    validate_identifier,
)
from dataset_citations.sources.models import (
    DoiReference,
    FetchError,
    FetchResult,
    FetchSuccess,
)

logger = logging.getLogger(__name__)

_CITATION_RELATIONS = frozenset(
    {"References", "IsDerivedFrom", "IsIdenticalTo", "IsVersionOf"}
)


class NemarMetadataSource:
    """Reads `.nemar/metadata.json` from a nemarDatasets repo and returns the
    DOI references suitable for opencite lookup."""

    def __init__(self, github_token: str | None = None) -> None:
        self.github = Github(github_token) if github_token else Github()

    def get_doi_references(
        self, dataset_id: str, org: str = "nemarDatasets"
    ) -> FetchResult[list[DoiReference]]:
        """Return DOI/PMID anchors for one nm-dataset, or a FetchError.

        Empty success (`FetchSuccess([])`) means the metadata file was parsed
        but contained no DOI-typed related_identifiers in our allow-list.
        That is distinct from `FetchError("not_found", ...)` (no metadata
        file).
        """
        try:
            repo = self.github.get_repo(f"{org}/{dataset_id}")
        except GithubException as e:
            return _github_error(e, f"{org}/{dataset_id}")

        try:
            content = repo.get_contents(".nemar/metadata.json")
        except GithubException as e:
            if getattr(e, "status", None) == 404:
                return FetchError("not_found", ".nemar/metadata.json missing")
            return _github_error(e, ".nemar/metadata.json")

        if isinstance(content, list):
            return FetchError("parse", "expected file, got directory listing")
        try:
            payload: Any = json.loads(content.decoded_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return FetchError("parse", f"invalid JSON: {e}")

        if not isinstance(payload, dict):
            return FetchError("parse", "metadata.json root is not an object")
        return FetchSuccess(parse_nemar_metadata(payload))


def parse_nemar_metadata(payload: dict[str, Any]) -> list[DoiReference]:
    """Pure function: convert parsed `.nemar/metadata.json` into DoiReferences.

    Exposed for unit testing with fixture files. The GitHub-fetching class
    delegates here after decoding bytes to JSON.
    """
    related = payload.get("related_identifiers") or []
    refs: list[DoiReference] = []
    for entry in related:
        ref = _entry_to_reference(entry)
        if ref is not None:
            refs.append(ref)
    return refs


def _entry_to_reference(entry: Any) -> DoiReference | None:
    if not isinstance(entry, dict):
        return None
    relation = entry.get("relation_type")
    if relation not in _CITATION_RELATIONS:
        return None
    identifier_type = entry.get("identifier_type")
    raw = entry.get("identifier")
    if not isinstance(raw, str) or not raw.strip():
        return None
    if identifier_type != "DOI":
        # URL / handle / other types: skip for opencite lookup.
        return None

    normalized = normalize_doi(raw)
    if not validate_identifier(normalized):
        logger.warning("skipping malformed DOI %r in .nemar/metadata.json", raw)
        return None
    if is_openneuro_dataset_doi(normalized):
        # OpenNeuro DatasetDOIs are not indexed in OpenAlex; skip from lookup set.
        return None
    return DoiReference(
        identifier=normalized,
        identifier_type="doi",
        relation_type=relation,
        source="nemar_metadata",
        source_field="related_identifiers",
    )


def _github_error(exc: GithubException, path: str) -> FetchError:
    status = getattr(exc, "status", None)
    if status == 404:
        return FetchError("not_found", f"{path} not found")
    if status == 401 or status == 403:
        return FetchError("auth", f"{path}: {exc}")
    if status == 429:
        return FetchError("rate_limit", f"{path}: {exc}")
    return FetchError("other", f"{path}: {exc}")
