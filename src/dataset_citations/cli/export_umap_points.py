"""Export UMAP 2D coordinates + real labels to JSON for the dashboard maps.

`analyze-umap` writes a Python pickle
(`embeddings/analysis/umap_projections/*_umap_2d_*.pkl`) holding `embedding_ids`
(`dataset_<id>` / `citation_<hash>`) and the 2D coordinates. The Astro dashboard
needs JS-readable coordinates joined to REAL labels so map nodes carry real
metadata rather than positional-index guesses (fixes #116):

  - dataset nodes  -> dataset name + citation count
  - citation nodes -> citation title, looked up by hash in the embedding
    registry (`embeddings/metadata/embedding_registry.json`, which stores a
    `title` per citation hash)

Writes `dashboard_data/umap_points.json`:
  {"generated_from": "<pkl>", "datasets": [{id,x,y,name,count}],
   "citations": [{id,x,y,title}]}
"""

import argparse
import json
import pickle
from pathlib import Path


def latest_pkl(projections_dir: Path) -> Path | None:
    """Newest UMAP pickle, preferring a `both_*` projection (datasets+citations)."""
    for prefer in ("both", "*"):
        cands = sorted(projections_dir.glob(f"{prefer}_umap_2d_*.pkl"))
        if cands:
            return cands[-1]
    return None


def load_registry_titles(registry_path: Path) -> dict[str, str]:
    if not registry_path.is_file():
        return {}
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    citations = reg.get("citations") or {}
    return {
        h: (v.get("title") or "").strip()
        for h, v in citations.items()
        if isinstance(v, dict)
    }


def load_dataset_meta(citations_dir: Path, datasets_dir: Path):
    names: dict[str, str] = {}
    counts: dict[str, int] = {}
    if citations_dir.is_dir():
        for f in citations_dir.glob("*_citations.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            did = d.get("dataset_id") or f.stem.replace("_citations", "")
            counts[did] = d.get("num_citations", len(d.get("citation_details", [])))
    if datasets_dir.is_dir():
        for f in datasets_dir.glob("*_datasets.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            did = d.get("dataset_id", "")
            name = ((d.get("dataset_description") or {}) or {}).get("Name")
            if did and name:
                names[did] = name.strip()
    return names, counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export UMAP coords + labels to JSON")
    parser.add_argument(
        "--projections-dir",
        type=Path,
        default=Path("embeddings/analysis/umap_projections"),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("embeddings/metadata/embedding_registry.json"),
    )
    parser.add_argument(
        "--citations-dir", type=Path, default=Path("citations/json_opencite")
    )
    parser.add_argument("--datasets-dir", type=Path, default=Path("datasets"))
    parser.add_argument(
        "--output", type=Path, default=Path("dashboard_data/umap_points.json")
    )
    args = parser.parse_args()

    pkl = latest_pkl(args.projections_dir)
    if pkl is None:
        raise SystemExit(f"No *_umap_2d_*.pkl in {args.projections_dir}")

    with open(pkl, "rb") as f:
        data = pickle.load(f)
    ids = data["embedding_ids"]
    coords = data["umap_embeddings"]

    titles = load_registry_titles(args.registry)
    names, counts = load_dataset_meta(args.citations_dir, args.datasets_dir)

    out: dict = {"generated_from": pkl.name, "datasets": [], "citations": []}
    for i, eid in enumerate(ids):
        x = round(float(coords[i][0]), 3)
        y = round(float(coords[i][1]), 3)
        if eid.startswith("dataset_"):
            did = eid[len("dataset_") :]
            out["datasets"].append(
                {
                    "id": did,
                    "x": x,
                    "y": y,
                    "name": names.get(did, did),
                    "count": counts.get(did, 0),
                }
            )
        elif eid.startswith("citation_"):
            h = eid[len("citation_") :]
            out["citations"].append(
                {"id": h, "x": x, "y": y, "title": titles.get(h, "")}
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out), encoding="utf-8")
    print(
        f"wrote {args.output}: {len(out['datasets'])} datasets, "
        f"{len(out['citations'])} citations from {pkl.name}"
    )


if __name__ == "__main__":
    main()
