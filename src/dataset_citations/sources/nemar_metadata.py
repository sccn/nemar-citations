"""Fetch and parse `.nemar/metadata.json` for nm-prefixed nemarDatasets repos.

The file follows a DataCite-style schema (v2.0) with a `related_identifiers`
block. We honor a fixed allow-list of `relation_type` values that map to
"citations of related work belong to this dataset" semantics: References,
IsDerivedFrom, IsIdenticalTo, IsVersionOf, IsDescribedBy. `IsDescribedBy` is
how a data paper is linked (e.g. 10.1038/sdata.2015.1 describes on000117); the
downstream gemma anchor judgment buckets each kept anchor (data_paper vs
methodology / umbrella / ...). We skip URL-typed identifiers (they exist for
human navigation, not literature lookup).

Two fetch paths are supported. The default path GETs
`https://data.nemar.org/<id>/metadata.json`, which is the same neuroschema
document served from the worker without authentication or GitHub rate-limit
pressure. The legacy path pulls the file from `nemarDatasets/<id>/.nemar/metadata.json`
via the GitHub API and is retained as a fallback for IDs not yet covered
by the data.nemar.org route.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast, get_args

import requests
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
    RelationType,
)
from dataset_citations.utils.github_client import build_github

logger = logging.getLogger(__name__)

_CITATION_RELATIONS: frozenset[RelationType] = frozenset(get_args(RelationType))

DEFAULT_DATA_API_BASE = "https://data.nemar.org"
DEFAULT_DATA_API_TIMEOUT = 15.0


class NemarMetadataSource:
    """Reads `.nemar/metadata.json` and returns DOI references for opencite.

    The default fetch path uses `data.nemar.org/<id>/metadata.json`. If
    that returns 404, the source falls back to the GitHub git-tree read
    on `nemarDatasets/<id>/.nemar/metadata.json`. Set `prefer_data_api=False`
    to skip the data API entirely (useful for offline development and the
    test environment).
    """

    def __init__(
        self,
        github_token: str | None = None,
        *,
        prefer_data_api: bool = True,
        data_api_base: str = DEFAULT_DATA_API_BASE,
        data_api_timeout: float = DEFAULT_DATA_API_TIMEOUT,
    ) -> None:
        self.github = build_github(github_token)
        self.prefer_data_api = prefer_data_api
        self.data_api_base = data_api_base.rstrip("/")
        self.data_api_timeout = data_api_timeout

    def get_doi_references(
        self, dataset_id: str, org: str = "nemarDatasets"
    ) -> FetchResult[list[DoiReference]]:
        """Return DOI/PMID anchors for one nm-dataset, or a FetchError.

        Empty success (`FetchSuccess([])`) means the metadata file was parsed
        but contained no DOI-typed related_identifiers in our allow-list.
        That is distinct from `FetchError("not_found", ...)` (no metadata
        file via either route).

        Order of attempts:
          1. `data.nemar.org/<id>/metadata.json` (unless `prefer_data_api=False`).
          2. GitHub git tree on `<org>/<dataset_id>/.nemar/metadata.json`.
        Transient or absence-style errors from path 1 (not_found, rate_limit,
        network) fall back to path 2 so a 30-second worker blip doesn't drop
        every dataset in the window. Parse errors and unclassified failures
        short-circuit so the operator can investigate a malformed payload.
        """
        if self.prefer_data_api:
            data_api_result = self._fetch_from_data_api(dataset_id)
            if isinstance(data_api_result, FetchSuccess):
                return FetchSuccess(parse_nemar_metadata(data_api_result.value))
            if data_api_result.reason not in {"not_found", "rate_limit", "network"}:
                # Parse / auth / unknown errors should not silently fall back;
                # surface them so the operator can investigate.
                return data_api_result
            logger.info(
                "data.nemar.org %s for %s (%s); falling back to GitHub",
                data_api_result.reason,
                dataset_id,
                data_api_result.detail,
            )
        return self._fetch_from_github(dataset_id, org)

    def _fetch_from_data_api(self, dataset_id: str) -> FetchResult[dict[str, Any]]:
        url = f"{self.data_api_base}/{dataset_id}/metadata.json"
        try:
            response = requests.get(url, timeout=self.data_api_timeout)
        except requests.exceptions.RequestException as exc:
            return FetchError("network", f"GET {url}: {exc}")

        if response.status_code == 404:
            return FetchError("not_found", f"{url} returned 404")
        if response.status_code == 429:
            return FetchError("rate_limit", f"{url} returned 429")
        if response.status_code != 200:
            return FetchError(
                "other",
                f"GET {url}: HTTP {response.status_code} {response.text[:200]}",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            return FetchError("parse", f"invalid JSON from {url}: {exc}")
        if not isinstance(payload, dict):
            return FetchError("parse", f"{url} root is not an object")
        return FetchSuccess(payload)

    def _fetch_from_github(
        self, dataset_id: str, org: str
    ) -> FetchResult[list[DoiReference]]:
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
        # `decoded_content` asserts the blob is base64-encoded; a >1MB
        # .nemar/metadata.json comes back with encoding=None and the property
        # raises AssertionError, which hasattr() propagates. Guard it so one
        # oversized blob is a per-dataset parse failure, not a pipeline abort
        # (same fix as bids_metadata.get_doi_references; see issue #168).
        try:
            raw = content.decoded_content
        except (AssertionError, ValueError, AttributeError) as e:
            return FetchError("parse", f"could not decode .nemar/metadata.json: {e}")
        if raw is None:
            return FetchError("parse", ".nemar/metadata.json has no decodable content")
        try:
            payload: Any = json.loads(raw.decode("utf-8"))
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
        relation_type=cast(RelationType, relation),
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
