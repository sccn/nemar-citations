/** Build-time loader for the temporal series (dashboard_data/temporal/
 * temporal_summary.csv: year, total_citations, high_confidence_citations,
 * unique_datasets). Returns rows sorted by year with a cumulative
 * high-confidence total. Empty-safe. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { findRepoPath } from "./repo";

export interface YearPoint {
  year: number;
  total: number;
  highConf: number;
  datasets: number;
  cumulativeHighConf: number;
}

export function loadTemporal(): YearPoint[] {
  const path = findRepoPath(join("dashboard_data", "temporal", "temporal_summary.csv"));
  if (!path) {
    return [];
  }
  try {
    const lines = readFileSync(path, "utf-8").trim().split("\n");
    if (lines.length < 2) {
      return [];
    }
    const header = lines[0].split(",").map((h) => h.trim());
    const col = (name: string) => header.indexOf(name);
    const yi = col("year");
    const ti = col("total_citations");
    const hi = col("high_confidence_citations");
    const di = col("unique_datasets");
    if (yi < 0 || ti < 0) {
      console.warn(`[temporal] CSV missing required columns; header=${header.join(",")}`);
      return [];
    }

    const rows = lines
      .slice(1)
      .map((line) => {
        const c = line.split(",");
        return {
          year: Number(c[yi]),
          total: Number(c[ti]) || 0,
          highConf: hi >= 0 ? Number(c[hi]) || 0 : 0,
          datasets: di >= 0 ? Number(c[di]) || 0 : 0,
        };
      })
      .filter((r) => Number.isFinite(r.year) && r.year > 0)
      .sort((a, b) => a.year - b.year);

    let cumulative = 0;
    return rows.map((r) => {
      cumulative += r.highConf;
      return { ...r, cumulativeHighConf: cumulative };
    });
  } catch (err) {
    console.warn(
      `[temporal] failed to parse temporal CSV: ${err instanceof Error ? err.message : err}`,
    );
    return [];
  }
}
