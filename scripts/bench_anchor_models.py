"""Throwaway bake-off: compare Ollama models on the anchor-classification task.

Investigation for issue #131 / epic #180. The over-attribution problem is that
gemma4:e4b (the cron model) classifies shared resource/paradigm papers (ERP CORE,
HBN-EEG) as `data_paper` for datasets that merely reuse them, so their citers
leak across many datasets. This script measures, on a small HAND-LABELED set:

  * per-model accuracy (exact 5-class + the decision-relevant data_paper-vs-not)
  * per-model latency
  * the same metrics with a deterministic relation-type prior layered on top
    (an external journal DOI linked via `References` is implausible as THIS
    dataset's data paper; downgrade a model `data_paper` call in that case).

Run against hallu's Ollama via the tunnel (per probe_anchor_judgment docstring):
    ssh -fN -L 21434:localhost:11434 hallu
    OLLAMA_BASE_URL=http://localhost:21434 \
        uv run python scripts/bench_anchor_models.py --output /tmp/bench.json

Writes no sidecars. Not part of the pipeline.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from dataset_citations.backends import OpenCiteBackend
from dataset_citations.quality.dataset_metadata import (
    DatasetMetadataRetriever,
    extract_dataset_text,
)
from dataset_citations.quality.llm_client import (
    LlmJudgmentError,
    OllamaJudgmentClient,
    build_anchor_prompt,
)
from dataset_citations.sources.models import FetchSuccess

# (dataset_id, anchor_doi, expected_class). expected_class drives both the
# exact-class score and the binary kept score (kept == data_paper).
LABELED_PAIRS: list[tuple[str, str, str]] = [
    # --- over-attribution cases: a shared resource/method paper a DIFFERENT
    #     dataset reuses; must NOT be data_paper (kept=False) ---
    (
        "on007052",
        "10.1016/j.neuroimage.2020.117465",
        "methodology",
    ),  # ERP CORE x PURSUE N400
    (
        "on007069",
        "10.1016/j.neuroimage.2020.117465",
        "methodology",
    ),  # ERP CORE x PURSUE MMN
    ("on005505", "10.1101/2024.10.03.615261", "umbrella"),  # HBN-EEG x an HBN sibling
    ("on005510", "10.1101/2024.10.03.615261", "umbrella"),  # HBN-EEG x an HBN sibling
    (
        "ds004118",
        "10.3389/fnins.2014.00155",
        "related_work",
    ),  # EEG task-perf method paper
    ("nm000163", "10.1016/j.neuroimage.2023.120446", "methodology"),  # c-VEP BCI method
    # --- controls: genuine data papers (IsDescribedBy); MUST stay data_paper ---
    (
        "on000117",
        "10.1038/sdata.2015.1",
        "data_paper",
    ),  # multimodal neuroimaging dataset
    ("on005779", "10.1016/j.brs.2024.01.001", "data_paper"),
    ("on005028", "10.1101/2022.06.24.22276882", "data_paper"),
]

DEFAULT_MODELS = ["gemma4:e4b", "gemma4:26b", "gemma4:31b", "qwen3.6:27b"]

# Relations under which an anchor is a plausible data paper for THIS dataset.
_DATA_PAPER_RELATIONS = {
    "IsDescribedBy",
    "IsSupplementTo",
    "IsVersionOf",
    "IsIdenticalTo",
}
# The dataset's own record DOIs (OpenNeuro / NEMAR) — always plausible self-anchors.
_OWN_DOI_PREFIXES = ("10.18112/openneuro.",)


def _lookup_relation(dataset_id: str, anchor_doi: str) -> str:
    """Read the source_relation for this (dataset, anchor) from the citation JSON."""
    path = Path("citations/json_opencite") / f"{dataset_id}_citations.json"
    target = anchor_doi.lower().replace("doi:", "")
    try:
        payload = json.loads(path.read_text())
    except OSError:
        return "References"
    for c in payload.get("citation_details") or []:
        if (c.get("source_doi") or "").lower().replace("doi:", "") == target:
            return c.get("source_relation") or "References"
    return "References"


def _data_paper_plausible(relation: str, anchor_doi: str) -> bool:
    """Relation-type prior: could this anchor be THIS dataset's data paper?"""
    if relation in _DATA_PAPER_RELATIONS:
        return True
    doi = anchor_doi.lower().replace("doi:", "")
    return any(doi.startswith(p) for p in _OWN_DOI_PREFIXES)


def _apply_prior(model_class: str, relation: str, anchor_doi: str) -> str:
    """Downgrade an implausible data_paper call; otherwise pass through."""
    if model_class == "data_paper" and not _data_paper_plausible(relation, anchor_doi):
        return "related_work"  # kept=False; "not this dataset's data paper"
    return model_class


