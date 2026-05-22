#!/usr/bin/env python3
"""
Utility functions for handling citation data in JSON format.

This module provides functions to convert citation DataFrames to structured JSON format
and handle citation data for easier downstream processing.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

import pandas as pd

logger = logging.getLogger(__name__)

DiscoveryBackend = Literal["scholarly", "opencite"]
SCHEMA_VERSION_V2 = "2.0"


def create_citation_json_structure(
    dataset_id: str, citations_df: pd.DataFrame, fetch_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Convert a pandas DataFrame of citations to a structured JSON format.

    Args:
        dataset_id (str): The dataset ID (e.g., 'ds000117')
        citations_df (pd.DataFrame): DataFrame containing citation data with columns:
                                   ['title', 'author', 'venue', 'year', 'url', 'cited_by', 'bib']
        fetch_date (datetime, optional): When the data was fetched. Defaults to current time.

    Returns:
        Dict[str, Any]: Structured citation data in JSON format with keys:
                       - dataset_id: Dataset identifier
                       - num_citations: Total number of citations
                       - date_last_updated: ISO format timestamp
                       - metadata: Additional processing information
                       - citation_details: List of citation objects
    """

    if fetch_date is None:
        fetch_date = datetime.now(timezone.utc)

    # Handle empty DataFrame
    if citations_df.empty:
        return {
            "dataset_id": dataset_id,
            "num_citations": 0,
            "date_last_updated": fetch_date.isoformat(),
            "metadata": {
                "total_cumulative_citations": 0,
                "fetch_date": fetch_date.isoformat(),
                "processing_version": "1.0",
            },
            "citation_details": [],
        }

    # Calculate metadata
    total_cumulative_citations = (
        citations_df["cited_by"].sum() if "cited_by" in citations_df.columns else 0
    )

    # Process citation details
    citation_details = []
    for _, row in citations_df.iterrows():
        # Start with main fields
        citation_obj = {
            "title": _safe_get_value(row, "title"),
            "author": _safe_get_value(row, "author"),
            "venue": _safe_get_value(row, "venue"),
            "year": _safe_get_int_value(row, "year"),
            "url": _safe_get_value(row, "url"),
            "cited_by": _safe_get_int_value(row, "cited_by"),
        }

        # Extract unique fields from bib data (avoiding duplicates)
        bib_data = row.get("bib", {})
        if isinstance(bib_data, dict):
            # Extract valuable unique fields from bib
            unique_bib_fields = {
                "abstract": _safe_get_value_from_dict(bib_data, "abstract"),
                "short_author": _safe_get_value_from_dict(bib_data, "short_author"),
                "publisher": _safe_get_value_from_dict(bib_data, "publisher"),
                "pages": _safe_get_value_from_dict(bib_data, "pages"),
                "volume": _safe_get_value_from_dict(bib_data, "volume"),
                "journal": _safe_get_value_from_dict(bib_data, "journal"),
                "pub_type": _safe_get_value_from_dict(bib_data, "pub_type"),
                "bib_id": _safe_get_value_from_dict(bib_data, "bib_id"),
            }

            # Only add fields that have meaningful values (not "n/a" or empty)
            for key, value in unique_bib_fields.items():
                if value and value != "n/a" and str(value).strip():
                    citation_obj[key] = value

        citation_details.append(citation_obj)

    # Create final structure
    json_structure = {
        "dataset_id": dataset_id,
        "num_citations": len(citations_df),
        "date_last_updated": fetch_date.isoformat(),
        "metadata": {
            "total_cumulative_citations": (
                int(total_cumulative_citations)
                if pd.notna(total_cumulative_citations)
                else 0
            ),
            "fetch_date": fetch_date.isoformat(),
            "processing_version": "1.0",
        },
        "citation_details": citation_details,
    }

    return json_structure


