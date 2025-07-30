#!/usr/bin/env python3
"""
Script to regenerate CSV summary files from existing JSON citation data.

This script addresses the issue where Google Scholar citation fetching fails
(due to captchas) but JSON files are generated successfully. It reads the
JSON files and creates the corresponding CSV files that the workflow expects.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import argparse
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging
from dataset_citations.core import citation_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def scan_json_files(json_dir: str) -> dict:
    """
    Scan directory for JSON citation files and extract citation counts.
    
    Args:
        json_dir (str): Directory containing JSON citation files
        
    Returns:
        dict: Dictionary mapping dataset_id to citation count
    """
    citation_counts = {}
    json_files = list(Path(json_dir).glob("*_citations.json"))
    
    logger.info(f"Found {len(json_files)} JSON citation files in {json_dir}")
    
    for json_file in json_files:
        try:
            citation_data = citation_utils.load_citation_json(str(json_file))
            dataset_id = citation_data.get('dataset_id')
            num_citations = citation_data.get('num_citations', 0)
            
            if dataset_id:
                citation_counts[dataset_id] = num_citations
                logger.debug(f"Extracted {dataset_id}: {num_citations} citations")
            else:
                logger.warning(f"No dataset_id found in {json_file}")
                
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            
    return citation_counts


def generate_citations_csv(citation_counts: dict, output_dir: str, date_suffix: str = None) -> str:
    """
    Generate the citations_DDMMYYYY.csv file from citation counts.
    
    Args:
        citation_counts (dict): Dictionary mapping dataset_id to citation count
        output_dir (str): Output directory
        date_suffix (str): Optional date suffix, defaults to today
        
    Returns:
        str: Path to generated CSV file
    """
    if date_suffix is None:
        date_suffix = datetime.now().strftime('%d%m%Y')
    
    filename = f'citations_{date_suffix}.csv'
    filepath = os.path.join(output_dir, filename)
    
    # Create pandas Series with citation counts
    citations_series = pd.Series(citation_counts, name='number_of_citations', dtype='float64')
    citations_series.index.name = 'dataset_id'
    
    # Save to CSV
    citations_series.to_csv(filepath)
    logger.info(f"Generated {filepath} with {len(citation_counts)} datasets")
    
    return filepath


def generate_updated_datasets_csv(citation_counts: dict, output_dir: str, date_suffix: str = None) -> str:
    """
    Generate the updated_datasets_DDMMYYYY.csv file from citation counts.
    
    Args:
        citation_counts (dict): Dictionary mapping dataset_id to citation count
        output_dir (str): Output directory
        date_suffix (str): Optional date suffix, defaults to today
        
    Returns:
        str: Path to generated CSV file
    """
    if date_suffix is None:
        date_suffix = datetime.now().strftime('%d%m%Y')
    
    filename = f'updated_datasets_{date_suffix}.csv'
    filepath = os.path.join(output_dir, filename)
    
    # Create DataFrame with citation counts (using count as "retrieved_citations_count")
    updated_df = pd.DataFrame.from_dict(citation_counts, orient='index', columns=['retrieved_citations_count'])
    updated_df.index.name = 'dataset_id'
    
    # Save to CSV
    updated_df.to_csv(filepath)
    logger.info(f"Generated {filepath} with {len(citation_counts)} datasets")
    
    return filepath


def update_previous_citations(citations_csv_path: str, output_dir: str) -> str:
    """
    Copy the current citations CSV to previous_citations.csv for next run.
    
    Args:
        citations_csv_path (str): Path to current citations CSV
        output_dir (str): Output directory
        
    Returns:
        str: Path to previous_citations.csv
    """
    previous_citations_path = os.path.join(output_dir, 'previous_citations.csv')
    
    # Read and copy the data
    df = pd.read_csv(citations_csv_path, index_col='dataset_id')
    df.to_csv(previous_citations_path)
    
    logger.info(f"Updated {previous_citations_path} from {citations_csv_path}")
    return previous_citations_path


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate CSV summary files from JSON citation data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate CSV files from JSON data
  python regenerate_csv_from_json.py --json-dir citations/json --output-dir citations/
  
  # Regenerate with custom date suffix
  python regenerate_csv_from_json.py --json-dir citations/json --output-dir citations/ --date-suffix 26072025
  
  # Update previous_citations.csv as well
  python regenerate_csv_from_json.py --json-dir citations/json --output-dir citations/ --update-previous
        """
    )
    
    parser.add_argument(
        "--json-dir",
        default="citations/json",
        help="Directory containing JSON citation files (default: citations/json)"
    )
    parser.add_argument(
        "--output-dir",
        default="citations",
        help="Directory to save CSV files (default: citations)"
    )
    parser.add_argument(
        "--date-suffix",
        help="Date suffix for filenames (DDMMYYYY format). Defaults to today's date"
    )
    parser.add_argument(
        "--update-previous",
        action="store_true",
        help="Also update previous_citations.csv file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate directories
    if not os.path.exists(args.json_dir):
        logger.error(f"JSON directory does not exist: {args.json_dir}")
        return 1
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Scan JSON files for citation counts
    logger.info(f"Scanning JSON files in {args.json_dir}")
    citation_counts = scan_json_files(args.json_dir)
    
    if not citation_counts:
        logger.error("No citation data found in JSON files")
        return 1
    
    total_citations = sum(citation_counts.values())
    logger.info(f"Found {len(citation_counts)} datasets with {total_citations} total citations")
    
    # Generate CSV files
    citations_csv = generate_citations_csv(citation_counts, args.output_dir, args.date_suffix)
    updated_csv = generate_updated_datasets_csv(citation_counts, args.output_dir, args.date_suffix)
    
    # Update previous citations if requested
    if args.update_previous:
        previous_csv = update_previous_citations(citations_csv, args.output_dir)
        logger.info(f"Updated previous citations file: {previous_csv}")
    
    logger.info("CSV regeneration completed successfully")
    logger.info(f"Generated files:")
    logger.info(f"  - {citations_csv}")
    logger.info(f"  - {updated_csv}")
    
    return 0


if __name__ == "__main__":
    exit(main()) 