def _build_cache(
    backend: OpenCiteBackend, retriever: DatasetMetadataRetriever
) -> dict[str, Any]:
    """Fetch each dataset description + anchor paper exactly once."""
    desc_cache: dict[str, str] = {}
    paper_cache: dict[str, Any] = {}
    relation: dict[tuple[str, str], str] = {}
    for ds, doi, _ in LABELED_PAIRS:
        if ds not in desc_cache:
            md = retriever.get_dataset_metadata(ds)
            desc_cache[ds] = extract_dataset_text(md)
        if doi not in paper_cache:
            res = backend.get_paper(doi)
            paper_cache[doi] = res.value if isinstance(res, FetchSuccess) else None
        relation[(ds, doi)] = _lookup_relation(ds, doi)
    return {"desc": desc_cache, "paper": paper_cache, "relation": relation}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    backend = OpenCiteBackend()
    retriever = DatasetMetadataRetriever()
    print(f"Fetching context for {len(LABELED_PAIRS)} labeled pairs (once)...")
    cache = _build_cache(backend, retriever)

    results: dict[str, Any] = {"models": {}, "pairs": []}
    for ds, doi, expected in LABELED_PAIRS:
        results["pairs"].append(
            {
                "dataset_id": ds,
                "anchor_doi": doi,
                "expected": expected,
                "relation": cache["relation"][(ds, doi)],
                "title": getattr(cache["paper"].get(doi), "title", None),
            }
        )

    for model in args.models:
        client = OllamaJudgmentClient(model=model, timeout=args.timeout)
        rows: list[dict[str, Any]] = []
        latencies: list[float] = []
        print(f"\n=== {model} ===")
        for ds, doi, expected in LABELED_PAIRS:
            paper = cache["paper"].get(doi)
            relation = cache["relation"][(ds, doi)]
            if paper is None:
                rows.append({"dataset_id": ds, "anchor_doi": doi, "error": "no_paper"})
                print(f"  [SKIP] {ds} <- {doi}: paper unresolved")
                continue
            prompt = build_anchor_prompt(
                dataset_id=ds,
                dataset_description=cache["desc"][ds],
                anchor_doi=doi,
                anchor_relation=relation,
                paper_title=paper.title,
                paper_abstract=paper.abstract,
                paper_venue=paper.venue,
                paper_authors=paper.authors,
                paper_year=paper.year,
            )
            t0 = time.perf_counter()
            try:
                judgment = client.judge_anchor(prompt)
                cls = judgment["classification"]
            except LlmJudgmentError as exc:
                rows.append(
                    {"dataset_id": ds, "anchor_doi": doi, "error": f"llm:{exc}"}
                )
                print(f"  [ERR] {ds} <- {doi}: {exc}")
                continue
            ms = (time.perf_counter() - t0) * 1000
            latencies.append(ms)
            with_prior = _apply_prior(cls, relation, doi)
            rows.append(
                {
                    "dataset_id": ds,
                    "anchor_doi": doi,
                    "expected": expected,
                    "model_class": cls,
                    "prior_class": with_prior,
                    "ms": round(ms),
                }
            )
            flag = "ok " if cls == expected else "MISS"
            pflag = "" if with_prior == cls else f" -> prior:{with_prior}"
            print(
                f"  [{flag}] {ds} <- {doi[:34]:34s} exp={expected:12s} got={cls:12s}{pflag} ({round(ms)}ms)"
            )

        scored = [r for r in rows if "model_class" in r]
        n = len(scored) or 1

        def kept(c: str) -> bool:
            return c == "data_paper"

        exact = sum(r["model_class"] == r["expected"] for r in scored)
        exact_prior = sum(r["prior_class"] == r["expected"] for r in scored)
        binacc = sum(kept(r["model_class"]) == kept(r["expected"]) for r in scored)
        binacc_prior = sum(
            kept(r["prior_class"]) == kept(r["expected"]) for r in scored
        )
        avg_ms = round(sum(latencies) / (len(latencies) or 1))
        results["models"][model] = {
            "exact_acc": round(exact / n, 2),
            "exact_acc_with_prior": round(exact_prior / n, 2),
            "kept_acc": round(binacc / n, 2),
            "kept_acc_with_prior": round(binacc_prior / n, 2),
            "avg_ms": avg_ms,
            "n_scored": len(scored),
            "rows": rows,
        }
        print(
            f"  -> exact {exact}/{n} (prior {exact_prior}/{n}) | "
            f"data_paper-binary {binacc}/{n} (prior {binacc_prior}/{n}) | avg {avg_ms}ms"
        )

    print("\n=== SUMMARY (model: exact | exact+prior | kept | kept+prior | avg ms) ===")
    for m, s in results["models"].items():
        print(
            f"  {m:14s} {s['exact_acc']:.2f} | {s['exact_acc_with_prior']:.2f} | "
            f"{s['kept_acc']:.2f} | {s['kept_acc_with_prior']:.2f} | {s['avg_ms']}ms"
        )

    if args.output:
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
