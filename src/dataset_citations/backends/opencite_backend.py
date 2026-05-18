"""Sync facade over `opencite.citations.CitationExplorer`.

opencite is async-only; this module hides the asyncio boilerplate so the
rest of the pipeline (sync, pandas-first) can stay sync. Batches reuse a
single `CitationExplorer` session so we get connection pooling and one
catalog warm-up per call.

Errors are surfaced through `FetchResult`, never silently absorbed. The
Phase 1 review found that an opencite rate limit was being cached as
"this DOI has zero citing works"; here a rate limit returns
`FetchError("rate_limit", ...)` and the caller decides whether to retry.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from opencite.citations import CitationExplorer
from opencite.config import Config

from dataset_citations.sources.models import (
    Author,
    CitingWork,
    DoiReference,
    FetchError,
    FetchResult,
    FetchSuccess,
)

logger = logging.getLogger(__name__)


class OpenCiteBackend:
    """Resolve `DoiReference` anchors into lists of `CitingWork` via opencite."""

    def __init__(
        self,
        config: Config | None = None,
        *,
        max_results_per_doi: int = 100,
        concurrency: int = 4,
    ) -> None:
        self._config = config or Config.from_env()
        self._max_results_per_doi = max_results_per_doi
        self._concurrency = max(1, concurrency)

    def get_citing_works(self, ref: DoiReference) -> FetchResult[list[CitingWork]]:
        """Look up citing works for a single anchor."""
        return asyncio.run(self._batch_async([ref]))[ref.identifier]

    def get_citing_works_batch(
        self, refs: Iterable[DoiReference]
    ) -> dict[str, FetchResult[list[CitingWork]]]:
        """Look up citing works for many anchors, reusing one opencite session."""
        ref_list = list(refs)
        if not ref_list:
            return {}
        return asyncio.run(self._batch_async(ref_list))

    async def _batch_async(
        self, refs: list[DoiReference]
    ) -> dict[str, FetchResult[list[CitingWork]]]:
        results: dict[str, FetchResult[list[CitingWork]]] = {}
        semaphore = asyncio.Semaphore(self._concurrency)
        async with CitationExplorer(self._config) as explorer:

            async def run_one(ref: DoiReference) -> FetchResult[list[CitingWork]]:
                async with semaphore:
                    return await self._lookup(explorer, ref)

            # return_exceptions=True isolates a single failing lookup from the
            # whole batch; we convert each leak-through to FetchError below.
            outcomes = await asyncio.gather(
                *(run_one(r) for r in refs), return_exceptions=True
            )
        for ref, outcome in zip(refs, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                logger.exception(
                    "uncaught exception in opencite lookup for %s",
                    ref.identifier,
                    exc_info=outcome,
                )
                results[ref.identifier] = classify_error(outcome, ref.identifier)
            else:
                results[ref.identifier] = outcome
        return results

    async def _lookup(
        self, explorer: CitationExplorer, ref: DoiReference
    ) -> FetchResult[list[CitingWork]]:
        try:
            result = await explorer.citing_papers(
                ref.identifier,
                max_results=self._max_results_per_doi,
                sort="citations",
            )
        except Exception as exc:
            # opencite raises bare Exception subclasses for HTTP / parse fails;
            # narrow when neuromechanist/opencite#32 adds typed errors. We let
            # KeyboardInterrupt / SystemExit / asyncio.CancelledError escape.
            return classify_error(exc, ref.identifier)

        works = [
            _paper_to_citing_work(paper, ref)
            for paper in (result.papers or [])
            if paper.title
        ]
        return FetchSuccess(works)


def _paper_to_citing_work(paper: Any, ref: DoiReference) -> CitingWork:
    ids = paper.ids
    venue = paper.source_venue.name if paper.source_venue else None
    authors = tuple(
        _to_author(a) for a in (paper.authors or []) if getattr(a, "name", None)
    )
    return CitingWork(
        title=paper.title,
        doi=ids.doi or None,
        pmid=ids.pmid or None,
        openalex_id=ids.openalex_id or None,
        year=paper.year,
        authors=authors,
        venue=venue,
        abstract=paper.abstract or None,
        citation_count=(
            paper.citation_count if paper.citation_count is not None else None
        ),
        source_doi=ref.identifier,
        source_relation=ref.relation_type,
    )


def _to_author(a: Any) -> Author:
    return Author(
        name=a.name,
        family=getattr(a, "family_name", None) or None,
        given=getattr(a, "given_name", None) or None,
        orcid=getattr(a, "orcid", None) or None,
    )


def classify_error(exc: BaseException, identifier: str) -> FetchError:
    """Map an opencite / httpx exception to a FetchError reason.

    Precedence order (first match wins):
      rate_limit -> auth -> not_found -> network -> other.
    Rate-limit and auth signatures are checked first so that an upstream
    error message that happens to mention 'not found' or 'connect' (e.g.,
    'Cannot connect to host: not found in DNS' on a 429 reroute) is still
    routed to the correct bucket.

    Uses httpx's `response.status_code` when the exception exposes one; falls
    back to substring matching of the stringified exception. Tracked for
    cleanup in neuromechanist/opencite#32 (typed exceptions upstream).
    """
    msg = f"{type(exc).__name__}: {exc}"
    status = _status_code_of(exc)
    if status == 429:
        return FetchError("rate_limit", msg)
    if status in (401, 403):
        return FetchError("auth", msg)
    if status == 404:
        return FetchError("not_found", msg)

    text = str(exc).lower()
    if "429" in text or "rate limit" in text or "too many requests" in text:
        return FetchError("rate_limit", msg)
    if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
        return FetchError("auth", msg)
    if "404" in text or "not found" in text:
        return FetchError("not_found", msg)
    if "timeout" in text or "timed out" in text or "connect" in text:
        return FetchError("network", msg)
    logger.exception(
        "unclassified opencite failure for %s", identifier, exc_info=exc
    )
    return FetchError("other", msg)


def _status_code_of(exc: BaseException) -> int | None:
    """Return the HTTP status code an exception carries, or None.

    Handles httpx.HTTPStatusError-style exceptions where the response attr
    exposes `.status_code`, plus the convention some libraries use of
    setting `exc.status_code` directly.
    """
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status", None)
    if isinstance(code, int):
        return code
    return None
