#!/usr/bin/env python3
"""Phase 1 deliverable: extract DOIs from legacy OpenNeuro dataset_description.json.

For each ds*_citations.json under citations/json/, fetches
OpenNeuroDatasets/<id>/dataset_description.json from GitHub and parses DOIs
from HowToAcknowledge, ReferencesAndLinks, and DatasetDOI.

Output:
    .context/phase1_ds_dois.csv  - rows: dataset_id, doi, source_field

Usage:
    uv run scripts/phase1_doi_extract.py [--limit N] [--citations-dir DIR]
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:\w]+", re.IGNORECASE)
PMID_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)|pubmed/(\d+)", re.IGNORECASE)


@dataclass
class DoiRecord:
    dataset_id: str
    doi: str
    source_field: str  # HowToAcknowledge | ReferencesAndLinks | DatasetDOI


def gh_api(path: str) -> dict | list | None:
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "Not Found" in result.stderr or '"status":"404"' in result.stdout:
        return None
    raise RuntimeError(f"gh api {path} failed: {result.stderr.strip()}")


def fetch_description(dataset_id: str) -> dict | None:
    """Fetch dataset_description.json from OpenNeuroDatasets/<id> via gh api."""
    try:
        resp = gh_api(
            f"repos/OpenNeuroDatasets/{dataset_id}/contents/dataset_description.json"
        )
    except RuntimeError:
        return None
    if not isinstance(resp, dict):
        return None
    content = resp.get("content")
    encoding = resp.get("encoding")
    if not content or encoding != "base64":
        return None
    try:
        raw = base64.b64decode(content).decode("utf-8", errors="replace")
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None


def normalize_doi(s: str) -> str:
    s = s.strip()
    s = s.removeprefix("doi:").removeprefix("DOI:").strip()
    s = s.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    s = s.removeprefix("https://dx.doi.org/").removeprefix("http://dx.doi.org/")
    return s.strip().rstrip(".,;")


def extract_dois_from_value(value, source_field: str) -> list[tuple[str, str]]:
    """Return list of (doi, source_field) from any string/list/dict value."""
    out: list[tuple[str, str]] = []
    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(extract_dois_from_value(item, source_field))
        return out
    if isinstance(value, dict):
        for v in value.values():
            out.extend(extract_dois_from_value(v, source_field))
        return out
    if not isinstance(value, str):
        return out
    # If the whole string looks like a bare DOI, take it.
    cleaned = normalize_doi(value)
    if DOI_RE.fullmatch(cleaned):
        out.append((cleaned, source_field))
        return out
    # Otherwise scan for embedded DOI patterns.
    for match in DOI_RE.finditer(value):
        out.append((normalize_doi(match.group(0)), source_field))
    # Capture PMIDs too — useful later for ID-set normalization.
    for match in PMID_RE.finditer(value):
        pmid = match.group(1) or match.group(2)
        if pmid:
            out.append((f"pmid:{pmid}", source_field))
    return out


def extract_records(dataset_id: str, desc: dict) -> list[DoiRecord]:
    records: list[DoiRecord] = []
    seen: set[tuple[str, str]] = set()
    for field_name in ("DatasetDOI", "HowToAcknowledge", "ReferencesAndLinks"):
        for doi, source in extract_dois_from_value(desc.get(field_name), field_name):
            key = (doi.lower(), source)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                DoiRecord(dataset_id=dataset_id, doi=doi, source_field=source)
            )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json"),
        help="Directory of <id>_citations.json files",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Cap datasets processed"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".context/phase1_ds_dois.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    if not args.citations_dir.exists():
        print(f"citations dir not found: {args.citations_dir}", file=sys.stderr)
        return 1

    dataset_ids = sorted(
        p.name.removesuffix("_citations.json")
        for p in args.citations_dir.glob("ds*_citations.json")
    )
    if args.limit:
        dataset_ids = dataset_ids[: args.limit]

    print(f"Processing {len(dataset_ids)} ds-datasets...", file=sys.stderr)

    all_records: list[DoiRecord] = []
    no_desc: list[str] = []
    no_doi: list[str] = []

    for i, ds_id in enumerate(dataset_ids, 1):
        desc = fetch_description(ds_id)
        if desc is None:
            no_desc.append(ds_id)
            marker = "?"
        else:
            recs = extract_records(ds_id, desc)
            if not recs:
                no_doi.append(ds_id)
                marker = "-"
            else:
                all_records.extend(recs)
                marker = "+"
        if i % 25 == 0 or i == len(dataset_ids):
            print(
                f"  [{i}/{len(dataset_ids)}] {marker} {ds_id} "
                f"(records so far: {len(all_records)})",
                file=sys.stderr,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dataset_id", "doi", "source_field"])
        for r in all_records:
            writer.writerow([r.dataset_id, r.doi, r.source_field])

    print(file=sys.stderr)
    print(f"Wrote {args.output}", file=sys.stderr)
    print(f"  total DOI/PMID records: {len(all_records)}", file=sys.stderr)
    print(
        f"  datasets with at least one DOI: {len(set(r.dataset_id for r in all_records))}",
        file=sys.stderr,
    )
    print(
        f"  datasets without dataset_description.json: {len(no_desc)}", file=sys.stderr
    )
    print(
        f"  datasets with description but no DOI found: {len(no_doi)}", file=sys.stderr
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
