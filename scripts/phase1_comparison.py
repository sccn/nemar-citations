#!/usr/bin/env python3
"""Phase 1 deliverable: scholarly-baseline vs opencite-DOI citation comparison.

For a sample of 12 ds-datasets (with existing citations/json snapshots from
scholarly) + 3 nm-datasets (citation discovery only), this script:
  - loads the scholarly baseline from citations/json/<id>_citations.json
  - resolves DOIs for that dataset (ds: phase1_ds_dois.csv;
    nm: .nemar/metadata.json fetched live)
  - runs `uvx opencite cite <doi> --direction citing -f json` for each DOI
  - computes overlap and per-dataset counts

Outputs:
    .context/phase1_comparison.csv       - per-dataset numbers
    .context/phase1_opencite_raw.json    - cached opencite output for reproducibility

Usage:
    uv run scripts/phase1_comparison.py [--ds-sample N] [--nm-ids ID1,ID2,...] [--max-citing K]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:\w]+", re.IGNORECASE)

DEFAULT_NM_IDS = ["nm000103", "nm000115", "nm000121"]


def normalize_doi(s: str) -> str:
    s = s.strip()
    s = s.removeprefix("doi:").removeprefix("DOI:").strip()
    s = s.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    s = s.removeprefix("https://dx.doi.org/").removeprefix("http://dx.doi.org/")
    return s.strip().rstrip(".,;").lower()


def normalize_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()


@dataclass
class DatasetSnapshot:
    dataset_id: str
    scholarly_titles: set[str] = field(default_factory=set)
    scholarly_dois: set[str] = field(default_factory=set)
    source_dois: list[tuple[str, str]] = field(default_factory=list)
    opencite_titles: set[str] = field(default_factory=set)
    opencite_dois: set[str] = field(default_factory=set)
    opencite_errors: int = 0


def load_scholarly_baseline(
    citations_dir: Path, dataset_id: str
) -> tuple[set[str], set[str]]:
    """Load (titles, dois) from existing scholarly snapshot."""
    path = citations_dir / f"{dataset_id}_citations.json"
    if not path.exists():
        return set(), set()
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return set(), set()
    titles: set[str] = set()
    dois: set[str] = set()
    for detail in data.get("citation_details") or []:
        title = detail.get("title") or ""
        if title:
            titles.add(normalize_title(title))
        # Scholarly snapshots embed DOIs in url / bib fields.
        for blob in (detail.get("url") or "", json.dumps(detail.get("bib") or {})):
            for m in DOI_RE.finditer(blob or ""):
                dois.add(normalize_doi(m.group(0)))
    return titles, dois


def load_ds_source_dois(csv_path: Path, dataset_id: str) -> list[tuple[str, str]]:
    """Return (doi, source_field) entries for one ds-dataset."""
    if not csv_path.exists():
        return []
    out: list[tuple[str, str]] = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            if row["dataset_id"] == dataset_id and not row["doi"].startswith("pmid:"):
                out.append((row["doi"], row["source_field"]))
    return out


def fetch_nm_source_dois(nm_id: str) -> list[tuple[str, str]]:
    """Fetch .nemar/metadata.json and return (doi, relation_type) entries."""
    api_path = f"repos/nemarDatasets/{nm_id}/contents/.nemar/metadata.json"
    res = subprocess.run(
        ["gh", "api", api_path], capture_output=True, text=True, check=False
    )
    if res.returncode != 0:
        return []
    try:
        info = json.loads(res.stdout)
        download_url = info.get("download_url")
    except (json.JSONDecodeError, AttributeError):
        return []
    if not download_url:
        return []
    raw = subprocess.run(
        ["curl", "-sL", download_url], capture_output=True, text=True, check=False
    )
    if raw.returncode != 0:
        return []
    try:
        meta = json.loads(raw.stdout)
    except json.JSONDecodeError:
        return []
    out: list[tuple[str, str]] = []
    for entry in meta.get("related_identifiers") or []:
        if entry.get("identifier_type") != "DOI":
            continue
        relation = entry.get("relation_type", "Unknown")
        identifier = entry.get("identifier", "")
        if identifier:
            out.append((normalize_doi(identifier), relation))
    return out


def opencite_citing(doi: str, max_results: int) -> tuple[list[dict], str | None]:
    """Run opencite cite via uvx; return (papers, error)."""
    cmd = [
        "uvx",
        "--from",
        "opencite",
        "opencite",
        "cite",
        doi,
        "--direction",
        "citing",
        "-f",
        "json",
        "--max",
        str(max_results),
        "--sort",
        "citations",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
    if res.returncode != 0:
        return [], f"exit {res.returncode}: {res.stderr.strip()[:200]}"
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        return [], f"invalid JSON from opencite: {e}"
    # opencite cite returns either a list of papers or {"papers":[...]} depending on version.
    if isinstance(data, dict):
        papers = data.get("papers") or data.get("results") or []
    else:
        papers = data if isinstance(data, list) else []
    return papers, None


def paper_identifiers(paper: dict) -> tuple[str | None, str | None]:
    """Return (normalized_doi, normalized_title) from an opencite paper record."""
    title = paper.get("title") or ""
    doi = None
    ids = paper.get("identifiers") or paper.get("ids") or {}
    if isinstance(ids, dict):
        for key in ("doi", "DOI"):
            v = ids.get(key)
            if v:
                doi = normalize_doi(v)
                break
    if doi is None:
        # Some opencite payloads emit doi at the top level.
        v = paper.get("doi") or paper.get("DOI")
        if v:
            doi = normalize_doi(v)
    return doi, (normalize_title(title) if title else None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--citations-dir", type=Path, default=Path("citations/json"))
    parser.add_argument(
        "--ds-doi-csv", type=Path, default=Path(".context/phase1_ds_dois.csv")
    )
    parser.add_argument("--ds-sample", type=int, default=12)
    parser.add_argument(
        "--nm-ids",
        type=str,
        default=",".join(DEFAULT_NM_IDS),
        help="Comma-separated nm dataset IDs",
    )
    parser.add_argument(
        "--max-citing", type=int, default=100, help="Cap citing-works per DOI"
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(".context/phase1_comparison.csv"),
    )
    parser.add_argument(
        "--cache-json",
        type=Path,
        default=Path(".context/phase1_opencite_raw.json"),
    )
    args = parser.parse_args()

    # Choose ds-datasets: first N with at least one DOI in the CSV.
    ds_to_dois: dict[str, list[tuple[str, str]]] = defaultdict(list)
    if args.ds_doi_csv.exists():
        with args.ds_doi_csv.open() as f:
            for row in csv.DictReader(f):
                if row["doi"].startswith("pmid:"):
                    continue
                ds_to_dois[row["dataset_id"]].append((row["doi"], row["source_field"]))
    if not ds_to_dois:
        print(
            f"No DOIs in {args.ds_doi_csv}; run phase1_doi_extract.py first.",
            file=sys.stderr,
        )
        return 1

    ds_sample = sorted(ds_to_dois)[: args.ds_sample]
    nm_sample = [s for s in args.nm_ids.split(",") if s.strip()]

    print(f"ds sample ({len(ds_sample)}): {', '.join(ds_sample)}", file=sys.stderr)
    print(f"nm sample ({len(nm_sample)}): {', '.join(nm_sample)}", file=sys.stderr)

    cache: dict = {}
    if args.cache_json.exists():
        try:
            cache = json.loads(args.cache_json.read_text())
        except json.JSONDecodeError:
            cache = {}

    snapshots: list[DatasetSnapshot] = []

    def process(
        dataset_id: str, source_dois: list[tuple[str, str]], is_ds: bool
    ) -> None:
        snap = DatasetSnapshot(dataset_id=dataset_id, source_dois=source_dois)
        if is_ds:
            snap.scholarly_titles, snap.scholarly_dois = load_scholarly_baseline(
                args.citations_dir, dataset_id
            )
        for i, (doi, label) in enumerate(source_dois, 1):
            cache_key = f"{doi}|{args.max_citing}"
            if cache_key in cache:
                papers = cache[cache_key].get("papers", [])
                error = cache[cache_key].get("error")
            else:
                print(
                    f"    [{i}/{len(source_dois)}] opencite cite {doi} ({label}) ...",
                    file=sys.stderr,
                )
                papers, error = opencite_citing(doi, args.max_citing)
                cache[cache_key] = {"papers": papers, "error": error}
                args.cache_json.parent.mkdir(parents=True, exist_ok=True)
                args.cache_json.write_text(json.dumps(cache))
            if error:
                snap.opencite_errors += 1
                print(f"        error: {error}", file=sys.stderr)
                continue
            for p in papers:
                p_doi, p_title = paper_identifiers(p)
                if p_doi:
                    snap.opencite_dois.add(p_doi)
                if p_title:
                    snap.opencite_titles.add(p_title)
        snapshots.append(snap)

    for ds_id in ds_sample:
        print(f"\n[ds] {ds_id}", file=sys.stderr)
        process(ds_id, ds_to_dois[ds_id], is_ds=True)

    for nm_id in nm_sample:
        print(f"\n[nm] {nm_id}", file=sys.stderr)
        nm_dois = fetch_nm_source_dois(nm_id)
        process(nm_id, nm_dois, is_ds=False)

    # Write CSV.
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "dataset_id",
                "kind",
                "source_doi_count",
                "scholarly_unique_titles",
                "scholarly_doi_hits",
                "opencite_unique_titles",
                "opencite_doi_hits",
                "intersection_by_title",
                "intersection_by_doi",
                "scholarly_only",
                "opencite_only",
                "opencite_errors",
            ]
        )
        for s in snapshots:
            kind = "ds" if s.dataset_id.startswith("ds") else "nm"
            inter_titles = len(s.scholarly_titles & s.opencite_titles)
            inter_dois = len(s.scholarly_dois & s.opencite_dois)
            sch_only_titles = len(s.scholarly_titles - s.opencite_titles)
            oc_only_titles = len(s.opencite_titles - s.scholarly_titles)
            w.writerow(
                [
                    s.dataset_id,
                    kind,
                    len(s.source_dois),
                    len(s.scholarly_titles),
                    len(s.scholarly_dois),
                    len(s.opencite_titles),
                    len(s.opencite_dois),
                    inter_titles,
                    inter_dois,
                    sch_only_titles,
                    oc_only_titles,
                    s.opencite_errors,
                ]
            )

    print(f"\nWrote {args.output_csv}", file=sys.stderr)
    print(f"Cached opencite responses in {args.cache_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