def add_discovery_provenance(
    citation_json: Dict[str, Any],
    *,
    discovery_backend: DiscoveryBackend,
    schema_version: str = SCHEMA_VERSION_V2,
    anchor_judgment_model: Optional[str] = None,
    context_anchors: Optional[list] = None,
) -> Dict[str, Any]:
    """Stamp a citation JSON with Phase 3 discovery-provenance markers.

    Mutates and returns the input dict. Always overwrites the top-level
    `metadata.schema_version` and `metadata.discovery_backend` keys: callers
    are explicitly declaring the schema/backend identity of this output, so
    any prior values were either stale or wrong. Per-citation
    `discovery_backend` is set only when missing (`entry.setdefault`) so the
    orchestrator can pre-populate the field with finer-grained labels in the
    future without this helper clobbering them.

    Per-citation `source_doi` and `source_relation` are NOT set here. The
    opencite orchestrator writes them per-citation while building the JSON
    because it alone knows which anchor surfaced each citing work. The
    helper is only responsible for the top-level provenance markers and the
    per-citation `discovery_backend` label.

    Phase 3 (#87) extends the schema with anchor-adjudication provenance:
      * `metadata.anchor_judgment_model` carries the LLM name from phase 2's
        sidecar (e.g. ``"gemma4:31b"``) so consumers can tell which model
        bucketed each dataset's anchors. Falsy values are normalized to
        ``None`` and persisted, since "no sidecar" is itself a meaningful
        signal for downstream code.
      * `metadata.context_anchors` is the list of non-`data_paper` anchors
        the pipeline chose NOT to fetch citations from but kept visible so
        the dashboard can render them as context. Each entry is a dict with
        at least ``anchor_identifier``, ``anchor_identifier_type``,
        ``source_relation``, ``classification``, ``reason``, and
        ``paper_title``. Phase 4 will surface these in the dashboard;
        keeping the field shape stable now lets that work land without a
        second schema change.

    The legacy scholarly path does not yet call this helper, so historical
    scholarly JSONs lack the markers (treat them as schema v1 by absence).
    Phase 4 retires the scholarly path; wiring it through here is not
    needed in the interim.
    """
    metadata = citation_json.setdefault("metadata", {})
    metadata["schema_version"] = schema_version
    metadata["discovery_backend"] = discovery_backend
    metadata["anchor_judgment_model"] = anchor_judgment_model or None
    metadata["context_anchors"] = list(context_anchors) if context_anchors else []
    for entry in citation_json.get("citation_details", []) or []:
        entry.setdefault("discovery_backend", discovery_backend)
    return citation_json


def _safe_get_value(row: pd.Series, key: str, default: str = "n/a") -> str:
    """Safely get a string value from a pandas Series row."""
    value = row.get(key, default)
    try:
        if pd.isna(value) or value is None:
            return default
    except (ValueError, TypeError):
        # Handle arrays or other complex data types
        if hasattr(value, "__iter__") and not isinstance(value, str):
            # Convert array-like objects to string representation
            value = str(value)
        elif value is None:
            return default
    return str(value).strip() if str(value).strip() else default


def _safe_get_int_value(row: pd.Series, key: str, default: int = 0) -> int:
    """Safely get an integer value from a pandas Series row."""
    value = row.get(key, default)
    if pd.isna(value) or value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_get_value_from_dict(data_dict: dict, key: str, default: str = "n/a") -> str:
    """Safely get a string value from a dictionary."""
    value = data_dict.get(key, default)
    if pd.isna(value) or value is None:
        return default
    return str(value).strip() if str(value).strip() else default


def _process_bib_data(bib_data: Any) -> Dict[str, Any]:
    """
    Process bibliographic data to ensure it's JSON serializable.

    Args:
        bib_data: Bibliographic data (could be dict, Series, or other format)

    Returns:
        Dict[str, Any]: Clean bibliographic data
    """
    if pd.isna(bib_data) or bib_data is None:
        return {}

    if isinstance(bib_data, dict):
        # Clean the dictionary
        clean_bib = {}
        for key, value in bib_data.items():
            if pd.notna(value) and value is not None:
                clean_bib[key] = str(value)
        return clean_bib

    # Handle other types by converting to string representation
    return {"raw_data": str(bib_data)}


