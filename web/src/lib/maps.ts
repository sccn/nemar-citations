/**
 * Build-time loader for the UMAP map points produced by
 * `dataset-citations-export-umap-points` (dashboard_data/umap_points.json).
 * Points carry real labels (dataset names, citation titles) joined by ID, so
 * the maps are not the by-index fabrication of the old dashboard (#116).
 * Maps are an enhancement: a missing file degrades to an empty map, it does not
 * fail the build.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";

export interface DatasetPoint {
  id: string;
  x: number;
  y: number;
  name: string;
  count: number;
}

export interface CitationPoint {
  id: string;
  x: number;
  y: number;
  title: string;
}

export interface UmapPoints {
  datasets: DatasetPoint[];
  citations: CitationPoint[];
}

function findFile(rel: string): string | null {
  let dir = process.cwd();
  for (let depth = 0; depth < 8; depth++) {
    const candidate = join(dir, rel);
    if (existsSync(candidate)) {
      return candidate;
    }
    const parent = dirname(dir);
    if (parent === dir) {
      break;
    }
    dir = parent;
  }
  return null;
}

export function loadUmapPoints(): UmapPoints {
  const empty: UmapPoints = { datasets: [], citations: [] };
  const path = findFile(join("dashboard_data", "umap_points.json"));
  if (!path) {
    return empty;
  }
  try {
    const data = JSON.parse(readFileSync(path, "utf-8")) as Partial<UmapPoints>;
    return { datasets: data.datasets ?? [], citations: data.citations ?? [] };
  } catch (err) {
    console.warn(
      `[maps] failed to parse umap_points.json: ${err instanceof Error ? err.message : err}`,
    );
    return empty;
  }
}
