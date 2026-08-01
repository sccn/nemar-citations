"""Generate network analysis data from citation JSON files."""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def generate_network(citations_dir: Path, output_dir: Path):
    """Generate network analysis CSV files from citation data."""

    # Initialize data structures
    author_datasets = defaultdict(set)
    dataset_citations = defaultdict(int)
    bridge_papers = []
    multi_dataset_citations = []

    # Track papers (title+author) to datasets for bridge papers
    paper_to_datasets = defaultdict(lambda: {"datasets": set(), "year": None})

    # Process all citation files
    for json_file in citations_dir.glob("*.json"):
        dataset_id = json_file.stem.replace("_citations", "")

        with open(json_file) as f:
            data = json.load(f)
            citations = data.get("citation_details", [])

            # Count high and low confidence citations separately
            high_conf_count = 0
            low_conf_count = 0
            total_count = len(citations)

            # Process each citation
            for citation in citations:
                # Get confidence score from nested structure
                confidence_data = citation.get("confidence_scoring", {})
                confidence = confidence_data.get(
                    "confidence_score", citation.get("confidence_score", 0)
                )

                if confidence >= 0.4:
                    high_conf_count += 1
                else:
                    low_conf_count += 1

                if confidence >= 0.4:
                    # Track authors
                    author = citation.get("author", "")
                    if author and author.strip():
                        author_datasets[author].add(dataset_id)

                        # Track individual papers for bridge paper analysis
                        title = citation.get("title", "")
                        year = citation.get("year", "")
                        if title and title.strip():
                            # Use title+author as unique key for a paper
                            paper_key = (title.strip(), author.strip())
                            paper_to_datasets[paper_key]["datasets"].add(dataset_id)
                            paper_to_datasets[paper_key]["year"] = year

                    # Check for multi-dataset citations (simplified)
                    title = citation.get("title", "").lower()
                    if any(
                        term in title
                        for term in ["multiple", "comparison", "benchmark", "survey"]
                    ):
                        multi_dataset_citations.append(
                            {
                                "title": citation.get("title"),
                                "datasets": dataset_id,
                                "confidence": confidence,
                            }
                        )

            # Store all citation counts for this dataset
            dataset_citations[dataset_id] = {
                "high_conf": high_conf_count,
                "low_conf": low_conf_count,
                "total": total_count,
            }

    # Identify bridge papers (papers citing multiple datasets)
    for (title, author), paper_info in paper_to_datasets.items():
        if len(paper_info["datasets"]) > 1:
            bridge_papers.append(
                {
                    "title": title,
                    "author": author,
                    "year": paper_info["year"] or "",
                    "datasets_bridged": ",".join(sorted(paper_info["datasets"])),
                    "num_datasets": len(paper_info["datasets"]),
                }
            )

    # Sort bridge papers by number of datasets
    bridge_papers.sort(key=lambda x: x["num_datasets"], reverse=True)

    # Prepare output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save author influence data
    with open(output_dir / "author_influence.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["author", "datasets_cited", "num_datasets"]
        )
        writer.writeheader()
        for author, datasets in author_datasets.items():
            writer.writerow(
                {
                    "author": author,
                    "datasets_cited": ",".join(sorted(datasets)),
                    "num_datasets": len(datasets),
                }
            )

    # Save bridge papers data
    with open(output_dir / "bridge_papers.csv", "w", newline="") as f:
        if bridge_papers:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "title",
                    "author",
                    "year",
                    "datasets_bridged",
                    "num_datasets",
                ],
            )
            writer.writeheader()
            writer.writerows(bridge_papers[:80])  # Top 80 bridge papers
        else:
            writer = csv.writer(f)
            writer.writerow(
                ["title", "author", "year", "datasets_bridged", "num_datasets"]
            )

    # Save dataset popularity with high/low confidence breakdown
    with open(output_dir / "dataset_popularity.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset_id",
                "high_conf_citations",
                "low_conf_citations",
                "total_citations",
            ],
        )
        writer.writeheader()
        for dataset_id, counts in sorted(
            dataset_citations.items(), key=lambda x: x[1]["high_conf"], reverse=True
        ):
            writer.writerow(
                {
                    "dataset_id": dataset_id,
                    "high_conf_citations": counts["high_conf"],
                    "low_conf_citations": counts["low_conf"],
                    "total_citations": counts["total"],
                }
            )

    # Save multi-dataset citations
    with open(output_dir / "multi_dataset_citations.csv", "w", newline="") as f:
        if multi_dataset_citations:
            writer = csv.DictWriter(f, fieldnames=["title", "datasets", "confidence"])
            writer.writeheader()
            writer.writerows(multi_dataset_citations[:100])
        else:
            writer = csv.writer(f)
            writer.writerow(["title", "datasets", "confidence"])

    # Calculate and save dataset co-citations
    co_citation_counts = Counter()
    for author, datasets in author_datasets.items():
        if len(datasets) > 1:
            datasets_list = sorted(datasets)
            for i in range(len(datasets_list)):
                for j in range(i + 1, len(datasets_list)):
                    pair = tuple(sorted([datasets_list[i], datasets_list[j]]))
                    co_citation_counts[pair] += 1

    with open(output_dir / "dataset_co_citations.csv", "w", newline="") as f:
        if co_citation_counts:
            writer = csv.DictWriter(
                f, fieldnames=["dataset1", "dataset2", "co_citation_count"]
            )
            writer.writeheader()
            for (d1, d2), count in sorted(
                co_citation_counts.items(), key=lambda x: x[1], reverse=True
            )[:50]:
                writer.writerow(
                    {"dataset1": d1, "dataset2": d2, "co_citation_count": count}
                )
        else:
            writer = csv.writer(f)
            writer.writerow(["dataset1", "dataset2", "co_citation_count"])

    print(
        f"Generated network analysis data: {len(bridge_papers)} bridge papers identified"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate network analysis data")
    parser.add_argument(
        "--citations-dir",
        type=Path,
        default=Path("citations/json_opencite"),
        help="Directory containing citation JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dashboard_data/network"),
        help="Output directory for network analysis",
    )

    args = parser.parse_args()

    if not args.citations_dir.exists():
        print(f"Error: Citations directory {args.citations_dir} not found")
        sys.exit(1)

    generate_network(args.citations_dir, args.output_dir)
