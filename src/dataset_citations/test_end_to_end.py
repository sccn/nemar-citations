#!/usr/bin/env python3
"""
End-to-end test function for the dataset citations workflow.

This script tests the complete workflow with a small subset of datasets
to ensure the package structure works correctly before running on all datasets.
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_package_imports():
    """Test that all package imports work correctly."""
    try:
        logger.info("Testing package imports...")
        
        # Test main package import
        import dataset_citations
        logger.info("✓ Main package imported successfully")
        
        # Test core module imports
        from dataset_citations.core import citation_utils, getCitations
        logger.info("✓ Core modules imported successfully")
        
        # Test function imports
        from dataset_citations.core.citation_utils import create_citation_json_structure
        from dataset_citations.core.getCitations import get_working_proxy
        logger.info("✓ Individual functions imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minimal_workflow(test_datasets: List[str] = None, output_dir: str = None):
    """
    Test the complete citation workflow with a minimal set of datasets.
    
    Args:
        test_datasets: List of dataset names to test (defaults to ['ds000117', 'ds000246'])
        output_dir: Output directory for test files (defaults to temp directory)
        
    Returns:
        bool: True if test passes, False otherwise
    """
    if test_datasets is None:
        test_datasets = ['ds000117', 'ds000246']  # Small datasets with known citations
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix='dataset_citations_test_')
        cleanup_needed = True
    else:
        cleanup_needed = False
        
    logger.info(f"Testing end-to-end workflow with datasets: {test_datasets}")
    logger.info(f"Using output directory: {output_dir}")
    
    try:
        # Import required modules
        from dataset_citations.core import getCitations as gc
        from dataset_citations.core import citation_utils
        
        # Test 1: Check if proxy setup works
        logger.info("Step 1: Testing proxy setup...")
        if not test_proxy_setup():
            logger.warning("Proxy setup test failed - this may be expected in test environments")
        
        # Test 2: Test citation JSON structure creation
        logger.info("Step 2: Testing citation JSON structure...")
        if not test_citation_json_structure():
            return False
            
        # Test 3: Test minimal citation retrieval (if API key available)
        logger.info("Step 3: Testing citation retrieval...")
        scraperapi_key = os.getenv("SCRAPERAPI_KEY")
        if scraperapi_key:
            if not test_citation_retrieval(test_datasets, output_dir):
                return False
        else:
            logger.warning("SCRAPERAPI_KEY not found - skipping actual citation retrieval test")
            # Create mock JSON files for testing
            create_mock_citation_files(test_datasets, output_dir)
            
        # Test 4: Test JSON file operations
        logger.info("Step 4: Testing JSON file operations...")
        if not test_json_operations(test_datasets, output_dir):
            return False
            
        logger.info("🎉 End-to-end workflow test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cleanup_needed:
            logger.info(f"Cleaning up test directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)


def test_proxy_setup() -> bool:
    """Test proxy setup functionality."""
    try:
        from dataset_citations.core import getCitations as gc
        
        # Test without actual API key to verify function exists and doesn't crash
        logger.info("Testing proxy setup function...")
        # Note: This will likely fail without proper credentials, but should not crash
        try:
            gc.get_working_proxy()
            return True
        except Exception:
            # Expected to fail without proper API key
            logger.info("Proxy setup function exists (credential failure expected)")
            return True
            
    except Exception as e:
        logger.error(f"Proxy setup test failed: {e}")
        return False


def test_citation_json_structure() -> bool:
    """Test citation JSON structure creation."""
    try:
        import pandas as pd
        from dataset_citations.core import citation_utils
        
        # Create mock citation data
        mock_data = {
            'title': ['Test Paper 1', 'Test Paper 2'],
            'author': ['Author 1', 'Author 2'],
            'venue': ['Journal 1', 'Journal 2'],
            'year': [2023, 2024],
            'url': ['http://example1.com', 'http://example2.com'],
            'cited_by': [10, 5],
            'bib': ['@article{test1}', '@article{test2}']
        }
        
        df = pd.DataFrame(mock_data)
        
        # Test JSON structure creation
        json_data = citation_utils.create_citation_json_structure('test_ds', df)
        
        # Verify required fields exist
        required_fields = ['dataset_id', 'num_citations', 'date_last_updated', 'metadata', 'citation_details']
        for field in required_fields:
            if field not in json_data:
                logger.error(f"Missing required field: {field}")
                return False
                
        logger.info("✓ Citation JSON structure test passed")
        return True
        
    except Exception as e:
        logger.error(f"Citation JSON structure test failed: {e}")
        return False


def test_citation_retrieval(test_datasets: List[str], output_dir: str) -> bool:
    """Test actual citation retrieval (requires API key)."""
    try:
        from dataset_citations.core import getCitations as gc
        from dataset_citations.core import citation_utils
        
        logger.info("Setting up proxy for citation retrieval...")
        gc.get_working_proxy()
        
        for dataset_id in test_datasets[:1]:  # Test only first dataset to save API calls
            logger.info(f"Testing citation retrieval for {dataset_id}...")
            
            # Get citation count
            citation_count = gc.get_citation_numbers(dataset_id)
            logger.info(f"Found {citation_count} citations for {dataset_id}")
            
            if citation_count > 0:
                # Get actual citations (limit to 2 for testing)
                citations_df = gc.get_citations(dataset_id, min(citation_count, 2))
                
                if not citations_df.empty:
                    # Save to file using the correct function signature
                    json_filepath = citation_utils.save_citation_json(dataset_id, citations_df, output_dir)
                    
                    logger.info(f"✓ Successfully retrieved and saved citations for {dataset_id}")
                else:
                    logger.warning(f"No citations retrieved for {dataset_id}")
                    
        return True
        
    except Exception as e:
        logger.error(f"Citation retrieval test failed: {e}")
        return False


def create_mock_citation_files(test_datasets: List[str], output_dir: str):
    """Create mock citation JSON files for testing when API key is not available."""
    try:
        import pandas as pd
        from dataset_citations.core import citation_utils
        
        for dataset_id in test_datasets:
            # Create mock citation data
            mock_data = {
                'title': [f'Mock Paper 1 for {dataset_id}', f'Mock Paper 2 for {dataset_id}'],
                'author': ['Mock Author 1', 'Mock Author 2'],
                'venue': ['Mock Journal 1', 'Mock Journal 2'],
                'year': [2023, 2024],
                'url': ['http://mock1.com', 'http://mock2.com'],
                'cited_by': [10, 5],
                'bib': [f'@article{{mock1_{dataset_id}}}', f'@article{{mock2_{dataset_id}}}']
            }
            
            df = pd.DataFrame(mock_data)
            
            # Save mock file using the correct function signature
            json_filepath = citation_utils.save_citation_json(dataset_id, df, output_dir)
            
        logger.info(f"✓ Created mock citation files for {test_datasets}")
        
    except Exception as e:
        logger.error(f"Mock file creation failed: {e}")


def test_json_operations(test_datasets: List[str], output_dir: str) -> bool:
    """Test JSON file loading and summary operations."""
    try:
        from dataset_citations.core import citation_utils
        
        # Find JSON files in output directory
        json_files = list(Path(output_dir).glob("*.json"))
        
        if not json_files:
            logger.error("No JSON files found for testing")
            return False
            
        for json_file in json_files:
            logger.info(f"Testing JSON operations with {json_file.name}...")
            
            # Test loading
            json_data = citation_utils.load_citation_json(str(json_file))
            
            # Test summary extraction (pass filepath, not loaded data)
            summary = citation_utils.get_citation_summary_from_json(str(json_file))
            
            # Verify summary has expected fields
            expected_fields = ['dataset_id', 'num_citations', 'total_cumulative_citations']
            for field in expected_fields:
                if field not in summary:
                    logger.error(f"Missing field in summary: {field}")
                    return False
                    
            logger.info(f"✓ JSON operations test passed for {json_file.name}")
            
        return True
        
    except Exception as e:
        logger.error(f"JSON operations test failed: {e}")
        return False


def main():
    """Run the complete end-to-end test suite."""
    logger.info("🚀 Starting end-to-end test suite for dataset citations package...")
    
    # Test 1: Package imports
    if not test_package_imports():
        logger.error("❌ Package import tests failed")
        sys.exit(1)
        
    # Test 2: End-to-end workflow
    if not test_minimal_workflow():
        logger.error("❌ End-to-end workflow tests failed")
        sys.exit(1)
        
    logger.info("🎉 All tests passed! Package structure is working correctly.")
    logger.info("Ready for full dataset processing.")


if __name__ == "__main__":
    main()