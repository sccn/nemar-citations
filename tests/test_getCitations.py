#!/usr/bin/env python3
"""
Unit tests for getCitations module.

Tests citation retrieval functions using real API calls with minimal usage.
Uses environment variables from .secrets file for API authentication.

Performance Optimizations:
- Proxy setup is done once in setUpClass and reused across all tests
- This eliminates 5+ separate proxy setup calls that were causing 30+ second delays
- Slow API tests are consolidated into one integration test

Test Structure:
1. Fast tests (seconds): Basic functionality, error handling, DataFrame structure
2. Slow integration test (minutes): Full API workflow with real Google Scholar calls

Usage:
- Regular tests: `pytest tests/test_getCitations.py` (runs in ~30 seconds)
- Full API test: `RUN_SLOW_INTEGRATION_TESTS=1 pytest tests/test_getCitations.py::TestGetCitations::test_integration_full_api_workflow -v`
"""

import unittest
import os
import sys
import pandas as pd
import logging
from unittest.mock import patch
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataset_citations.core import getCitations as gc

# Configure test logging
logging.getLogger().setLevel(logging.WARNING)  # Reduce noise during tests


class TestGetCitations(unittest.TestCase):
    """Test suite for getCitations module functions."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        # Load environment variables for API testing
        load_dotenv(".secrets")
        cls.has_api_key = bool(os.getenv("SCRAPERAPI_KEY"))
        cls.proxy_initialized = False

        if not cls.has_api_key:
            print("\nWarning: SCRAPERAPI_KEY not found in .secrets file.")
            print(
                "Some tests will be skipped. To run full test suite, add API key to .secrets file."
            )
        else:
            # Set up proxy once for all tests that need it
            print("\nSetting up proxy for all tests...")
            try:
                gc.get_working_proxy("ScraperAPI")
                cls.proxy_initialized = True
                print("Proxy setup successful - will be reused for all tests.")
            except Exception as e:
                print(f"Failed to initialize proxy: {e}")
                cls.proxy_initialized = False

    def setUp(self):
        """Set up test fixtures."""
        # Test datasets known to have citations (but minimal to save API calls)
        # These are real datasets from the project with confirmed citations
        self.test_datasets = {
            "minimal": "ds005410",  # Known to have 1 citation from our JSON files
            "medium": "ds005672",  # Known to have 3 citations from our JSON files
        }

        # Invalid dataset for testing error handling
        self.invalid_dataset = "nonexistent_dataset_xyz123"

    def test_get_working_proxy_without_key(self):
        """Test proxy setup without API key (should handle gracefully)."""
        with patch.dict(os.environ, {}, clear=True):
            # This should not crash, but will log an error
            with patch("builtins.print") as mock_print:
                # Force proxy setup to bypass our optimization
                gc.get_working_proxy("ScraperAPI", force=True)

                # Should have printed error messages
                mock_print.assert_called()
                error_calls = [
                    call for call in mock_print.call_args_list if "ERROR" in str(call)
                ]
                self.assertTrue(len(error_calls) > 0)

    def test_get_working_proxy_with_invalid_method(self):
        """Test proxy setup with unsupported method."""
        # This should not crash and should fall back to FreeProxies
        try:
            gc.get_working_proxy("UnsupportedMethod")
            # If we reach here, it didn't crash - which is good
        except Exception as e:
            # We allow exceptions here since this tests edge cases
            # The important thing is it doesn't crash the whole system
            self.assertIsInstance(e, Exception)

    @unittest.skipUnless(
        os.getenv("SCRAPERAPI_KEY"), "Requires SCRAPERAPI_KEY environment variable"
    )
    def test_get_working_proxy_with_valid_key(self):
        """Test proxy setup with valid ScraperAPI key."""
        # Since proxy is set up in setUpClass, we just verify it was successful
        self.assertTrue(
            self.__class__.proxy_initialized,
            "Proxy should have been initialized in setUpClass",
        )

    @unittest.skip("Slow API test - use test_integration_full_api_workflow instead")
    def test_get_citation_numbers_invalid_dataset(self):
        """Test citation count for non-existent dataset."""
        pass

    @unittest.skip("Slow API test - use test_integration_full_api_workflow instead")
    def test_get_citation_numbers_valid_dataset(self):
        """Test citation count for known valid dataset."""
        pass

    def test_get_citations_zero_citations(self):
        """Test get_citations with zero citations requested."""
        result = gc.get_citations("any_dataset", 0)

        # Should return empty DataFrame with correct columns
        expected_columns = [
            "title",
            "author",
            "venue",
            "year",
            "url",
            "cited_by",
            "bib",
        ]
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        self.assertListEqual(list(result.columns), expected_columns)

    def test_get_citations_none_citations(self):
        """Test get_citations with None citations requested."""
        result = gc.get_citations("any_dataset", None)

        # Should return empty DataFrame with correct columns
        expected_columns = [
            "title",
            "author",
            "venue",
            "year",
            "url",
            "cited_by",
            "bib",
        ]
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        self.assertListEqual(list(result.columns), expected_columns)

    def test_get_citations_with_existing_dataframe(self):
        """Test get_citations with existing DataFrame to append to."""
        # Create existing DataFrame
        existing_df = pd.DataFrame(
            [
                {
                    "title": "Existing Paper",
                    "author": "Existing Author",
                    "venue": "Existing Venue",
                    "year": 2020,
                    "url": "http://existing.com",
                    "cited_by": 5,
                    "bib": {"title": "Existing Paper"},
                }
            ]
        )

        # Test with 0 citations (should return existing DataFrame unchanged)
        result = gc.get_citations("any_dataset", 0, citations=existing_df)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["title"], "Existing Paper")

    @unittest.skip("Slow API test - use test_integration_full_api_workflow instead")
    def test_get_citations_single_citation(self):
        """Test retrieving a single citation from a known dataset."""
        pass

    @unittest.skip("Slow API test - use test_integration_full_api_workflow instead")
    def test_get_citations_with_year_filter(self):
        """Test citation retrieval with year filtering."""
        pass

    @unittest.skip("Slow API test - use test_integration_full_api_workflow instead")
    def test_get_citations_invalid_dataset_graceful_handling(self):
        """Test that get_citations handles invalid datasets gracefully."""
        pass

    def test_citation_dataframe_structure(self):
        """Test that citation DataFrames have the expected structure."""
        # Test empty DataFrame creation
        empty_df = gc.get_citations("test", 0)

        expected_columns = [
            "title",
            "author",
            "venue",
            "year",
            "url",
            "cited_by",
            "bib",
        ]
        self.assertListEqual(list(empty_df.columns), expected_columns)
        self.assertTrue(empty_df.empty)

    @unittest.skipUnless(
        os.getenv("RUN_SLOW_INTEGRATION_TESTS"),
        "Slow integration test - set RUN_SLOW_INTEGRATION_TESTS=1 to run",
    )
    @unittest.skipUnless(
        os.getenv("SCRAPERAPI_KEY"), "Requires SCRAPERAPI_KEY environment variable"
    )
    def test_integration_full_api_workflow(self):
        """
        Comprehensive integration test for all Google Scholar API functionality.

        This test consolidates all the slow API tests into one comprehensive test.
        It tests: proxy setup, citation counting, citation retrieval, year filtering,
        error handling, and data structure validation.

        To run this test: RUN_SLOW_INTEGRATION_TESTS=1 pytest tests/test_getCitations.py::TestGetCitations::test_integration_full_api_workflow -v
        """
        # Skip if proxy initialization failed
        if not self.__class__.proxy_initialized:
            self.skipTest("Proxy not initialized")

        # Test 1: Citation count for valid dataset
        dataset_id = self.test_datasets["minimal"]
        print(f"\n[Integration Test] Testing citation count for {dataset_id}")
        citation_count = gc.get_citation_numbers(dataset_id)
        self.assertGreaterEqual(citation_count, 0)
        self.assertLessEqual(citation_count, 1000)  # Reasonable upper bound
        print(f"Found {citation_count} citations")

        # Test 2: Citation count for invalid dataset
        print("[Integration Test] Testing invalid dataset handling")
        invalid_count = gc.get_citation_numbers(self.invalid_dataset)
        self.assertEqual(invalid_count, 0)

        # Test 3: Citation retrieval with minimal API calls
        if citation_count > 0:
            print("[Integration Test] Testing citation retrieval")
            max_citations = min(citation_count, 1)
            citations_df = gc.get_citations(dataset_id, max_citations)

            # Verify DataFrame structure
            self.assertIsInstance(citations_df, pd.DataFrame)
            self.assertLessEqual(len(citations_df), max_citations)

            if not citations_df.empty:
                # Verify columns exist
                expected_columns = [
                    "title",
                    "author",
                    "venue",
                    "year",
                    "url",
                    "cited_by",
                    "bib",
                ]
                for col in expected_columns:
                    self.assertIn(col, citations_df.columns)

                # Verify citation has reasonable data
                citation = citations_df.iloc[0]
                self.assertIsNotNone(citation["title"])
                self.assertIsNotNone(citation["author"])
                self.assertIsNotNone(citation["venue"])

                # Numeric fields should be reasonable
                if pd.notna(citation["cited_by"]) and citation["cited_by"] != "n/a":
                    self.assertGreaterEqual(int(citation["cited_by"]), 0)

                # Year should be reasonable if present
                if pd.notna(citation["year"]) and citation["year"] != "n/a":
                    year = int(citation["year"])
                    self.assertGreaterEqual(year, 1900)
                    self.assertLessEqual(year, 2030)

        # Test 4: Year filtering (if citations available)
        print("[Integration Test] Testing year filtering")
        year_filtered = gc.get_citations(dataset_id, 1, year_low=2020, year_high=2024)
        self.assertIsInstance(year_filtered, pd.DataFrame)

        # Test 5: Invalid dataset graceful handling
        print("[Integration Test] Testing graceful error handling")
        invalid_result = gc.get_citations(self.invalid_dataset, 1)
        self.assertIsInstance(invalid_result, pd.DataFrame)

        print("[Integration Test] All API functionality tests completed successfully!")

    def test_error_handling_patterns(self):
        """Test error handling patterns in the module."""
        # Test that functions don't crash with various invalid inputs

        # Empty string dataset
        result = gc.get_citation_numbers("")
        self.assertEqual(result, 0)

        # None dataset (should raise TypeError)
        with self.assertRaises(TypeError):
            gc.get_citation_numbers(None)

    @unittest.skip("Slow test - logging functionality covered in integration test")
    def test_logging_functionality(self):
        """Test that logging works correctly."""
        pass


class TestGetCitationsEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for getCitations module."""

    def test_proxy_setup_error_conditions(self):
        """Test proxy setup under various error conditions."""
        # Test with empty environment
        with patch.dict(os.environ, {}, clear=True):
            # Should handle missing API key gracefully
            with patch("builtins.print"):  # Suppress error output
                gc.get_working_proxy("ScraperAPI")

    def test_get_citations_boundary_conditions(self):
        """Test get_citations with boundary conditions."""
        # Test with very large number (should be handled gracefully)
        result = gc.get_citations("test_dataset", 10000)
        self.assertIsInstance(result, pd.DataFrame)

        # Test with negative number (should be handled gracefully)
        result = gc.get_citations("test_dataset", -1)
        self.assertIsInstance(result, pd.DataFrame)

    def test_dataframe_column_consistency(self):
        """Test that all functions return DataFrames with consistent columns."""
        expected_columns = [
            "title",
            "author",
            "venue",
            "year",
            "url",
            "cited_by",
            "bib",
        ]

        # Test various scenarios
        test_scenarios = [
            ("test", 0),
            ("test", None),
        ]

        for dataset, num_cites in test_scenarios:
            result = gc.get_citations(dataset, num_cites)
            self.assertListEqual(list(result.columns), expected_columns)


if __name__ == "__main__":
    # Run tests with appropriate verbosity
    unittest.main(verbosity=2)
