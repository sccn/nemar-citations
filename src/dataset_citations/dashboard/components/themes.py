"""
Theme visualization component for dashboard.

Closes #79: renders word clouds from
`theme_analysis.comprehensive_theme_analysis.themes[]` so the Research Themes
tab actually shows the per-theme content. Previously this component only
emitted metadata + image paths, and if no upstream step had generated the
PNGs the tab rendered as four empty cards. The generator now materializes a
PNG for each theme from its `top_words` list at dashboard-build time using
the `wordcloud` library (already a runtime dependency).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


class ThemeGenerator:
    """Generate research theme visualizations."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """Initialize the theme generator.

        Args:
            output_dir: Dashboard output directory. When provided, wordcloud
                PNGs are written under `<output_dir>/data/themes/` so the
                generated HTML can reference them with a stable relative
                path (`data/themes/theme_N_wordcloud.png`).
        """
        self.output_dir = Path(output_dir) if output_dir is not None else None

    def generate_themes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate theme visualization data.

        Reads themes from
        `data["theme_analysis"]["comprehensive_theme_analysis"]["themes"]`.
        Each theme is expected to have `id`, `name`, `size`, and a non-empty
        `top_words` list (phrases). When `output_dir` was provided to
        `__init__`, this method also writes a PNG wordcloud per theme.

        Args:
            data: Aggregated data from `DataAggregator`.

        Returns:
            Dictionary with `themes` (renderable entries) and the list of
            wordcloud image paths that the HTML template references.
        """
        theme_data = data.get("theme_analysis", {}).get(
            "comprehensive_theme_analysis", {}
        )
        generated_themes = theme_data.get("themes", [])

        themes: List[Dict[str, Any]] = []
        for theme in generated_themes:
            theme_id = theme.get("id", 0)
            theme_name = theme.get("name", f"Theme {theme_id + 1}")
            theme_size = theme.get("size", 0)
            top_words = theme.get("top_words", []) or []

            # Track whether the PNG was actually produced. If rendering fails
            # (or no output_dir / empty top_words), `wordcloud` is set to None
            # so the payload doesn't advertise a non-existent asset; the
            # template's tag-cloud fallback covers the visual.
            wordcloud_path: str | None = None
            if self.output_dir is not None and top_words:
                target = self.output_dir / "data" / "themes"
                try:
                    self._render_wordcloud_png(top_words, target, theme_id)
                except Exception as exc:  # noqa: BLE001
                    # Defensive: never let a rendering failure kill the whole
                    # dashboard build. Log and leave wordcloud=None so the
                    # template renders the tag-cloud fallback only.
                    logger.warning(
                        "Failed to render wordcloud for theme %s (%s): %s",
                        theme_id,
                        theme_name,
                        exc,
                    )
                else:
                    wordcloud_path = f"data/themes/theme_{theme_id}_wordcloud.png"

            themes.append(
                {
                    "id": theme_id,
                    "title": f"Theme {theme_id + 1} - {theme_name}",
                    "subtitle": f"{theme_size} citations in this cluster",
                    "wordcloud": wordcloud_path,
                    "top_words": list(top_words),
                }
            )

        # Fallback if no themes are generated
        if not themes:
            themes = [
                {
                    "id": 0,
                    "title": "Theme 1",
                    "subtitle": "Themes will be generated when analysis is run",
                    "wordcloud": None,
                    "top_words": [],
                }
            ]

        return {
            "themes": themes,
            # Only advertise wordcloud paths that actually exist on disk;
            # None entries are dropped so the template's <img> tags don't
            # point at non-existent files.
            "wordcloud_images": [t["wordcloud"] for t in themes if t["wordcloud"]],
        }

    @staticmethod
    def _render_wordcloud_png(
        top_words: Sequence[str],
        target_dir: Path,
        theme_id: Any,
    ) -> Path:
        """Render `top_words` to a PNG using the `wordcloud` library.

        The list of phrases is fed to `WordCloud.generate_from_frequencies`
        with a decaying weight so the first phrase appears largest. This keeps
        the visual order aligned with the analysis output and avoids needing
        the raw text corpus at dashboard-build time.
        """
        # Local import keeps the dashboard module importable even in
        # environments where the heavy `wordcloud`/`matplotlib` stack is
        # unavailable (e.g., minimal smoke tests).
        from wordcloud import WordCloud

        target_dir.mkdir(parents=True, exist_ok=True)
        frequencies = _build_frequency_map(top_words)
        if not frequencies:
            raise ValueError("top_words is empty after normalization")

        cloud = WordCloud(
            width=800,
            height=400,
            background_color="white",
            max_words=len(frequencies),
        ).generate_from_frequencies(frequencies)

        path = target_dir / f"theme_{theme_id}_wordcloud.png"
        cloud.to_file(str(path))
        return path


def _build_frequency_map(top_words: Iterable[str]) -> Dict[str, float]:
    """Turn an ordered list of phrases into a frequency map.

    Earlier phrases get higher weights (linear decay) so the resulting
    wordcloud's visual prominence matches the upstream ranking.
    """
    cleaned = [w.strip() for w in top_words if isinstance(w, str) and w.strip()]
    if not cleaned:
        return {}
    n = len(cleaned)
    return {phrase: float(n - idx) for idx, phrase in enumerate(cleaned)}
