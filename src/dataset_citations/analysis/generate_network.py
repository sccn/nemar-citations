#!/usr/bin/env python
"""Generate network analysis data from citation JSON files."""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter


def generate_network(citations_dir: Path, output_dir: Path):
    """Generate network analysis CSV files from citation data."""

    # Initialize data structures
    author_datasets = defaultdict(set)
    dataset_citations = defaultdict(int)
    bridge_papers = []
    multi_dataset_citations = []

    # Process all citation files
    for json_file in citations_dir.glob("*.json"):
        dataset_id = json_file.stem.replace("_citations", "")

        with open(json_file) as f:
            data = json.load(f)
            citations = data.get("citation_details", [])
            dataset_citations[dataset_id] = len(citations)

            # Process each citation
            for citation in citations:
                # Get confidence score from nested structure
                confidence_data = citation.get("confidence_scoring", {})
                confidence = confidence_data.get(
                    "confidence_score", citation.get("confidence_score", 0)
                )

                if confidence >= 0.4:
                    # Track authors
                    author = citation.get("author", "")
                    if author and author.strip():
                        author_datasets[author].add(dataset_id)

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

    # Identify bridge papers (authors citing multiple datasets)
    for author, datasets in author_datasets.items():
        if len(datasets) > 1:
            bridge_papers.append(
                {
                    "author": author,
                    "datasets_bridged": ",".join(sorted(list(datasets))),
                    "num_datasets": len(datasets),
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
                    "datasets_cited": ",".join(sorted(list(datasets))),
                    "num_datasets": len(datasets),
                }
            )

    # Save bridge papers data
    with open(output_dir / "bridge_papers.csv", "w", newline="") as f:
        if bridge_papers:
            writer = csv.DictWriter(
                f, fieldnames=["author", "datasets_bridged", "num_datasets"]
            )
            writer.writeheader()
            writer.writerows(bridge_papers[:80])  # Top 80 bridge papers
        else:
            writer = csv.writer(f)
            writer.writerow(["author", "datasets_bridged", "num_datasets"])

    # Save dataset popularity
    with open(output_dir / "dataset_popularity.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["dataset_id", "citation_count"])
        writer.writeheader()
        for dataset_id, count in sorted(
            dataset_citations.items(), key=lambda x: x[1], reverse=True
        ):
            writer.writerow({"dataset_id": dataset_id, "citation_count": count})

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
            datasets_list = sorted(list(datasets))
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
        default=Path("citations/json"),
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