def save_citation_json(
    dataset_id: str,
    citations_df: pd.DataFrame,
    output_dir: str,
    fetch_date: Optional[datetime] = None,
) -> str:
    """
    Save citation data as JSON file.

    Args:
        dataset_id (str): Dataset identifier
        citations_df (pd.DataFrame): Citation DataFrame
        output_dir (str): Output directory path
        fetch_date (datetime, optional): Fetch timestamp

    Returns:
        str: Path to saved JSON file

    Raises:
        IOError: If file cannot be saved
    """
    json_data = create_citation_json_structure(dataset_id, citations_df, fetch_date)

    # Create filename
    filename = f"{dataset_id}_citations.json"
    filepath = os.path.join(output_dir, filename)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save JSON file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved citation JSON for {dataset_id} to {filepath}")
        return filepath

    except Exception as e:
        logger.error(
            f"Failed to save citation JSON for {dataset_id} to {filepath}. Error: {e}"
        )
        raise OSError(f"Could not save JSON file: {e}")


def load_citation_json(filepath: str) -> Dict[str, Any]:
    """
    Load citation data from JSON file.

    Args:
        filepath (str): Path to JSON file

    Returns:
        Dict[str, Any]: Citation data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)  # type: ignore
    except FileNotFoundError:
        logger.error(f"Citation JSON file not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {filepath}: {e}")
        raise


def migrate_pickle_to_json(
    pickle_filepath: str, output_dir: str, dataset_id: Optional[str] = None
) -> str:
    """
    Convert an existing pickle file to JSON format.

    Args:
        pickle_filepath (str): Path to pickle file
        output_dir (str): Output directory for JSON file
        dataset_id (str, optional): Dataset ID. If not provided, extracted from filename.

    Returns:
        str: Path to created JSON file
    """
    # Extract dataset ID from filename if not provided
    if dataset_id is None:
        filename = os.path.basename(pickle_filepath)
        dataset_id = filename.replace(".pkl", "")

    try:
        # Load pickle file
        citations_df = pd.read_pickle(pickle_filepath)
        logger.info(
            f"Loaded pickle file {pickle_filepath} with {len(citations_df)} citations"
        )

        # Convert to JSON
        json_filepath = save_citation_json(dataset_id, citations_df, output_dir)
        logger.info(f"Successfully migrated {pickle_filepath} to {json_filepath}")

        return json_filepath

    except Exception as e:
        logger.error(f"Failed to migrate {pickle_filepath} to JSON: {e}")
        raise


def get_citation_summary_from_json(json_filepath: str) -> Dict[str, Any]:
    """
    Extract summary information from a citation JSON file.

    Args:
        json_filepath (str): Path to citation JSON file

    Returns:
        Dict[str, Any]: Summary with keys: dataset_id, num_citations,
                       total_cumulative_citations, date_last_updated
    """
    citation_data = load_citation_json(json_filepath)

    return {
        "dataset_id": citation_data.get("dataset_id"),
        "num_citations": citation_data.get("num_citations", 0),
        "total_cumulative_citations": citation_data.get("metadata", {}).get(
            "total_cumulative_citations", 0
        ),
        "date_last_updated": citation_data.get("date_last_updated"),
    }


def load_citations_from_json(file_path: str) -> Dict[str, Any]:
    """
    Load citation data from a JSON file.

    Args:
        file_path: Path to the citation JSON file

    Returns:
        Dictionary containing citation data structure

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        logger.debug(f"Loaded citations from {file_path}")
        return data

    except FileNotFoundError:
        logger.error(f"Citation file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in citation file {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading citation file {file_path}: {e}")
        raise
