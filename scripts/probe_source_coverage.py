"""Per-source citation-coverage probe across opencite's cited-by sources.

Epic #180, phase 2. Generalizes the earlier `probe_s2_vs_openalex.py`
(OpenAlex-vs-combined) into a per-source measurement: for each DOI anchor it
runs an independent single-source cited-by lookup against every source that
implements `citing_papers` in opencite, then reports how many citing papers
each source contributes *uniquely* (returned by that source and no other).

opencite's cited-by sources (clients with a `citing_papers` method):

  - openalex : `OpenAlexClient.lookup_doi(doi)` -> `citing_papers(openalex_id)`
  - s2       : `SemanticScholarClient.citing_papers("DOI:<doi>")`
  - pubmed   : `PubMedClient.lookup_doi(doi)` -> `citing_papers(pmid)`

`CitationExplorer` (the production path) only fans out to openalex + s2 today;
this probe also exercises pubmed directly so we can decide whether wiring
pubmed into the explorer upstream is worth it.

The aggregate answers: across this sample, what does each source uniquely add
on top of the others, and how much do they overlap?

Usage:
    uv run python scripts/probe_source_coverage.py \
        --input scripts/probe_datasets.json \
        --output .context/research/source_coverage_2026-06-19.json \
        --max-results-per-doi 100 --sleep-between 1.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opencite.clients.openalex import OpenAlexClient
from opencite.clients.pubmed import PubMedClient
from opencite.clients.semantic_scholar import SemanticScholarClient
from opencite.config import Config
from opencite.exceptions import APIError

logger = logging.getLogger("probe_source_coverage")

# Sources this probe knows how to query for cited-by, in display order. Each
# entry maps to a `_lookup_<name>` coroutine below.
SOURCES: tuple[str, ...] = ("openalex", "s2", "pubmed")


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def _paper_doi_set(papers: Iterable[Any]) -> set[str]:
    """Project an opencite Paper iterable into a set of normalized DOIs.

    Papers without a DOI are skipped (they can't be cross-matched).
    """
    out: set[str] = set()
    for p in papers:
        doi = _normalize_doi(getattr(p, "doi", None))
        if doi:
            out.add(doi)
    return out


def summarize_source_sets(source_dois: dict[str, set[str]]) -> dict[str, Any]:
    """Pure set arithmetic over one anchor's per-source citing-DOI sets.

    Returns, per source: the count and the number of DOIs unique to that
    source (present there and in no other source). Plus the union size,
    every pairwise overlap, and the all-source intersection. No I/O; this is
    the unit covered by tests.
    """
    sources = sorted(source_dois)
    union: set[str] = set().union(*source_dois.values()) if source_dois else set()

    per_source: dict[str, dict[str, int]] = {}
    for name in sources:
        mine = source_dois[name]
        others: set[str] = (
            set().union(*(source_dois[o] for o in sources if o != name))
            if len(sources) > 1
            else set()
        )
        per_source[name] = {
            "count": len(mine),
            "unique": len(mine - others),
        }

    pairwise: dict[str, int] = {}
    for i, a in enumerate(sources):
        for b in sources[i + 1 :]:
            pairwise[f"{a}&{b}"] = len(source_dois[a] & source_dois[b])

    all_overlap = (
        len(set.intersection(*(source_dois[s] for s in sources))) if sources else 0
    )

    return {
        "union": len(union),
        "per_source": per_source,
        "pairwise_overlap": pairwise,
        "all_source_overlap": all_overlap,
    }


async def _lookup_openalex(config: Config, doi: str, max_results: int) -> set[str]:
    async with OpenAlexClient(config) as oa:
        assert isinstance(oa, OpenAlexClient)
        paper = await oa.lookup_doi(doi)
        if paper is None or not paper.ids.openalex_id:
            raise LookupError("no_openalex_id")
        cites = await oa.citing_papers(
            paper.ids.openalex_id, max_results=max_results, sort="citations"
        )
        return _paper_doi_set(cites)


async def _lookup_s2(config: Config, doi: str, max_results: int) -> set[str]:
    async with SemanticScholarClient(config) as s2:
        assert isinstance(s2, SemanticScholarClient)
        try:
            cites = await s2.citing_papers(f"DOI:{doi}", max_results=max_results)
        except APIError as exc:
            # A 404 means S2 has not indexed this DOI (e.g. NEMAR/Zenodo data
            # records) -- a legitimate "no record on this source", the same
            # semantic as OpenAlex's no_openalex_id / PubMed's no_pmid. Surface
            # it as LookupError so it is not counted as a transport failure.
            if exc.status_code == 404:
                raise LookupError("no_s2_record") from exc
            raise
        return _paper_doi_set(cites)


async def _lookup_pubmed(config: Config, doi: str, max_results: int) -> set[str]:
    async with PubMedClient(config) as pm:
        assert isinstance(pm, PubMedClient)
        paper = await pm.lookup_doi(doi)
        if paper is None or not paper.ids.pmid:
            raise LookupError("no_pmid")
        cites = await pm.citing_papers(paper.ids.pmid, max_results=max_results)
        return _paper_doi_set(cites)


_LOOKUPS = {
    "openalex": _lookup_openalex,
    "s2": _lookup_s2,
    "pubmed": _lookup_pubmed,
}


async def _probe_one(
    config: Config,
    doi: str,
    max_results: int,
    sources: tuple[str, ...],
) -> dict[str, Any]:
    """Run one independent single-source cited-by lookup per source."""
    record: dict[str, Any] = {"doi": doi, "sources": {}}
    source_dois: dict[str, set[str]] = {}
    for name in sources:
        # error_kind distinguishes "not indexed on this source" (a legitimate
        # empty contribution) from "transport" (a real failure that hides what
        # the source would have returned, contaminating the unique counts).
        branch: dict[str, Any] = {
            "count": 0,
            "error": None,
            "error_kind": None,
            "dois": [],
        }
        try:
            found = await _LOOKUPS[name](config, doi, max_results)
            source_dois[name] = found
            branch["count"] = len(found)
            branch["dois"] = sorted(found)
        except LookupError as exc:
            # Anchor not indexed on this source (no PMID / no OpenAlex id / S2
            # 404). A genuine empty contribution, not a failure.
            source_dois[name] = set()
            branch["error"] = str(exc)
            branch["error_kind"] = "unresolved"
        except Exception as exc:
            logger.exception("%s probe failed for %s", name, doi)
            source_dois[name] = set()
            branch["error"] = f"{type(exc).__name__}: {exc}"
            branch["error_kind"] = "transport"
        record["sources"][name] = branch

    record["diff"] = summarize_source_sets(source_dois)
    return record


async def _run(
    config: Config,
    anchors: list[tuple[str, str]],
    max_results: int,
    sleep_between: float,
    sources: tuple[str, ...],
) -> dict[str, Any]:
    """anchors is a list of (dataset_id, doi). Returns the full probe report."""
    per_doi: dict[str, dict[str, Any]] = {}
    started = time.time()

    unique_dois = sorted({d for _, d in anchors})
    logger.info("probing %d unique DOIs across sources %s", len(unique_dois), sources)

    for i, doi in enumerate(unique_dois, start=1):
        logger.info("[%d/%d] %s", i, len(unique_dois), doi)
        per_doi[doi] = await _probe_one(config, doi, max_results, sources)
        if sleep_between > 0 and i < len(unique_dois):
            await asyncio.sleep(sleep_between)

    elapsed = time.time() - started

    # Aggregate per-source totals across all anchors. Counts are in the
    # citing-paper DOI-set domain (papers without a DOI are dropped because
    # they can't be cross-matched between sources).
    totals_count: dict[str, int] = {s: 0 for s in sources}
    totals_unique: dict[str, int] = {s: 0 for s in sources}
    total_union = 0
    # "unresolved" = anchor not indexed on the source (legitimate empty);
    # "transport" = a real failure that hides what the source would have
    # returned and therefore inflates every other source's unique count.
    unresolved: dict[str, int] = {s: 0 for s in sources}
    transport_errors: dict[str, int] = {s: 0 for s in sources}
    for rec in per_doi.values():
        diff = rec["diff"]
        total_union += diff["union"]
        for s in sources:
            totals_count[s] += diff["per_source"][s]["count"]
            totals_unique[s] += diff["per_source"][s]["unique"]
            kind = rec["sources"][s]["error_kind"]
            if kind == "unresolved":
                unresolved[s] += 1
            elif kind == "transport":
                transport_errors[s] += 1

    unique_pct = {
        s: (round(100.0 * totals_unique[s] / total_union, 2) if total_union else 0.0)
        for s in sources
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "max_results_per_doi": max_results,
        "sources": list(sources),
        "anchors_total": len(anchors),
        "unique_dois": len(unique_dois),
        "totals": {
            "union_dois": total_union,
            "per_source_dois": totals_count,
            "per_source_unique_dois": totals_unique,
            "per_source_unique_pct_of_union": unique_pct,
            "per_source_unresolved": unresolved,
            "per_source_transport_errors": transport_errors,
        },
        "per_doi": per_doi,
    }


def _load_anchors(path: Path) -> list[tuple[str, str]]:
    payload = json.loads(path.read_text())
    out: list[tuple[str, str]] = []
    for ds in payload["datasets"]:
        for entry in ds["anchors"]:
            out.append((ds["dataset_id"], entry["doi"]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("scripts/probe_datasets.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-results-per-doi", type=int, default=100)
    parser.add_argument(
        "--sleep-between",
        type=float,
        default=1.0,
        help="Seconds between consecutive anchors (gentle on rate limits).",
    )
    parser.add_argument(
        "--sources",
        default=",".join(SOURCES),
        help="Comma-separated subset of: " + ",".join(SOURCES),
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())
    unknown = [s for s in sources if s not in _LOOKUPS]
    if unknown:
        logger.error("unknown sources %s; known: %s", unknown, list(_LOOKUPS))
        return 1

    anchors = _load_anchors(args.input)
    if not anchors:
        logger.error("no anchors loaded from %s", args.input)
        return 1

    config = Config.from_env()
    report = asyncio.run(
        _run(
            config,
            anchors,
            max_results=args.max_results_per_doi,
            sleep_between=args.sleep_between,
            sources=sources,
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info("wrote %s", args.output)

    totals = report["totals"]
    print("\n=== Summary ===")
    print(f"unique DOIs probed: {report['unique_dois']}")
    print(f"union of citing DOIs (all sources): {totals['union_dois']}")
    for s in sources:
        print(
            f"  {s:9s} total={totals['per_source_dois'][s]:5d} "
            f"unique={totals['per_source_unique_dois'][s]:5d} "
            f"({totals['per_source_unique_pct_of_union'][s]}% of union) "
            f"unresolved={totals['per_source_unresolved'][s]} "
            f"transport_errors={totals['per_source_transport_errors'][s]}"
        )
    if any(totals["per_source_transport_errors"].values()):
        print(
            "\nWARNING: transport errors occurred. A failed source contributes "
            "an empty set, so the other sources' 'unique' counts above are "
            "INFLATED for the affected anchors. Re-run, or read the unique%% as "
            "an upper bound, when transport_errors > 0."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
