"""Cross-dataset citation attribution audit.

Detects the inflation failure mode where a shared anchor DOI (a methods,
standards, or umbrella paper) is listed as a citation anchor in many datasets,
so the opencite fetch attributes all of that anchor's citing papers to every
dataset that lists it. Each per-file schema looks healthy in isolation, so this
audit only surfaces the problem by working across the whole corpus.

Definitions
-----------
- A *citing paper* is one entry in ``citation_details[]``. Its identity key is
  the normalized DOI when present, else the OpenAlex id, else ``pmid:<n>``,
  else the normalized title. This mirrors the pipeline's DOI-first dedup intent
  so the unique count aligns with what a correctly-deduped corpus would hold.
- An *anchor* is the ``source_doi`` that pulled a citing paper in. An anchor's
  *spread* is the number of distinct datasets in which it appears as a
  ``source_doi`` inside ``citation_details`` (its citers were fetched and
  counted, i.e. it is a ``kept`` entry in ``metadata.anchors``).
- A *violation* is an anchor whose spread exceeds ``max_datasets_per_anchor``.
  These are the umbrella / methods anchors that anchor judgment (epic #76) is
  meant to bucket out; once judged they become ``kept=False`` in
  ``metadata.anchors`` and no longer inflate per-dataset counts.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dataset_citations.sources.doi import normalize_doi

logger = logging.getLogger(__name__)

_NO_ANCHOR = "<no-anchor>"


def _normalize_title(title: str | None) -> str:
    return " ".join((title or "").lower().split())


def _citing_key(citation: dict[str, Any]) -> str:
    """Stable identity for a citing paper, DOI-first to match dedup intent."""
    doi = citation.get("doi")
    if doi:
        return f"doi:{normalize_doi(doi)}"
    openalex_id = citation.get("openalex_id")
    if openalex_id:
        return f"openalex:{str(openalex_id).strip().lower()}"
    pmid = citation.get("pmid")
    if pmid:
        return f"pmid:{str(pmid).strip()}"
    return f"title:{_normalize_title(citation.get('title'))}"


def _anchor_key(source_doi: str | None) -> str:
    return normalize_doi(source_doi) if source_doi else _NO_ANCHOR


@dataclass
class AnchorSpread:
    """How widely a single anchor's citers are attributed across datasets."""

    anchor: str
    dataset_count: int
    total_attributed: int
    datasets: list[str]
    paper_title: str | None
    context_classified: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor": self.anchor,
            "dataset_count": self.dataset_count,
            "total_attributed": self.total_attributed,
            "datasets": self.datasets,
            "paper_title": self.paper_title,
            "context_classified": self.context_classified,
        }


@dataclass
class AttributionReport:
    """Corpus-wide attribution audit result."""

    n_files: int
    summed_citations: int
    unique_citations: int
    max_datasets_per_anchor: int
    anchor_spreads: list[AnchorSpread]
    per_dataset: dict[str, dict[str, int]]

    @property
    def inflation_ratio(self) -> float:
        if self.unique_citations == 0:
            return 0.0
        return self.summed_citations / self.unique_citations

    @property
    def violations(self) -> list[AnchorSpread]:
        return [
            a
            for a in self.anchor_spreads
            if a.anchor != _NO_ANCHOR and a.dataset_count > self.max_datasets_per_anchor
        ]

    @property
    def estimated_true_total(self) -> int:
        """Summed citations after dropping rows whose only anchor is a violation.

        A lower-bound estimate: each ``citation_details`` row carries a single
        ``source_doi`` after dedup, so a citer pulled in solely via an
        over-spread anchor is dropped. Genuine per-dataset citers (via a
        data-paper anchor) are retained.
        """
        return sum(d["cleaned"] for d in self.per_dataset.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_files": self.n_files,
            "summed_citations": self.summed_citations,
            "unique_citations": self.unique_citations,
            "inflation_ratio": round(self.inflation_ratio, 4),
            "estimated_true_total": self.estimated_true_total,
            "max_datasets_per_anchor": self.max_datasets_per_anchor,
            "n_violations": len(self.violations),
            "anchor_spreads": [a.to_dict() for a in self.anchor_spreads],
            "per_dataset": self.per_dataset,
        }


