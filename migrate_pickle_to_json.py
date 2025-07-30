#!/usr/bin/env python3
"""
Migration script to convert existing citation pickle files to JSON format.

This script processes all .pkl files in the citations directory and converts them
to the new JSON citation format for easier downstream processing.

Usage:
    python migrate_pickle_to_json.py [--input-dir citations] [--output-dir citations] [--overwrite]

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from dataset_citations.core import citation_utils
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_pickle_files(input_dir: str) -> list[str]:
    """
    Find all pickle files in the input directory.
    
    Args:
        input_dir (str): Directory to search for pickle files
    
    Returns:
        list[str]: List of pickle file paths
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return []
    
    pickle_files = list(input_path.glob("*.pkl"))
    logger.info(f"Found {len(pickle_files)} pickle files in {input_dir}")
    return [str(f) for f in pickle_files]


def migrate_single_file(pickle_filepath: str, output_dir: str, overwrite: bool = False) -> bool:
    """
    Migrate a single pickle file to JSON format.
    
    Args:
        pickle_filepath (str): Path to pickle file
        output_dir (str): Output directory for JSON file
        overwrite (bool): Whether to overwrite existing JSON files
    
    Returns:
        bool: True if migration was successful, False otherwise
    """
    try:
        # Extract dataset ID from filename
        filename = os.path.basename(pickle_filepath)
        dataset_id = filename.replace('.pkl', '')
        
        # Check if JSON file already exists
        json_filename = f"{dataset_id}_citations.json"
        json_filepath = os.path.join(output_dir, json_filename)
        
        if os.path.exists(json_filepath) and not overwrite:
            logger.info(f"JSON file already exists for {dataset_id}, skipping (use --overwrite to force)")
            return True
        
        # Load and validate pickle file
        try:
            citations_df = pd.read_pickle(pickle_filepath)
            logger.info(f"Loaded {dataset_id}: {len(citations_df)} citations")
        except Exception as e:
            logger.error(f"Failed to load pickle file {pickle_filepath}: {e}")
            return False
        
        # Migrate to JSON
        json_filepath = citation_utils.save_citation_json(dataset_id, citations_df, output_dir)
        logger.info(f"Successfully migrated {dataset_id} to JSON: {json_filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate {pickle_filepath}: {e}")
        return False


def validate_migration(input_dir: str, output_dir: str) -> dict:
    """
    Validate that all pickle files have corresponding JSON files.
    
    Args:
        input_dir (str): Input directory with pickle files
        output_dir (str): Output directory with JSON files
    
    Returns:
        dict: Validation results with counts and missing files
    """
    pickle_files = find_pickle_files(input_dir)
    validation_results = {
        "total_pickle_files": len(pickle_files),
        "json_files_found": 0,
        "missing_json_files": [],
        "validation_errors": []
    }
    
    for pickle_file in pickle_files:
        filename = os.path.basename(pickle_file)
        dataset_id = filename.replace('.pkl', '')
        json_filename = f"{dataset_id}_citations.json"
        json_filepath = os.path.join(output_dir, json_filename)
        
        if os.path.exists(json_filepath):
            # Validate JSON file
            try:
                citation_data = citation_utils.load_citation_json(json_filepath)
                if citation_data.get("dataset_id") == dataset_id:
                    validation_results["json_files_found"] += 1
                else:
                    validation_results["validation_errors"].append(
                        f"Dataset ID mismatch in {json_filename}"
                    )
            except Exception as e:
                validation_results["validation_errors"].append(
                    f"Invalid JSON file {json_filename}: {e}"
                )
        else:
            validation_results["missing_json_files"].append(dataset_id)
    
    return validation_results


