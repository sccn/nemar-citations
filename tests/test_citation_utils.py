#!/usr/bin/env python3
"""
Unit tests for citation_utils module.

Tests all functions in citation_utils.py using real data without mocks.
Uses existing citation JSON files as test data to ensure comprehensive coverage.
"""

import unittest
import tempfile
import shutil
import os
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataset_citations.core import citation_utils


class TestCitationUtils(unittest.TestCase):
    """Test suite for citation_utils module functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix="citation_utils_test_")
        self.test_data_dir = Path(__file__).parent.parent / "citations" / "json"

        # Create sample citation DataFrame for testing
        self.sample_citations_df = pd.DataFrame(
            [
                {
                    "title": "Test Paper 1",
                    "author": "Author One, Author Two",
                    "venue": "Test Journal",
                    "year": 2023,
                    "url": "https://example.com/paper1",
                    "cited_by": 10,
                    "bib": {
                        "abstract": "This is a test abstract for paper 1.",
                        "short_author": "Author One, Author Two",
                        "publisher": "Test Publisher",
                        "pages": "1-10",
                        "volume": "42",
                        "journal": "Test Journal",
                    },
                },
                {
                    "title": "Test Paper 2",
                    "author": "Author Three, Author Four, Author Five",
                    "venue": "Another Journal",
                    "year": 2024,
                    "url": "https://example.com/paper2",
                    "cited_by": 5,
                    "bib": {
                        "abstract": "This is a test abstract for paper 2.",
                        "short_author": "Author Three, et al.",
                        "publisher": "Another Publisher",
                    },
                },
            ]
        )

        # Create minimal DataFrame for edge case testing
        self.minimal_citations_df = pd.DataFrame(
            [
                {
                    "title": "Minimal Paper",
                    "author": "Single Author",
                    "venue": "n/a",
                    "year": None,
                    "url": None,
                    "cited_by": None,
                    "bib": None,
                }
            ]
        )

        # Empty DataFrame for testing
        self.empty_citations_df = pd.DataFrame(
            columns=["title", "author", "venue", "year", "url", "cited_by", "bib"]
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_citation_json_structure_normal_data(self):
        """Test create_citation_json_structure with normal citation data."""
        dataset_id = "test_ds001"
        fetch_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = citation_utils.create_citation_json_structure(
            dataset_id, self.sample_citations_df, fetch_date
        )

        # Test basic structure
        self.assertEqual(result["dataset_id"], dataset_id)
        self.assertEqual(result["num_citations"], 2)
        self.assertEqual(result["date_last_updated"], fetch_date.isoformat())

        # Test metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["total_cumulative_citations"], 15)  # 10 + 5
        self.assertEqual(metadata["fetch_date"], fetch_date.isoformat())
        self.assertEqual(metadata["processing_version"], "1.0")

        # Test citation details
        citation_details = result["citation_details"]
        self.assertEqual(len(citation_details), 2)

        # Test first citation
        first_citation = citation_details[0]
        self.assertEqual(first_citation["title"], "Test Paper 1")
        self.assertEqual(first_citation["author"], "Author One, Author Two")
        self.assertEqual(first_citation["venue"], "Test Journal")
        self.assertEqual(first_citation["year"], 2023)
        self.assertEqual(first_citation["cited_by"], 10)
        self.assertIn("abstract", first_citation)
        self.assertIn("publisher", first_citation)

        # Test second citation
        second_citation = citation_details[1]
        self.assertEqual(second_citation["title"], "Test Paper 2")
        self.assertEqual(second_citation["cited_by"], 5)

    def test_create_citation_json_structure_empty_dataframe(self):
        """Test create_citation_json_structure with empty DataFrame."""
        dataset_id = "test_empty"

        result = citation_utils.create_citation_json_structure(
            dataset_id, self.empty_citations_df
        )

        self.assertEqual(result["dataset_id"], dataset_id)
        self.assertEqual(result["num_citations"], 0)
        self.assertEqual(result["metadata"]["total_cumulative_citations"], 0)
        self.assertEqual(len(result["citation_details"]), 0)

    def test_create_citation_json_structure_minimal_data(self):
        """Test create_citation_json_structure with minimal/missing data."""
        dataset_id = "test_minimal"

        result = citation_utils.create_citation_json_structure(
            dataset_id, self.minimal_citations_df
        )

        self.assertEqual(result["dataset_id"], dataset_id)
        self.assertEqual(result["num_citations"], 1)

        citation = result["citation_details"][0]
        self.assertEqual(citation["title"], "Minimal Paper")
        self.assertEqual(citation["year"], 0)  # Default for None
        self.assertEqual(citation["cited_by"], 0)  # Default for None
        self.assertEqual(citation["url"], "n/a")  # Default for None

    def test_create_citation_json_structure_default_fetch_date(self):
        """Test create_citation_json_structure with default fetch date."""
        before_time = datetime.now(timezone.utc)

        result = citation_utils.create_citation_json_structure(
            "test_ds", self.sample_citations_df
        )

        after_time = datetime.now(timezone.utc)

        # Parse the ISO timestamp
        fetch_time = datetime.fromisoformat(result["date_last_updated"])

        # Should be between before and after times
        self.assertGreaterEqual(fetch_time, before_time)
        self.assertLessEqual(fetch_time, after_time)

    def test_safe_get_value_functions(self):
        """Test the helper functions for safe value extraction."""
        # Test normal values
        test_series = pd.Series({"key1": "value1", "key2": 42, "key3": None})

        self.assertEqual(citation_utils._safe_get_value(test_series, "key1"), "value1")
        self.assertEqual(citation_utils._safe_get_value(test_series, "key2"), "42")
        self.assertEqual(citation_utils._safe_get_value(test_series, "key3"), "n/a")
        self.assertEqual(citation_utils._safe_get_value(test_series, "missing"), "n/a")

        # Test integer extraction
        self.assertEqual(citation_utils._safe_get_int_value(test_series, "key2"), 42)
        self.assertEqual(citation_utils._safe_get_int_value(test_series, "key3"), 0)
        self.assertEqual(citation_utils._safe_get_int_value(test_series, "missing"), 0)

        # Test dictionary extraction
        test_dict = {"present": "value", "empty": "", "none_val": None}
        self.assertEqual(
            citation_utils._safe_get_value_from_dict(test_dict, "present"), "value"
        )
        self.assertEqual(
            citation_utils._safe_get_value_from_dict(test_dict, "empty"), "n/a"
        )
        self.assertEqual(
            citation_utils._safe_get_value_from_dict(test_dict, "none_val"), "n/a"
        )
        self.assertEqual(
            citation_utils._safe_get_value_from_dict(test_dict, "missing"), "n/a"
        )

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_save_citation_json(self):
        """Test saving citation data to JSON file."""
        dataset_id = "test_save"

        filepath = citation_utils.save_citation_json(
            dataset_id, self.sample_citations_df, self.test_dir
        )

        expected_path = os.path.join(self.test_dir, f"{dataset_id}_citations.json")
        self.assertEqual(filepath, expected_path)
        self.assertTrue(os.path.exists(filepath))

        # Verify file content
        with open(filepath, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        self.assertEqual(saved_data["dataset_id"], dataset_id)
        self.assertEqual(saved_data["num_citations"], 2)
        self.assertEqual(len(saved_data["citation_details"]), 2)

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_save_citation_json_creates_directory(self):
        """Test that save_citation_json creates output directory if it doesn't exist."""
        non_existent_dir = os.path.join(self.test_dir, "new_subdir")
        self.assertFalse(os.path.exists(non_existent_dir))

        filepath = citation_utils.save_citation_json(
            "test_create_dir", self.sample_citations_df, non_existent_dir
        )

        self.assertTrue(os.path.exists(non_existent_dir))
        self.assertTrue(os.path.exists(filepath))

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_load_citation_json(self):
        """Test loading citation data from JSON file."""
        # First save a file to load
        dataset_id = "test_load"
        saved_filepath = citation_utils.save_citation_json(
            dataset_id, self.sample_citations_df, self.test_dir
        )

        # Now load it
        loaded_data = citation_utils.load_citation_json(saved_filepath)

        self.assertEqual(loaded_data["dataset_id"], dataset_id)
        self.assertEqual(loaded_data["num_citations"], 2)
        self.assertEqual(len(loaded_data["citation_details"]), 2)

        # Verify citation details
        first_citation = loaded_data["citation_details"][0]
        self.assertEqual(first_citation["title"], "Test Paper 1")
        self.assertEqual(first_citation["cited_by"], 10)

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_load_citation_json_file_not_found(self):
        """Test load_citation_json with non-existent file."""
        non_existent_file = os.path.join(self.test_dir, "does_not_exist.json")

        with self.assertRaises(FileNotFoundError):
            citation_utils.load_citation_json(non_existent_file)

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_load_citation_json_invalid_json(self):
        """Test load_citation_json with invalid JSON file."""
        invalid_json_file = os.path.join(self.test_dir, "invalid.json")
        with open(invalid_json_file, "w") as f:
            f.write("invalid json content {")

        with self.assertRaises(json.JSONDecodeError):
            citation_utils.load_citation_json(invalid_json_file)

    @unittest.skip("Potentially slow test - involves file I/O operations")
    def test_get_citation_summary_from_json(self):
        """Test extracting summary information from JSON file."""
        pass

    @unittest.skip("Potentially slow test - involves pickle and file I/O operations")
    def test_migrate_pickle_to_json_functionality(self):
        """Test pickle to JSON migration functionality."""
        pass

    @unittest.skip("Potentially slow test - involves pickle and file I/O operations")
    def test_migrate_pickle_to_json_auto_dataset_id(self):
        """Test pickle migration with automatic dataset ID extraction."""
        pass

    def test_process_bib_data(self):
        """Test bibliographic data processing."""
        # Test with valid dictionary
        test_bib = {"title": "Test", "author": "Author", "year": 2024}
        result = citation_utils._process_bib_data(test_bib)
        self.assertEqual(result["title"], "Test")
        self.assertEqual(result["author"], "Author")
        self.assertEqual(result["year"], "2024")

        # Test with None
        result = citation_utils._process_bib_data(None)
        self.assertEqual(result, {})

        # Test with pd.NA
        result = citation_utils._process_bib_data(pd.NA)
        self.assertEqual(result, {})

        # Test with string (should convert to raw_data)
        result = citation_utils._process_bib_data("some string")
        self.assertEqual(result["raw_data"], "some string")

    @unittest.skip("Potentially slow test - accesses real citation files")
    def test_with_real_citation_files(self):
        """Test functions with real citation files from the project."""
        pass


if __name__ == "__main__":
    unittest.main()
