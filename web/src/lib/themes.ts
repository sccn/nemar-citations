/** Build-time loader for research themes (dashboard_data/themes/
 * comprehensive_theme_analysis.json). Empty-safe. */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { findRepoPath } from "./repo";

export interface Theme {
  id: number;
  name: string;
  size: number;
  topWords: string[];
  /** Public path to the matplotlib wordcloud PNG (copied into public/themes/
   * by scripts/copy-theme-assets.mjs), or null when the source PNG is absent. */
  wordcloud: string | null;
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
  const themesDir = dirname(path);
  try {
    const data = JSON.parse(readFileSync(path, "utf-8")) as { themes?: RawTheme[] };
    return (data.themes ?? []).map((t) => {
      const id = t.id ?? 0;
      const png = `theme_${id}_wordcloud.png`;
      return {
        id,
        name: t.name?.trim() || "Theme",
        size: t.size ?? 0,
        topWords: t.top_words ?? [],
        wordcloud: existsSync(join(themesDir, png)) ? png : null,
      };
    });
  } catch (err) {
    console.warn(
      `[themes] failed to parse theme analysis: ${err instanceof Error ? err.message : err}`,
    );
    return [];
  }
}