def generate_migration_report(input_dir: str, output_dir: str, successful: list, failed: list):
    """
    Generate a migration report.
    
    Args:
        input_dir (str): Input directory
        output_dir (str): Output directory  
        successful (list): List of successfully migrated dataset IDs
        failed (list): List of failed dataset IDs
    """
    report_lines = [
        "=" * 60,
        "PICKLE TO JSON MIGRATION REPORT",
        "=" * 60,
        f"Input Directory: {input_dir}",
        f"Output Directory: {output_dir}",
        f"Total Files Processed: {len(successful) + len(failed)}",
        f"Successful Migrations: {len(successful)}",
        f"Failed Migrations: {len(failed)}",
        ""
    ]
    
    if successful:
        report_lines.extend([
            "Successfully Migrated Datasets:",
            "-" * 30
        ])
        for dataset_id in successful:
            report_lines.append(f"  ✓ {dataset_id}")
        report_lines.append("")
    
    if failed:
        report_lines.extend([
            "Failed Migrations:",
            "-" * 20
        ])
        for dataset_id in failed:
            report_lines.append(f"  ✗ {dataset_id}")
        report_lines.append("")
    
    # Validation
    validation_results = validate_migration(input_dir, output_dir)
    report_lines.extend([
        "Validation Results:",
        "-" * 20,
        f"Total pickle files: {validation_results['total_pickle_files']}",
        f"JSON files found: {validation_results['json_files_found']}",
        f"Missing JSON files: {len(validation_results['missing_json_files'])}",
        f"Validation errors: {len(validation_results['validation_errors'])}",
        ""
    ])
    
    if validation_results['missing_json_files']:
        report_lines.extend([
            "Missing JSON Files:",
            "-" * 20
        ])
        for dataset_id in validation_results['missing_json_files']:
            report_lines.append(f"  - {dataset_id}")
        report_lines.append("")
    
    if validation_results['validation_errors']:
        report_lines.extend([
            "Validation Errors:",
            "-" * 20
        ])
        for error in validation_results['validation_errors']:
            report_lines.append(f"  - {error}")
        report_lines.append("")
    
    report_lines.append("=" * 60)
    
    # Print report
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save report to file
    report_filepath = os.path.join(output_dir, "migration_report.txt")
    try:
        with open(report_filepath, 'w') as f:
            f.write(report_text)
        logger.info(f"Migration report saved to: {report_filepath}")
    except Exception as e:
        logger.warning(f"Could not save migration report: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate citation pickle files to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate all pickle files in citations/ directory
  python migrate_pickle_to_json.py
  
  # Migrate from custom input directory to custom output directory
  python migrate_pickle_to_json.py --input-dir data/pickles --output-dir data/json
  
  # Overwrite existing JSON files
  python migrate_pickle_to_json.py --overwrite
        """
    )
    
    parser.add_argument(
        "--input-dir", 
        default="citations/pickle",
        help="Directory containing pickle files to migrate (default: citations/pickle)"
    )
    parser.add_argument(
        "--output-dir",
        default="citations/json", 
        help="Directory to save JSON files (default: citations/json)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing JSON files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="Show what would be migrated without actually doing it"
    )
    
    args = parser.parse_args()
    
    # Validate directories
    if not os.path.exists(args.input_dir):
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find pickle files
    pickle_files = find_pickle_files(args.input_dir)
    if not pickle_files:
        logger.warning("No pickle files found to migrate")
        sys.exit(0)
    
    # Dry run mode
    if args.dry_run:
        print(f"\nDRY RUN: Would migrate {len(pickle_files)} pickle files:")
        for pickle_file in pickle_files:
            filename = os.path.basename(pickle_file)
            dataset_id = filename.replace('.pkl', '')
            json_filename = f"{dataset_id}_citations.json"
            print(f"  {filename} -> {json_filename}")
        sys.exit(0)
    
    # Perform migration
    logger.info(f"Starting migration of {len(pickle_files)} pickle files...")
    successful_migrations = []
    failed_migrations = []
    
    for pickle_file in pickle_files:
        filename = os.path.basename(pickle_file)
        dataset_id = filename.replace('.pkl', '')
        
        if migrate_single_file(pickle_file, args.output_dir, args.overwrite):
            successful_migrations.append(dataset_id)
        else:
            failed_migrations.append(dataset_id)
    
    # Generate report
    generate_migration_report(
        args.input_dir, args.output_dir, successful_migrations, failed_migrations
    )
    
    # Exit with appropriate code
    if failed_migrations:
        logger.warning(f"Migration completed with {len(failed_migrations)} failures")
        sys.exit(1)
    else:
        logger.info("All migrations completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main() 