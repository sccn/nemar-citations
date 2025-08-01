"""Temporal analysis functions for dataset citations."""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from pydantic import ValidationError

from .schemas import CitationCitedInYear

logger = logging.getLogger(__name__)


def extract_years_from_citations(citation_file: Path) -> List[int]:
    """
    Extract publication years from a dataset citation JSON file.

    Args:
        citation_file: Path to the dataset citations JSON file

    Returns:
        List of publication years from citation_details

    Raises:
        FileNotFoundError: If citation file doesn't exist
        ValueError: If JSON structure is invalid
    """
    if not citation_file.exists():
        raise FileNotFoundError(f"Citation file not found: {citation_file}")

    try:
        with open(citation_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {citation_file}: {e}")

    years = []
    citation_details = data.get("citation_details", [])

    for citation in citation_details:
        year = citation.get("year")
        if year and isinstance(year, int) and 1900 <= year <= 2030:
            years.append(year)
        elif year:
            # Try to parse string years
            try:
                year_int = int(str(year).strip())
                if 1900 <= year_int <= 2030:
                    years.append(year_int)
            except (ValueError, TypeError):
                logger.warning(f"Invalid year format in {citation_file}: {year}")

    return years


def analyze_citation_timeline(
    citations_dir: Path, confidence_threshold: float = 0.4
) -> Dict:
    """
    Analyze citation timeline across all datasets.

    Args:
        citations_dir: Directory containing citation JSON files
        confidence_threshold: Minimum confidence score to include citations

    Returns:
        Dictionary with temporal analysis results
    """
    timeline_data = {
        "datasets": {},
        "yearly_totals": defaultdict(int),
        "cumulative_totals": defaultdict(int),
        "dataset_first_citations": {},
        "dataset_last_citations": {},
        "high_confidence_yearly": defaultdict(int),
    }

    json_files = list(citations_dir.glob("*.json"))
    logger.info(f"Processing {len(json_files)} citation files...")

    for json_file in json_files:
        dataset_id = json_file.stem.replace("_citations", "")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])
            dataset_years = []
            high_confidence_years = []

            for citation in citation_details:
                year = citation.get("year")
                # Extract confidence score from nested structure
                confidence_data = citation.get("confidence_scoring", {})
                confidence = confidence_data.get("confidence_score", 0.0)

                # Validate year
                if year and isinstance(year, int) and 1900 <= year <= 2030:
                    dataset_years.append(year)
                    timeline_data["yearly_totals"][year] += 1

                    # Track high confidence citations
                    if confidence >= confidence_threshold:
                        high_confidence_years.append(year)
                        timeline_data["high_confidence_yearly"][year] += 1

            if dataset_years:
                timeline_data["datasets"][dataset_id] = {
                    "years": sorted(dataset_years),
                    "high_confidence_years": sorted(high_confidence_years),
                    "first_year": min(dataset_years),
                    "last_year": max(dataset_years),
                    "total_citations": len(dataset_years),
                    "high_confidence_citations": len(high_confidence_years),
                    "num_citations": data.get("num_citations", 0),
                    "total_cumulative_citations": data.get(
                        "total_cumulative_citations", 0
                    ),
                }

                timeline_data["dataset_first_citations"][dataset_id] = min(
                    dataset_years
                )
                timeline_data["dataset_last_citations"][dataset_id] = max(dataset_years)

        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            continue

    # Calculate cumulative totals
    years = sorted(timeline_data["yearly_totals"].keys())
    cumulative = 0
    for year in years:
        cumulative += timeline_data["yearly_totals"][year]
        timeline_data["cumulative_totals"][year] = cumulative

    logger.info(f"Processed {len(timeline_data['datasets'])} datasets")
    logger.info(
        f"Year range: {min(years) if years else 'N/A'} - {max(years) if years else 'N/A'}"
    )

    return dict(timeline_data)


def create_temporal_summary(timeline_data: Dict) -> pd.DataFrame:
    """
    Create a summary DataFrame for temporal analysis.

    Args:
        timeline_data: Results from analyze_citation_timeline()

    Returns:
        DataFrame with yearly citation statistics
    """
    if not timeline_data["yearly_totals"]:
        return pd.DataFrame()

    years = sorted(timeline_data["yearly_totals"].keys())

    summary_data = []
    for year in years:
        row = {
            "year": year,
            "total_citations": timeline_data["yearly_totals"][year],
            "cumulative_citations": timeline_data["cumulative_totals"][year],
            "high_confidence_citations": timeline_data["high_confidence_yearly"][year],
            "datasets_with_citations": sum(
                1
                for dataset_data in timeline_data["datasets"].values()
                if year in dataset_data["years"]
            ),
        }
        summary_data.append(row)

    return pd.DataFrame(summary_data)


def get_dataset_temporal_stats(timeline_data: Dict, dataset_id: str) -> Optional[Dict]:
    """
    Get temporal statistics for a specific dataset.

    Args:
        timeline_data: Results from analyze_citation_timeline()
        dataset_id: Dataset identifier (e.g., 'ds000117')

    Returns:
        Dictionary with dataset temporal statistics or None if not found
    """
    return timeline_data["datasets"].get(dataset_id)


def create_citation_year_relationships(
    citations_dir: Path, confidence_threshold: float = 0.4
) -> List[CitationCitedInYear]:
    """
    Create Citation-Year relationship objects for Neo4j loading.

    Args:
        citations_dir: Directory containing citation JSON files
        confidence_threshold: Minimum confidence score to include citations

    Returns:
        List of CitationCitedInYear relationship objects
    """
    relationships = []

    json_files = list(citations_dir.glob("*.json"))

    for json_file in json_files:
        dataset_id = json_file.stem.replace("_citations", "")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            citation_details = data.get("citation_details", [])

            for i, citation in enumerate(citation_details):
                year = citation.get("year")
                # Extract confidence score from nested structure
                confidence_data = citation.get("confidence_scoring", {})
                confidence = confidence_data.get("confidence_score", 0.0)

                # Only include high-confidence citations
                if confidence < confidence_threshold:
                    continue

                if year and isinstance(year, int) and 1900 <= year <= 2030:
                    citation_uid = f"{dataset_id}_citation_{i}"

                    try:
                        relationship = CitationCitedInYear(
                            citation_uid=citation_uid, year_value=year
                        )
                        relationships.append(relationship)
                    except ValidationError as e:
                        logger.warning(f"Invalid relationship data: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            continue

    logger.info(f"Created {len(relationships)} citation-year relationships")
    return relationships
