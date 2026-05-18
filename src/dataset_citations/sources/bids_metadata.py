"""Fetch and parse `dataset_description.json` for OpenNeuroDatasets ds-repos.

Legacy ds-prefixed datasets predate `.nemar/metadata.json` so there's no
structured `relation_type`. We extract DOIs/PMIDs/arXiv IDs from three free-
text fields and assign relation types heuristically:
  - `DatasetDOI`           -> IsIdenticalTo  (skipped from lookup if OpenNeuro)
  - `HowToAcknowledge`     -> IsDerivedFrom  (field literally requests citing it)
  - `ReferencesAndLinks`   -> References
"""

from __future__ import annotations

import json
import logging
from typing import Any

from github import Github
from github.GithubException import GithubException

from dataset_citations.sources.doi import (
    extract_identifiers,
    is_openneuro_dataset_doi,
    normalize_doi,
    validate_identifier,
)
from dataset_citations.sources.models import (
    DoiReference,
    FetchError,
    FetchResult,
    FetchSuccess,
    IdentifierType,
    RelationType,
)

logger = logging.getLogger(__name__)

_FIELD_RELATION: dict[str, RelationType] = {
    "DatasetDOI": "IsIdenticalTo",
    "HowToAcknowledge": "IsDerivedFrom",
    "ReferencesAndLinks": "References",
}


class BidsMetadataSource:
    """Reads `dataset_description.json` from an OpenNeuroDatasets ds-repo and
    returns DOI/PMID/arXiv references suitable for opencite lookup."""

    def __init__(self, github_token: str | None = None) -> None:
        self.github = Github(github_token) if github_token else Github()

    def get_doi_references(
        self, dataset_id: str, org: str = "OpenNeuroDatasets"
    ) -> FetchResult[list[DoiReference]]:
        try:
            repo = self.github.get_repo(f"{org}/{dataset_id}")
        except GithubException as e:
            return _github_error(e, f"{org}/{dataset_id}")

        try:
            content = repo.get_contents("dataset_description.json")
        except GithubException as e:
            if getattr(e, "status", None) == 404:
                return FetchError("not_found", "dataset_description.json missing")
            return _github_error(e, "dataset_description.json")

        if isinstance(content, list):
            return FetchError("parse", "expected file, got directory listing")
        if not hasattr(content, "decoded_content"):
            return FetchError(
                "parse",
                f"unexpected get_contents return shape: {type(content).__name__}",
            )
        try:
            payload: Any = json.loads(content.decoded_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return FetchError("parse", f"invalid JSON: {e}")
        if not isinstance(payload, dict):
            return FetchError("parse", "dataset_description.json root is not an object")

        return FetchSuccess(parse_bids_description(payload))


def parse_bids_description(desc: dict[str, Any]) -> list[DoiReference]:
    """Pure function: convert parsed `dataset_description.json` into DoiReferences.

    Exposed for unit testing with fixture files. The GitHub-fetching class
    delegates here after decoding bytes to JSON.
    """
    return _references_from_description(desc)


def _references_from_description(desc: dict[str, Any]) -> list[DoiReference]:
    refs: list[DoiReference] = []
    seen: set[tuple[str, str]] = set()

    for field_name, relation in _FIELD_RELATION.items():
        value = desc.get(field_name)
        for ident, kind in _identifiers_from_value(value):
            if kind == "doi" and is_openneuro_dataset_doi(ident):
                # Keep for record linkage only — not sent to opencite.
                continue
            key = (ident, relation)
            if key in seen:
                continue
            seen.add(key)
            refs.append(
                DoiReference(
                    identifier=ident,
                    identifier_type=kind,
                    relation_type=relation,
                    source="openneuro_description",
                    source_field=field_name,
                )
            )
    return refs


def _identifiers_from_value(
    value: Any,
) -> list[tuple[str, IdentifierType]]:
    """Recurse through a JSON value collecting all identifier hits."""
    out: list[tuple[str, IdentifierType]] = []
    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(_identifiers_from_value(item))
        return out
    if isinstance(value, dict):
        for v in value.values():
            out.extend(_identifiers_from_value(v))
        return out
    if not isinstance(value, str):
        return out
    # Whole-string DOI shortcut: catches `DatasetDOI: "doi:10.x/y"`.
    cleaned = normalize_doi(value)
    if validate_identifier(cleaned) and cleaned.startswith("10."):
        out.append((cleaned, "doi"))
        return out
    for ident, kind in extract_identifiers(value):
        out.append((ident, kind))  # type: ignore[arg-type]
    return out


def _github_error(exc: GithubException, path: str) -> FetchError:
    status = getattr(exc, "status", None)
    if status == 404:
        return FetchError("not_found", f"{path} not found")
    if status == 401 or status == 403:
        return FetchError("auth", f"{path}: {exc}")
    if status == 429:
        return FetchError("rate_limit", f"{path}: {exc}")
    return FetchError("other", f"{path}: {exc}")
