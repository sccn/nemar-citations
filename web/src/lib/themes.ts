/** Build-time loader for research themes (dashboard_data/themes/
 * comprehensive_theme_analysis.json). Empty-safe. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { findRepoPath } from "./repo";

export interface Theme {
  id: number;
  name: string;
  size: number;
  topWords: string[];
}

interface RawTheme {
  id?: number;
  name?: string;
  size?: number;
  top_words?: string[];
}

export function loadThemes(): Theme[] {
  const path = findRepoPath(join("dashboard_data", "themes", "comprehensive_theme_analysis.json"));
  if (!path) {
    return [];
  }
  try {
    const data = JSON.parse(readFileSync(path, "utf-8")) as { themes?: RawTheme[] };
    return (data.themes ?? []).map((t) => ({
      id: t.id ?? 0,
      name: t.name?.trim() || "Theme",
      size: t.size ?? 0,
      topWords: t.top_words ?? [],
    }));
  } catch (err) {
    console.warn(
      `[themes] failed to parse theme analysis: ${err instanceof Error ? err.message : err}`,
    );
    return [];
  }
}
