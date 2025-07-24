"""
Utility functions for handling citation data in JSON format.

This module provides functions to convert citation DataFrames to structured JSON format
and handle citation data for easier downstream processing.

(c) 2024, Seyed Yahya Shirazi
"""

import pandas as pd
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def create_citation_json_structure(
    dataset_id: str,
    citations_df: pd.DataFrame,
    fetch_date: Optional[datetime] = None
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
                "processing_version": "1.0"
            },
            "citation_details": []
        }
    
    # Calculate metadata
    total_cumulative_citations = citations_df['cited_by'].sum() if 'cited_by' in citations_df.columns else 0
    
    # Process citation details
    citation_details = []
    for _, row in citations_df.iterrows():
        # Start with main fields
        citation_obj = {
            "title": _safe_get_value(row, 'title'),
            "author": _safe_get_value(row, 'author'),
            "venue": _safe_get_value(row, 'venue'),
            "year": _safe_get_int_value(row, 'year'),
            "url": _safe_get_value(row, 'url'),
            "cited_by": _safe_get_int_value(row, 'cited_by'),
        }
        
        # Extract unique fields from bib data (avoiding duplicates)
        bib_data = row.get('bib', {})
        if isinstance(bib_data, dict):
            # Extract valuable unique fields from bib
            unique_bib_fields = {
                'abstract': _safe_get_value_from_dict(bib_data, 'abstract'),
                'short_author': _safe_get_value_from_dict(bib_data, 'short_author'),
                'publisher': _safe_get_value_from_dict(bib_data, 'publisher'),
                'pages': _safe_get_value_from_dict(bib_data, 'pages'),
                'volume': _safe_get_value_from_dict(bib_data, 'volume'),
                'journal': _safe_get_value_from_dict(bib_data, 'journal'),
                'pub_type': _safe_get_value_from_dict(bib_data, 'pub_type'),
                'bib_id': _safe_get_value_from_dict(bib_data, 'bib_id'),
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
            "total_cumulative_citations": int(total_cumulative_citations) if pd.notna(total_cumulative_citations) else 0,
            "fetch_date": fetch_date.isoformat(),
            "processing_version": "1.0"
        },
        "citation_details": citation_details
    }
    
    return json_structure


def _safe_get_value(row: pd.Series, key: str, default: str = "n/a") -> str:
    """Safely get a string value from a pandas Series row."""
    value = row.get(key, default)
    if pd.isna(value) or value is None:
        return default
    return str(value)


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
    fetch_date: Optional[datetime] = None
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
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved citation JSON for {dataset_id} to {filepath}")
        return filepath
    
    except Exception as e:
        logger.error(f"Failed to save citation JSON for {dataset_id} to {filepath}. Error: {e}")
        raise IOError(f"Could not save JSON file: {e}")


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
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Citation JSON file not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {filepath}: {e}")
        raise


def migrate_pickle_to_json(
    pickle_filepath: str,
    output_dir: str,
    dataset_id: Optional[str] = None
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
        dataset_id = filename.replace('.pkl', '')
    
    try:
        # Load pickle file
        citations_df = pd.read_pickle(pickle_filepath)
        logger.info(f"Loaded pickle file {pickle_filepath} with {len(citations_df)} citations")
        
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
        "total_cumulative_citations": citation_data.get("metadata", {}).get("total_cumulative_citations", 0),
        "date_last_updated": citation_data.get("date_last_updated")
    } 