"""Sync facade over `opencite.citations.CitationExplorer`.

opencite is async-only; this module hides the asyncio boilerplate so the
rest of the pipeline (sync, pandas-first) can stay sync. Batches reuse a
single `CitationExplorer` session so we get connection pooling and one
catalog warm-up per call.

Errors are surfaced through `FetchResult`, never silently absorbed. The
Phase 1 review found that an opencite rate limit was being cached as
"this DOI has zero citing works"; here a rate limit returns
`FetchError("rate_limit", ...)` and the caller decides whether to retry.

DOIs whose prefixes are known to 404 on Semantic Scholar are routed
through OpenAlex directly, bypassing the CitationExplorer (which would
otherwise fire S2 in parallel and burn retry budget on a guaranteed
miss). See the May 2026 coverage probe in
`.context/research/s2_vs_openalex_2026-05-19.json` and `S2_SKIP_PREFIXES`
below for the list.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

import httpx
from opencite.citations import CitationExplorer
from opencite.clients.openalex import OpenAlexClient
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

# DOI prefixes that the May 2026 coverage probe confirmed return 404 on
# Semantic Scholar's `paper/cited_by` endpoint. For anchors matching any of
# these, we call OpenAlex directly and skip the S2 round-trip entirely.
# Keep this list lowercase; the matcher lowercases its input before checking.
S2_SKIP_PREFIXES: tuple[str, ...] = (
    "10.82901/nemar.",  # NEMAR-minted DOIs (too new for S2 index)
    "10.5281/zenodo.",  # Zenodo data records (data, not papers)
    "10.13026/",  # PhysioNet data records
)


def should_skip_s2(identifier: str) -> bool:
    """Return True if this DOI is known to 404 on Semantic Scholar.

    Pure function; safe to call from any layer. Lowercases the input so
    matching is insensitive to the original DOI casing.
    """
    lowered = identifier.lower()
    return any(lowered.startswith(p) for p in S2_SKIP_PREFIXES)


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

    def get_paper(self, doi: str) -> FetchResult[CitingWork]:
        """Look up the anchor paper's own bib + abstract via OpenAlex.

        Returns a `CitingWork` populated with the paper's title, abstract,
        authors, venue, year, and ID fields. The `source_doi` is set to the
        looked-up DOI and `source_relation` defaults to "References" since
        the model only carries the four DataCite values; callers treating
        this as a self-lookup should ignore both fields.

        Used by epic #76's anchor adjudication path (probe + judge-anchors
        CLI) to assemble the candidate paper context for the LLM prompt.
        Sync facade over opencite's async `OpenAlexClient.lookup_doi`.
        """
        return asyncio.run(self._get_paper_async(doi))

    async def _get_paper_async(self, doi: str) -> FetchResult[CitingWork]:
        # Narrow exception list: classify_error is built for network-shaped
        # failures, so we only route those through it. Programmer errors
        # (AttributeError on opencite API drift, AssertionError on the
        # isinstance invariant below, TypeError) must propagate to surface
        # the contract break instead of being silently demoted to
        # FetchError("other", ...). Mirror this list against the existing
        # _lookup branch's handling if it widens in the future.
        try:
            async with OpenAlexClient(self._config) as openalex_base:
                assert isinstance(openalex_base, OpenAlexClient), (
                    "opencite changed OpenAlexClient.__aenter__ return type; "
                    "expected an OpenAlexClient bound, got "
                    f"{type(openalex_base).__name__}"
                )
                paper = await openalex_base.lookup_doi(doi)
        except (httpx.HTTPError, asyncio.TimeoutError, OSError) as exc:
            return classify_error(exc, doi)

        if paper is None or not paper.title:
            return FetchError(
                "not_found", f"{doi}: not found in OpenAlex (anchor self-lookup)"
            )

        # Synthesize a self-referential anchor so we can reuse the existing
        # paper -> CitingWork mapper. Callers treat source_relation as opaque
        # for self-lookups; the dataclass invariant just requires a non-empty
        # source_doi and a valid RelationType literal.
        self_ref = DoiReference(
            identifier=doi,
            identifier_type="doi",
            relation_type="References",
            source="nemar_catalog",
            source_field="self_lookup",
        )
        return FetchSuccess(_paper_to_citing_work(paper, self_ref))

    async def _batch_async(
        self, refs: list[DoiReference]
    ) -> dict[str, FetchResult[list[CitingWork]]]:
        results: dict[str, FetchResult[list[CitingWork]]] = {}
        semaphore = asyncio.Semaphore(self._concurrency)
        # Open both clients up-front so each batch can mix S2-skip and
        # full-explorer paths without redundant session setup. The
        # CitationExplorer owns its own internal OpenAlexClient; the second
        # client below is what the S2-skip path uses.
        async with (
            CitationExplorer(self._config) as explorer,
            OpenAlexClient(self._config) as openalex_base,
        ):
            # opencite's `__aenter__` returns the BaseClient bound; narrow
            # back to OpenAlexClient so the method signature stays specific.
            assert isinstance(openalex_base, OpenAlexClient), (
                "opencite changed OpenAlexClient.__aenter__ return type; "
                "expected an OpenAlexClient bound, got "
                f"{type(openalex_base).__name__}"
            )
            openalex = openalex_base

            async def run_one(ref: DoiReference) -> FetchResult[list[CitingWork]]:
                async with semaphore:
                    if should_skip_s2(ref.identifier):
                        return await self._lookup_openalex_only(openalex, ref)
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
            # narrow when neuromechanist/opencite#33 adds typed errors. We let
            # KeyboardInterrupt / SystemExit / asyncio.CancelledError escape.
            return classify_error(exc, ref.identifier)

        works = [
            _paper_to_citing_work(paper, ref)
            for paper in (result.papers or [])
            if paper.title
        ]
        return FetchSuccess(works)

    async def _lookup_openalex_only(
        self, openalex: OpenAlexClient, ref: DoiReference
    ) -> FetchResult[list[CitingWork]]:
        """Resolve `ref` via OpenAlex only, skipping Semantic Scholar.

        Two HTTP requests: `lookup_doi` to get the OpenAlex work ID, then
        `citing_papers` against that ID. Used for DOI families that the May
        2026 probe confirmed return 404 on S2 (`S2_SKIP_PREFIXES`).
        """
        try:
            paper = await openalex.lookup_doi(ref.identifier)
            if paper is None or not paper.ids.openalex_id:
                return FetchError(
                    "not_found",
                    f"{ref.identifier}: not found in OpenAlex (S2 skipped by prefix)",
                )
            cite_papers = await openalex.citing_papers(
                paper.ids.openalex_id,
                max_results=self._max_results_per_doi,
                sort="citations",
            )
        except Exception as exc:
            return classify_error(exc, ref.identifier)

        works = [_paper_to_citing_work(p, ref) for p in cite_papers if p.title]
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
    cleanup in neuromechanist/opencite#33 (typed exceptions upstream).
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
    logger.exception("unclassified opencite failure for %s", identifier, exc_info=exc)
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
