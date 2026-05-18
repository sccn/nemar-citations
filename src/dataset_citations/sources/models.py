"""Typed records and result wrappers shared by source extractors and backends.

`FetchResult` is a discriminated union: either `FetchSuccess(value)` or
`FetchError(reason, detail)`. Callers must check `result.ok` (or use
isinstance) before accessing the value. This is the project's answer to the
Phase 1 review finding that broad except blocks conflated transient failures
with legitimately empty results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

IdentifierType = Literal["doi", "pmid", "arxiv"]
SourceKind = Literal["nemar_metadata", "openneuro_description"]
FetchErrorReason = Literal[
    "not_found", "auth", "network", "parse", "rate_limit", "other"
]


@dataclass(frozen=True, slots=True)
class DoiReference:
    """One DOI/PMID/arXiv anchor extracted from a dataset's metadata."""

    identifier: str
    identifier_type: IdentifierType
    relation_type: str
    source: SourceKind
    source_field: str | None = None


@dataclass(frozen=True, slots=True)
class CitingWork:
    """One citing paper, normalized from an opencite Paper and tagged with the
    source DOI / relation it was discovered through."""

    title: str
    doi: str | None
    pmid: str | None
    openalex_id: str | None
    year: int | None
    authors: tuple[str, ...]
    venue: str | None
    abstract: str | None
    citation_count: int | None
    source_doi: str
    source_relation: str


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FetchSuccess(Generic[T]):
    value: T

    @property
    def ok(self) -> Literal[True]:
        return True


@dataclass(frozen=True, slots=True)
class FetchError:
    reason: FetchErrorReason
    detail: str

    @property
    def ok(self) -> Literal[False]:
        return False


FetchResult = FetchSuccess[T] | FetchError
