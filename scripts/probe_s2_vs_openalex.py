"""Coverage probe: OpenAlex-only vs OpenAlex+S2(+PubMed) for our DOI anchors.

Issue #53 phase A. Runs each DOI from `scripts/probe_datasets.json` through
opencite two ways:

  - "combined": the production call path, `CitationExplorer.citing_papers`,
    which fires OpenAlex and Semantic Scholar in parallel and merges.
  - "openalex_only": `OpenAlexClient.lookup_doi` -> `citing_papers` on the
    resolved OpenAlex ID. Skips S2 entirely.

Per anchor we record the set of citing-paper DOIs returned by each path and
compute the symmetric diff. The aggregate output answers: across this
sample, how many citing papers does S2 add that OpenAlex misses?

Usage:
    uv run python scripts/probe_s2_vs_openalex.py \
        --input scripts/probe_datasets.json \
        --output .context/research/s2_vs_openalex_2026-05-19.json \
        --max-results-per-doi 100
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

from opencite.citations import CitationExplorer
from opencite.clients.openalex import OpenAlexClient
from opencite.config import Config

logger = logging.getLogger("probe_s2_vs_openalex")


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


async def _probe_one(
    config: Config,
    doi: str,
    max_results: int,
) -> dict[str, Any]:
    """Run both probes against one DOI and return the diff stats."""
    oa_branch: dict[str, Any] = {"count": 0, "error": None, "dois": []}
    combined_branch: dict[str, Any] = {"count": 0, "error": None, "dois": []}
    record: dict[str, Any] = {
        "doi": doi,
        "openalex_only": oa_branch,
        "combined": combined_branch,
    }

    # ----- OpenAlex-only path: resolve DOI -> openalex_id, then citing_papers
    try:
        oa_client: OpenAlexClient = OpenAlexClient(config)
        async with oa_client as oa:
            assert isinstance(oa, OpenAlexClient)
            paper = await oa.lookup_doi(doi)
            if paper is None or not paper.ids.openalex_id:
                record["openalex_only"]["error"] = "no_openalex_id"
                oa_dois: set[str] = set()
            else:
                cite_papers = await oa.citing_papers(
                    paper.ids.openalex_id, max_results=max_results, sort="citations"
                )
                oa_dois = _paper_doi_set(cite_papers)
                record["openalex_only"]["count"] = len(cite_papers)
                record["openalex_only"]["dois"] = sorted(oa_dois)
    except Exception as exc:
        logger.exception("openalex-only probe failed for %s", doi)
        record["openalex_only"]["error"] = f"{type(exc).__name__}: {exc}"
        oa_dois = set()

    # ----- Combined path: CitationExplorer (OpenAlex + S2 in parallel)
    try:
        async with CitationExplorer(config) as explorer:
            result = await explorer.citing_papers(
                doi, max_results=max_results, sort="citations"
            )
            combined_dois = _paper_doi_set(result.papers)
            record["combined"]["count"] = len(result.papers)
            record["combined"]["dois"] = sorted(combined_dois)
    except Exception as exc:
        logger.exception("combined probe failed for %s", doi)
        record["combined"]["error"] = f"{type(exc).__name__}: {exc}"
        combined_dois = set()

    overlap = oa_dois & combined_dois
    s2_only = combined_dois - oa_dois
    oa_unique = oa_dois - combined_dois  # should usually be empty
    record["diff"] = {
        "overlap": sorted(overlap),
        "s2_only": sorted(s2_only),
        "openalex_only_unique": sorted(oa_unique),
        "overlap_count": len(overlap),
        "s2_only_count": len(s2_only),
        "openalex_only_unique_count": len(oa_unique),
    }
    return record


async def _run(
    config: Config,
    anchors: list[tuple[str, str]],
    max_results: int,
    sleep_between: float,
) -> dict[str, Any]:
    """anchors is a list of (dataset_id, doi). Returns the full probe report."""
    per_doi: dict[str, dict[str, Any]] = {}
    started = time.time()

    unique_dois = sorted({d for _, d in anchors})
    logger.info("probing %d unique DOIs", len(unique_dois))

    for i, doi in enumerate(unique_dois, start=1):
        logger.info("[%d/%d] %s", i, len(unique_dois), doi)
        per_doi[doi] = await _probe_one(config, doi, max_results)
        if sleep_between > 0 and i < len(unique_dois):
            await asyncio.sleep(sleep_between)

    elapsed = time.time() - started

    # Aggregate. All five totals are computed in the same domain (the set of
    # citing-paper DOIs returned by each path) so they reconcile: combined ==
    # overlap + s2_unique, openalex_only == overlap + openalex_unique. Papers
    # without a DOI returned by either backend are necessarily dropped here
    # because they can't be cross-matched between paths.
    total_combined = 0
    total_oa_only = 0
    total_combined_raw = 0
    total_oa_only_raw = 0
    total_overlap = 0
    total_s2_unique = 0
    total_oa_unique = 0
    errors = 0
    no_openalex_id = 0
    truncated_dois = 0
    for rec in per_doi.values():
        oa = rec["openalex_only"]
        comb = rec["combined"]
        if oa.get("error") == "no_openalex_id":
            no_openalex_id += 1
            continue
        if oa.get("error") or comb.get("error"):
            errors += 1
            continue
        diff = rec["diff"]
        total_combined += len(set(comb["dois"]))
        total_oa_only += len(set(oa["dois"]))
        total_combined_raw += comb["count"]
        total_oa_only_raw += oa["count"]
        total_overlap += diff["overlap_count"]
        total_s2_unique += diff["s2_only_count"]
        total_oa_unique += diff["openalex_only_unique_count"]
        if comb["count"] >= max_results or oa["count"] >= max_results:
            truncated_dois += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "max_results_per_doi": max_results,
        "anchors_total": len(anchors),
        "unique_dois": len(unique_dois),
        "no_openalex_id": no_openalex_id,
        "errors": errors,
        "truncated_dois": truncated_dois,
        "totals": {
            "combined_dois": total_combined,
            "openalex_only_dois": total_oa_only,
            "overlap_dois": total_overlap,
            "s2_unique_dois": total_s2_unique,
            "openalex_unique_dois": total_oa_unique,
            "s2_unique_pct_of_combined": (
                round(100.0 * total_s2_unique / total_combined, 2)
                if total_combined
                else 0.0
            ),
            "combined_papers_raw": total_combined_raw,
            "openalex_only_papers_raw": total_oa_only_raw,
            "_raw_vs_doi_note": (
                "*_papers_raw counts include results without a usable DOI "
                "(can't be cross-matched). *_dois counts are the DOI-set "
                "domain used for diff arithmetic. These should not be mixed."
            ),
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
        help="Seconds between consecutive probes (gentle on rate limits).",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info("wrote %s", args.output)

    totals = report["totals"]
    print("\n=== Summary ===")
    print(f"unique DOIs probed: {report['unique_dois']}")
    print(f"unresolved in OpenAlex: {report['no_openalex_id']}")
    print(f"errors: {report['errors']}")
    print(f"DOIs at max_results truncation: {report['truncated_dois']}")
    print(f"combined DOIs (set domain): {totals['combined_dois']}")
    print(f"openalex-only DOIs (set domain): {totals['openalex_only_dois']}")
    print(f"overlap: {totals['overlap_dois']}")
    print(f"S2-unique (in combined but not OA-only): {totals['s2_unique_dois']}")
    print(f"OA-unique (in OA-only but not combined): {totals['openalex_unique_dois']}")
    print(f"S2-unique % of combined: {totals['s2_unique_pct_of_combined']}%")
    print(
        f"(raw paper counts including no-DOI: combined={totals['combined_papers_raw']}, "
        f"openalex_only={totals['openalex_only_papers_raw']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
