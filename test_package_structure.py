#!/usr/bin/env python3
"""
Test script to verify the new package structure works correctly.
"""

def test_package_imports():
    """Test that all package imports work correctly."""
    try:
        # Test main package import
        import dataset_citations
        print("✓ dataset_citations package imported successfully")
        
        # Test submodule imports
        from dataset_citations import citation_utils, getCitations
        print("✓ citation_utils and getCitations modules imported successfully")
        
        # Test function imports
        from dataset_citations.citation_utils import create_citation_json_structure
        from dataset_citations.getCitations import get_working_proxy
        print("✓ Individual functions imported successfully")
        
        # Test package attributes
        print(f"✓ Package version: {dataset_citations.__version__}")
        print(f"✓ Available modules: {[m for m in dir(dataset_citations) if not m.startswith('_')]}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing new package structure...")
    success = test_package_imports()
    
    if success:
        print("\n🎉 All package structure tests passed!")
        print("Phase 1 package refactoring completed successfully.")
    else:
        print("\n❌ Package structure tests failed.")
        exit(1)