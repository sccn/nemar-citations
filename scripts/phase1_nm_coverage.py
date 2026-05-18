#!/usr/bin/env python3
"""Phase 1 deliverable: survey .nemar/metadata.json coverage across nemarDatasets.

Enumerates nm-prefixed repos under the nemarDatasets GitHub org, checks each for
the presence of .nemar/metadata.json, and aggregates schema observations
(related_identifiers counts, relation_type / identifier_type distributions).

Output:
    .context/phase1_nm_coverage.md  - human-readable summary table

Usage:
    uv run scripts/phase1_nm_coverage.py [--limit N] [--org NAME]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoResult:
    name: str
    has_metadata: bool
    relation_type_counts: Counter = field(default_factory=Counter)
    identifier_type_counts: Counter = field(default_factory=Counter)
    related_count: int = 0
    error: str | None = None


def gh_api(path: str) -> dict | list | None:
    """Call gh api; return parsed JSON or None on 404. Raise on other errors."""
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "Not Found" in result.stderr or '"status":"404"' in result.stdout:
        return None
    raise RuntimeError(f"gh api {path} failed: {result.stderr.strip()}")


def list_nm_repos(org: str, limit: int | None) -> list[str]:
    """Return nm-prefixed repo names under the org, paginated."""
    names: list[str] = []
    page = 1
    while True:
        per_page = 100
        data = gh_api(f"orgs/{org}/repos?per_page={per_page}&page={page}")
        if not data:
            break
        chunk = [r["name"] for r in data if r["name"].startswith("nm")]
        names.extend(chunk)
        if len(data) < per_page:
            break
        if limit and len(names) >= limit:
            break
        page += 1
    if limit:
        names = names[:limit]
    return sorted(set(names))


def inspect_repo(org: str, name: str) -> RepoResult:
    """Fetch .nemar/metadata.json and tally its schema fields."""
    res = RepoResult(name=name, has_metadata=False)
    try:
        meta_file = gh_api(f"repos/{org}/{name}/contents/.nemar/metadata.json")
    except RuntimeError as e:
        res.error = str(e)
        return res
    if meta_file is None:
        return res
    if not isinstance(meta_file, dict):
        res.error = f"unexpected API response shape: {type(meta_file).__name__}"
        return res
    download_url = meta_file.get("download_url")
    if not download_url:
        res.error = "no download_url in API response"
        return res
    raw = subprocess.run(
        ["curl", "-sL", download_url], capture_output=True, text=True, check=False
    )
    if raw.returncode != 0 or not raw.stdout.strip():
        res.error = f"curl failed: {raw.stderr.strip()}"
        return res
    try:
        meta = json.loads(raw.stdout)
    except json.JSONDecodeError as e:
        res.error = f"invalid JSON: {e}"
        return res
    res.has_metadata = True
    related = meta.get("related_identifiers") or []
    res.related_count = len(related)
    for entry in related:
        rt = entry.get("relation_type", "unknown")
        it = entry.get("identifier_type", "unknown")
        res.relation_type_counts[rt] += 1
        res.identifier_type_counts[it] += 1
    return res


def render_markdown(results: list[RepoResult], org: str) -> str:
    total = len(results)
    with_meta = [r for r in results if r.has_metadata]
    coverage_pct = (len(with_meta) / total * 100) if total else 0.0

    relation_totals: Counter = Counter()
    identifier_totals: Counter = Counter()
    for r in with_meta:
        relation_totals.update(r.relation_type_counts)
        identifier_totals.update(r.identifier_type_counts)

    lines: list[str] = []
    lines.append("# Phase 1: .nemar/metadata.json coverage in nemarDatasets")
    lines.append("")
    lines.append(f"- Org surveyed: `{org}`")
    lines.append(f"- nm-prefixed repos found: **{total}**")
    lines.append(
        f"- Repos with `.nemar/metadata.json`: **{len(with_meta)}** ({coverage_pct:.1f}%)"
    )
    lines.append("")
    lines.append("## Relation type distribution (across all related_identifiers)")
    lines.append("")
    if relation_totals:
        lines.append("| relation_type | count |")
        lines.append("|---------------|------:|")
        for rt, n in relation_totals.most_common():
            lines.append(f"| {rt} | {n} |")
    else:
        lines.append("_No `.nemar/metadata.json` files observed yet._")
    lines.append("")
    lines.append("## Identifier type distribution")
    lines.append("")
    if identifier_totals:
        lines.append("| identifier_type | count |")
        lines.append("|-----------------|------:|")
        for it, n in identifier_totals.most_common():
            lines.append(f"| {it} | {n} |")
    else:
        lines.append("_No identifiers observed._")
    lines.append("")
    lines.append("## Per-repo detail (with metadata)")
    lines.append("")
    if with_meta:
        lines.append("| repo | related_count | top relation_types |")
        lines.append("|------|--------------:|--------------------|")
        for r in with_meta:
            top = ", ".join(
                f"{k}:{v}" for k, v in r.relation_type_counts.most_common(3)
            )
            lines.append(f"| {r.name} | {r.related_count} | {top} |")
    else:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## Repos checked without metadata")
    lines.append("")
    without_meta = [r.name for r in results if not r.has_metadata and not r.error]
    if without_meta:
        lines.append(
            f"{len(without_meta)} repos: "
            + ", ".join(without_meta[:20])
            + (" ..." if len(without_meta) > 20 else "")
        )
    errors = [r for r in results if r.error]
    if errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for r in errors:
            lines.append(f"- `{r.name}`: {r.error}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", default="nemarDatasets", help="GitHub org")
    parser.add_argument(
        "--limit", type=int, default=None, help="Cap number of nm repos surveyed"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".context/phase1_nm_coverage.md"),
        help="Output markdown file",
    )
    args = parser.parse_args()

    print(f"Listing nm-prefixed repos under {args.org}...", file=sys.stderr)
    names = list_nm_repos(args.org, args.limit)
    print(
        f"Found {len(names)} nm repos. Sampling .nemar/metadata.json ...",
        file=sys.stderr,
    )

    results: list[RepoResult] = []
    for i, name in enumerate(names, 1):
        res = inspect_repo(args.org, name)
        results.append(res)
        marker = "+" if res.has_metadata else "-" if not res.error else "!"
        print(f"  [{i}/{len(names)}] {marker} {name}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(results, args.org))
    print(f"\nWrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
