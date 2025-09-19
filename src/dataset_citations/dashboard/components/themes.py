"""
Theme visualization component for dashboard.
"""

from typing import Any, Dict


class ThemeGenerator:
    """Generate research theme visualizations."""

    def generate_themes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate theme visualization data.

        Args:
            data: Aggregated data from DataAggregator

        Returns:
            Dictionary containing theme configurations
        """
        theme_data = data.get("theme_analysis", {}).get(
            "comprehensive_theme_analysis", {}
        )
        generated_themes = theme_data.get("themes", [])

        themes = []
        for theme in generated_themes:
            theme_id = theme.get("id", 0)
            theme_name = theme.get("name", f"Theme {theme_id + 1}")
            theme_size = theme.get("size", 0)

            themes.append(
                {
                    "id": theme_id,
                    "title": f"Theme {theme_id + 1} - {theme_name}",
                    "subtitle": f"{theme_size} citations in this cluster",
                    "wordcloud": f"data/themes/theme_{theme_id}_wordcloud.png",
                }
            )

        # Fallback if no themes are generated
        if not themes:
            themes = [
                {
                    "id": 0,
                    "title": "Theme 1",
                    "subtitle": "Themes will be generated when analysis is run",
                    "wordcloud": "data/themes/theme_0_wordcloud.png",
                }
            ]

        return {"themes": themes, "wordcloud_images": [t["wordcloud"] for t in themes]}
