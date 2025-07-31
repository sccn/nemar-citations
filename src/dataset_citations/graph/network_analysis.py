"""Network analysis functions for dataset citations and author collaboration."""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def find_multi_dataset_citations(
    citations_dir: Path, confidence_threshold: float = 0.4
) -> Dict[str, List[str]]:
    """
    Find citations that appear across multiple datasets (shared citations).

    Args:
        citations_dir: Directory containing dataset citation JSON files
        confidence_threshold: Minimum confidence score for citations

    Returns:
        Dictionary mapping citation titles to list of dataset IDs that cite them

    Raises:
        FileNotFoundError: If citations directory doesn't exist
    """
    if not citations_dir.exists():
        raise FileNotFoundError(f"Citations directory not found: {citations_dir}")

    # Track citations across datasets
    citation_to_datasets = defaultdict(list)

    json_files = list(citations_dir.glob("*_citations.json"))
    logger.info(
        f"Analyzing {len(json_files)} citation files for multi-dataset citations"
    )

    for citation_file in json_files:
        try:
            dataset_id = citation_file.stem.replace("_citations", "")

            with open(citation_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])

            for citation in citation_details:
                # Check confidence score
                confidence_scoring = citation.get("confidence_scoring", {})
                confidence = confidence_scoring.get("confidence_score", 0.0)

                if confidence < confidence_threshold:
                    continue

                title = citation.get("title", "").strip()
                if title:
                    citation_to_datasets[title].append(dataset_id)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing {citation_file}: {e}")
            continue

    # Filter to only multi-dataset citations
    multi_dataset_citations = {
        title: datasets
        for title, datasets in citation_to_datasets.items()
        if len(datasets) > 1
    }

    logger.info(
        f"Found {len(multi_dataset_citations)} citations that appear across multiple datasets"
    )
    return multi_dataset_citations


def analyze_dataset_co_citations(
    multi_dataset_citations: Dict[str, List[str]],
) -> pd.DataFrame:
    """
    Analyze which datasets are commonly co-cited together.

    Args:
        multi_dataset_citations: Dict mapping citation titles to dataset lists

    Returns:
        DataFrame with dataset pairs and their co-citation frequency
    """
    co_citation_counts = defaultdict(int)

    for citation_title, datasets in multi_dataset_citations.items():
        # Create all pairwise combinations of datasets
        for i in range(len(datasets)):
            for j in range(i + 1, len(datasets)):
                dataset_pair = tuple(sorted([datasets[i], datasets[j]]))
                co_citation_counts[dataset_pair] += 1

    # Convert to DataFrame
    co_citation_data = []
    for (dataset1, dataset2), count in co_citation_counts.items():
        co_citation_data.append(
            {
                "dataset1": dataset1,
                "dataset2": dataset2,
                "co_citation_count": count,
                "shared_citations": count,  # Same value, but clearer naming
            }
        )

    df = pd.DataFrame(co_citation_data)
    if not df.empty:
        df = df.sort_values("co_citation_count", ascending=False)

    logger.info(f"Generated co-citation matrix with {len(df)} dataset pairs")
    return df


