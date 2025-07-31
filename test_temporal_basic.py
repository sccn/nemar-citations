#!/usr/bin/env python3
"""Basic test script for temporal analysis functionality."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, "src")

try:
    from dataset_citations.graph.temporal import (
        extract_years_from_citations,
        analyze_citation_timeline,
    )

    print("✅ Imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_extract_years():
    """Test year extraction from a sample citation file."""
    citations_dir = Path("citations/json")

    if not citations_dir.exists():
        print("❌ Citations directory not found")
        return False

    # Get the first JSON file to test
    json_files = list(citations_dir.glob("*.json"))
    if not json_files:
        print("❌ No citation JSON files found")
        return False

    test_file = json_files[0]
    print(f"🔍 Testing with file: {test_file}")

    try:
        years = extract_years_from_citations(test_file)
        print(f"✅ Extracted {len(years)} years: {sorted(set(years))}")
        return True
    except Exception as e:
        print(f"❌ Error extracting years: {e}")
        return False


def test_timeline_analysis():
    """Test timeline analysis on a subset of files."""
    citations_dir = Path("citations/json")

    if not citations_dir.exists():
        print("❌ Citations directory not found")
        return False

    print("🔍 Running timeline analysis on citation data...")

    try:
        timeline_data = analyze_citation_timeline(
            citations_dir, confidence_threshold=0.4
        )

        total_datasets = len(timeline_data["datasets"])
        total_years = len(timeline_data["yearly_totals"])
        total_citations = sum(timeline_data["yearly_totals"].values())

        print("✅ Timeline analysis successful!")
        print(f"   📊 Datasets analyzed: {total_datasets}")
        print(f"   📅 Years with citations: {total_years}")
        print(f"   📖 Total citations: {total_citations}")

        if timeline_data["yearly_totals"]:
            years = sorted(timeline_data["yearly_totals"].keys())
            print(f"   📆 Year range: {min(years)} - {max(years)}")

            # Show top 3 years by citation count
            year_citations = [
                (year, count) for year, count in timeline_data["yearly_totals"].items()
            ]
            year_citations.sort(key=lambda x: x[1], reverse=True)
            print("   🏆 Top 3 years by citations:")
            for i, (year, count) in enumerate(year_citations[:3], 1):
                print(f"      {i}. {year}: {count} citations")

        return True
    except Exception as e:
        print(f"❌ Error in timeline analysis: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Testing Dataset Citations Temporal Analysis")
    print("=" * 50)

    # Test imports
    print("\n1. Testing imports...")

    # Test year extraction
    print("\n2. Testing year extraction...")
    years_ok = test_extract_years()

    # Test timeline analysis
    print("\n3. Testing timeline analysis...")
    timeline_ok = test_timeline_analysis()

    print("\n" + "=" * 50)
    if years_ok and timeline_ok:
        print("✅ All tests passed! Temporal analysis is working.")
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)
