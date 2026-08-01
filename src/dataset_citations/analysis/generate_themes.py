"""Generate theme analysis with wordclouds from citation data."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

# Non-interactive backend: the nightly pipeline runs headless on hallu, so
# savefig must not require a display. Set before importing pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from wordcloud import WordCloud


def generate_themes(citations_dir: Path, output_dir: Path):
    """Generate theme wordclouds from citation titles."""

    # Collect all high-confidence citation titles
    citation_texts_by_theme = defaultdict(list)

    for json_file in citations_dir.glob("*.json"):
        with open(json_file) as f:
            data = json.load(f)
            citations = data.get("citation_details", [])

            for citation in citations:
                # Get confidence score from nested structure
                confidence_data = citation.get("confidence_scoring", {})
                confidence = confidence_data.get(
                    "confidence_score", citation.get("confidence_score", 0)
                )

                if confidence >= 0.4:
                    title = citation.get("title", "")
                    if title:
                        # Simple theme assignment based on keywords
                        title_lower = title.lower()
                        if any(
                            term in title_lower
                            for term in ["eeg", "erp", "electrode", "brain"]
                        ):
                            citation_texts_by_theme["core_eeg"].append(title)
                        elif any(
                            term in title_lower
                            for term in ["audio", "sound", "music", "hearing"]
                        ):
                            citation_texts_by_theme["audio"].append(title)
                        elif any(
                            term in title_lower
                            for term in ["task", "cognitive", "memory", "attention"]
                        ):
                            citation_texts_by_theme["cognitive"].append(title)
                        elif any(
                            term in title_lower
                            for term in ["method", "analysis", "algorithm", "model"]
                        ):
                            citation_texts_by_theme["methods"].append(title)
                        else:
                            citation_texts_by_theme["general"].append(title)

    # Generate wordclouds for each theme
    output_dir.mkdir(parents=True, exist_ok=True)

    theme_names = {
        "core_eeg": "Core EEG",
        "audio": "Audio & Stimulation",
        "cognitive": "Task Performance",
        "methods": "Advanced Methods",
        "general": "General Research",
    }

    theme_data = {"themes": []}
    theme_id = 0

    for theme_key, texts in citation_texts_by_theme.items():
        if texts and theme_id < 4:  # Limit to 4 themes
            # Combine texts for wordcloud
            combined_text = " ".join(texts)

            # Generate wordcloud
            wordcloud = WordCloud(
                width=800, height=400, background_color="white", max_words=50
            ).generate(combined_text)

            # Save wordcloud
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation="bilinear")
            plt.axis("off")
            plt.title(theme_names.get(theme_key, theme_key))
            plt.tight_layout()
            plt.savefig(
                output_dir / f"theme_{theme_id}_wordcloud.png",
                dpi=100,
                bbox_inches="tight",
            )
            plt.close()

            # Add to theme data
            theme_data["themes"].append(
                {
                    "id": theme_id,
                    "name": theme_names.get(theme_key, theme_key),
                    "size": len(texts),
                    "top_words": (
                        list(wordcloud.words_.keys())[:10] if wordcloud.words_ else []
                    ),
                }
            )

            print(
                f"Generated wordcloud for {theme_names.get(theme_key, theme_key)}: {len(texts)} citations"
            )
            theme_id += 1

    # Save theme analysis
    with open(output_dir / "comprehensive_theme_analysis.json", "w") as f:
        json.dump(theme_data, f, indent=2)

    print(f"Theme analysis complete: {len(theme_data['themes'])} themes generated")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate theme analysis with wordclouds"
    )
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json_opencite"),
        help="Directory containing citation JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dashboard_data/themes"),
        help="Output directory for theme analysis",
    )

    args = parser.parse_args()

    if not args.citations_dir.exists():
        print(f"Error: Citations directory {args.citations_dir} not found")
        sys.exit(1)

    generate_themes(args.citations_dir, args.output_dir)