def extract_author_networks(
    citations_dir: Path, datasets_dir: Path, confidence_threshold: float = 0.4
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Extract author networks from datasets and citations.

    Args:
        citations_dir: Directory containing citation JSON files
        datasets_dir: Directory containing dataset JSON files
        confidence_threshold: Minimum confidence score for citations

    Returns:
        Tuple of (dataset_authors, citation_authors) dictionaries
        dataset_authors: {dataset_id: [author_names]}
        citation_authors: {dataset_id: [citation_author_names]}
    """
    dataset_authors = {}
    citation_authors = defaultdict(list)

    # Extract dataset authors
    dataset_files = list(datasets_dir.glob("*_datasets.json"))
    logger.info(f"Extracting authors from {len(dataset_files)} dataset files")

    for dataset_file in dataset_files:
        try:
            dataset_id = dataset_file.stem.replace("_datasets", "")

            with open(dataset_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            authors = data.get("Authors", [])
            if authors:
                dataset_authors[dataset_id] = authors

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing dataset file {dataset_file}: {e}")
            continue

    # Extract citation authors
    citation_files = list(citations_dir.glob("*_citations.json"))
    logger.info(
        f"Extracting citation authors from {len(citation_files)} citation files"
    )

    for citation_file in citation_files:
        try:
            dataset_id = citation_file.stem.replace("_citations", "")

            with open(citation_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])

            for citation in citation_details:
                # Check confidence score
                confidence_scoring = citation.get("confidence_scoring", {})
                confidence = confidence_scoring.get("confidence_score", 0.0)

                if confidence < confidence_threshold:
                    continue

                author = citation.get("author", "")
                if author:
                    citation_authors[dataset_id].append(author)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing citation file {citation_file}: {e}")
            continue

    logger.info(
        f"Extracted authors from {len(dataset_authors)} datasets and {len(citation_authors)} citation sets"
    )
    return dataset_authors, dict(citation_authors)


def find_author_overlaps(
    dataset_authors: Dict[str, List[str]], citation_authors: Dict[str, List[str]]
) -> pd.DataFrame:
    """
    Find overlaps between dataset authors and citation authors.

    Args:
        dataset_authors: {dataset_id: [author_names]}
        citation_authors: {dataset_id: [citation_author_names]}

    Returns:
        DataFrame with author overlap analysis
    """
    overlap_data = []

    for dataset_id in dataset_authors.keys():
        if dataset_id not in citation_authors:
            continue

        dataset_author_set = set(dataset_authors[dataset_id])
        citation_author_set = set(citation_authors[dataset_id])

        # Find overlapping authors
        overlapping_authors = dataset_author_set.intersection(citation_author_set)

        if overlapping_authors:
            for author in overlapping_authors:
                overlap_data.append(
                    {
                        "dataset_id": dataset_id,
                        "author": author,
                        "author_type": "dataset_creator_and_citation_author",
                        "overlap_count": 1,
                    }
                )

    df = pd.DataFrame(overlap_data)
    if not df.empty:
        # Aggregate by author to see which authors appear across multiple datasets
        author_summary = (
            df.groupby("author")
            .agg({"dataset_id": "count", "overlap_count": "sum"})
            .rename(columns={"dataset_id": "datasets_involved"})
        )
        author_summary = author_summary.sort_values(
            "datasets_involved", ascending=False
        )

        logger.info(
            f"Found {len(author_summary)} authors with dataset-citation overlaps"
        )
        return author_summary

    logger.info(
        "No author overlaps found between dataset creators and citation authors"
    )
    return df


def analyze_citation_impact(
    citations_dir: Path, confidence_threshold: float = 0.4
) -> pd.DataFrame:
    """
    Analyze citation impact using cited_by counts.

    Args:
        citations_dir: Directory containing citation JSON files
        confidence_threshold: Minimum confidence score for citations

    Returns:
        DataFrame with citation impact analysis
    """
    impact_data = []

    json_files = list(citations_dir.glob("*_citations.json"))
    logger.info(f"Analyzing citation impact from {len(json_files)} files")

    for citation_file in json_files:
        try:
            dataset_id = citation_file.stem.replace("_citations", "")

            with open(citation_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])

            for citation in citation_details:
                # Check confidence score
                confidence_scoring = citation.get("confidence_scoring", {})
                confidence = confidence_scoring.get("confidence_score", 0.0)

                if confidence < confidence_threshold:
                    continue

                title = citation.get("title", "")
                author = citation.get("author", "")
                year = citation.get("year")
                cited_by = citation.get("cited_by", 0)
                venue = citation.get("venue", "")

                impact_data.append(
                    {
                        "dataset_id": dataset_id,
                        "title": title,
                        "author": author,
                        "year": year,
                        "cited_by": cited_by,
                        "confidence_score": confidence,
                        "venue": venue,
                    }
                )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing {citation_file}: {e}")
            continue

    df = pd.DataFrame(impact_data)
    if not df.empty:
        df = df.sort_values("cited_by", ascending=False)

    logger.info(f"Generated impact analysis for {len(df)} citations")
    return df
