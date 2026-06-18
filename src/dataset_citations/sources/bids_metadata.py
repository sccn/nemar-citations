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
import os
from typing import Any

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
from dataset_citations.utils.github_client import build_github

logger = logging.getLogger(__name__)

_FIELD_RELATION: dict[str, RelationType] = {
    "DatasetDOI": "IsIdenticalTo",
    "HowToAcknowledge": "IsDerivedFrom",
    "ReferencesAndLinks": "References",
}


class BidsMetadataSource:
    """Reads `dataset_description.json` from an OpenNeuroDatasets ds-repo and
    returns DOI/PMID/arXiv references suitable for opencite lookup."""

    def __init__(
        self,
        github_token: str | None = None,
        *,
        local_metadata_dir: str | None = None,
    ) -> None:
        self.github = build_github(github_token)
        # When set, get_doi_references parses the cached dataset_description
        # from `<local_metadata_dir>/<id>_datasets.json` (written by
        # retrieve-metadata) instead of refetching from GitHub. This avoids the
        # cold-start GitHub rate-limit storm on the ~463 legacy ds-* datasets
        # (issue #174). GitHub remains the fallback when the cache is absent.
        self._local_metadata_dir = local_metadata_dir

    def get_doi_references(
        self, dataset_id: str, org: str = "OpenNeuroDatasets"
    ) -> FetchResult[list[DoiReference]]:
        cached = self._cached_description(dataset_id)
        if cached is not None:
            return FetchSuccess(parse_bids_description(cached))

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
        # `decoded_content` is a PyGithub property that asserts the blob is
        # base64-encoded. GitHub returns encoding=None for blobs larger than 1MB,
        # so the property raises AssertionError -- and hasattr() PROPAGATES that
        # rather than returning False. Catch it (plus the analogous ValueError /
        # AttributeError) so one undecodable dataset_description.json is a
        # per-dataset parse failure instead of aborting the whole pipeline. This
        # is the judge-anchors analogue of the retrieve-metadata fix in PR #119.
        try:
            raw = content.decoded_content
        except (AssertionError, ValueError, AttributeError) as e:
            return FetchError(
                "parse", f"could not decode dataset_description.json: {e}"
            )
        if raw is None:
            return FetchError(
                "parse", "dataset_description.json has no decodable content"
            )
        try:
            payload: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return FetchError("parse", f"invalid JSON: {e}")
        if not isinstance(payload, dict):
            return FetchError("parse", "dataset_description.json root is not an object")

        return FetchSuccess(parse_bids_description(payload))

    def _cached_description(self, dataset_id: str) -> dict[str, Any] | None:
        """Return the cached dataset_description dict, or None to use GitHub.

        Reads `<local_metadata_dir>/<id>_datasets.json` (retrieve-metadata's
        output). Returns None when no cache dir is configured, the file is
        missing / unreadable, or it carries no non-empty `dataset_description`
        object, so the caller falls back to the live GitHub fetch.
        """
        if not self._local_metadata_dir:
            return None
        path = os.path.join(self._local_metadata_dir, f"{dataset_id}_datasets.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "could not read cached metadata %s (%s); falling back to GitHub",
                path,
                e,
            )
            return None
        desc = data.get("dataset_description") if isinstance(data, dict) else None
        return desc if isinstance(desc, dict) and desc else None


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
                # Keep for record linkage only; not sent to opencite.
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