def load_corpus(citations_dir: Path) -> list[dict[str, Any]]:
    """Read every ``*_citations.json`` file in ``citations_dir``."""
    records: list[dict[str, Any]] = []
    for path in sorted(citations_dir.glob("*_citations.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable citation file %s: %s", path.name, exc)
    return records


def build_report(
    records: list[dict[str, Any]], max_datasets_per_anchor: int = 5
) -> AttributionReport:
    """Compute the attribution audit over already-loaded citation records."""
    anchor_datasets: dict[str, set[str]] = defaultdict(set)
    anchor_total: Counter[str] = Counter()
    anchor_title: dict[str, str] = {}
    anchor_context: dict[str, set[str]] = defaultdict(set)
    global_unique: set[str] = set()
    summed = 0
    per_dataset_counts: dict[str, Counter[str]] = {}

    for rec in records:
        dataset_id = rec.get("dataset_id") or "<unknown>"
        details = rec.get("citation_details") or []
        summed += len(details)

        counts: Counter[str] = Counter()
        for citation in details:
            global_unique.add(_citing_key(citation))
            akey = _anchor_key(citation.get("source_doi"))
            anchor_datasets[akey].add(dataset_id)
            anchor_total[akey] += 1
            counts[akey] += 1
        per_dataset_counts[dataset_id] = counts

        # anchors[] carry each anchor's own paper title; the kept=False subset is
        # what judgment buckets out (informational columns). Schema v2.1 replaced
        # context_anchors[] with anchors[] (the kept=False entries are the old
        # context anchors).
        meta = rec.get("metadata") or {}
        for anc in meta.get("anchors") or []:
            if anc.get("kept"):
                continue
            identifier = anc.get("identifier")
            if not identifier:
                continue
            ckey = _anchor_key(identifier)
            anchor_context[ckey].add(dataset_id)
            if ckey not in anchor_title and anc.get("paper_title"):
                anchor_title[ckey] = anc["paper_title"]

    spreads = [
        AnchorSpread(
            anchor=akey,
            dataset_count=len(datasets),
            total_attributed=anchor_total[akey],
            datasets=sorted(datasets),
            paper_title=anchor_title.get(akey),
            context_classified=len(anchor_context.get(akey, set())),
        )
        for akey, datasets in anchor_datasets.items()
    ]
    spreads.sort(key=lambda a: (a.dataset_count, a.total_attributed), reverse=True)

    violation_anchors = {
        a.anchor
        for a in spreads
        if a.anchor != _NO_ANCHOR and a.dataset_count > max_datasets_per_anchor
    }

    per_dataset: dict[str, dict[str, int]] = {}
    for dataset_id, counts in per_dataset_counts.items():
        per_dataset[dataset_id] = {
            "summed": sum(counts.values()),
            "cleaned": sum(n for a, n in counts.items() if a not in violation_anchors),
        }

    return AttributionReport(
        n_files=len(records),
        summed_citations=summed,
        unique_citations=len(global_unique),
        max_datasets_per_anchor=max_datasets_per_anchor,
        anchor_spreads=spreads,
        per_dataset=per_dataset,
    )


def format_text(report: AttributionReport, top: int = 20) -> str:
    """Human-readable console summary."""
    lines = [
        "=== CITATION ATTRIBUTION AUDIT ===",
        f"Files:             {report.n_files}",
        f"Summed citations:  {report.summed_citations}",
        f"Unique citations:  {report.unique_citations}",
        f"Inflation ratio:   {report.inflation_ratio:.2f}x",
        f"Est. true total:   {report.estimated_true_total} "
        f"(after dropping {len(report.violations)} over-spread anchors)",
        f"Threshold:         > {report.max_datasets_per_anchor} datasets per anchor",
        f"Violations:        {len(report.violations)} anchors exceed the threshold",
        "",
        f"Top {min(top, len(report.anchor_spreads))} anchors by dataset spread "
        "(! = violation, ctx = datasets that bucket it as context):",
        f"  {'#ds':>4} {'attr':>6} {'ctx':>4}  anchor / title",
    ]
    for anchor in report.anchor_spreads[:top]:
        flag = "!" if anchor in report.violations else " "
        title = (anchor.paper_title or "")[:48]
        lines.append(
            f" {flag}{anchor.dataset_count:>4} {anchor.total_attributed:>6} "
            f"{anchor.context_classified:>4}  {anchor.anchor}  {title}"
        )
    return "\n".join(lines)


def format_markdown(report: AttributionReport, top: int = 20) -> str:
    """Markdown report suitable for a PR comment or artifact."""
    lines = [
        "# Citation attribution audit",
        "",
        f"- Files: **{report.n_files}**",
        f"- Summed citations: **{report.summed_citations}**",
        f"- Globally unique citations: **{report.unique_citations}**",
        f"- Inflation ratio: **{report.inflation_ratio:.2f}x**",
        f"- Estimated true total: **{report.estimated_true_total}**",
        f"- Violations (> {report.max_datasets_per_anchor} datasets/anchor): "
        f"**{len(report.violations)}**",
        "",
        f"## Top {min(top, len(report.anchor_spreads))} anchors by dataset spread",
        "",
        "| ! | datasets | attributed | context | anchor | title |",
        "|---|---|---|---|---|---|",
    ]
    violations = set(report.violations)
    for anchor in report.anchor_spreads[:top]:
        flag = "x" if anchor in violations else ""
        title = (anchor.paper_title or "").replace("|", "/")[:60]
        lines.append(
            f"| {flag} | {anchor.dataset_count} | {anchor.total_attributed} | "
            f"{anchor.context_classified} | `{anchor.anchor}` | {title} |"
        )
    return "\n".join(lines)


def run_audit(
    citations_dir: Path,
    max_datasets_per_anchor: int = 5,
    top: int = 20,
    report_json: Path | None = None,
    report_md: Path | None = None,
) -> AttributionReport:
    """Load the corpus, build the report, write optional artifacts, log summary."""
    if not citations_dir.exists():
        raise FileNotFoundError(f"Citations directory not found: {citations_dir}")

    records = load_corpus(citations_dir)
    report = build_report(records, max_datasets_per_anchor=max_datasets_per_anchor)

    print(format_text(report, top=top))

    if report_json is not None:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        logger.info("Wrote JSON report to %s", report_json)
    if report_md is not None:
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text(format_markdown(report, top=top), encoding="utf-8")
        logger.info("Wrote Markdown report to %s", report_md)

    return report
