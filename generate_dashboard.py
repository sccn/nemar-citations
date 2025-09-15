#!/usr/bin/env python
"""
Generate the NEMAR citation dashboard.

This script generates the dashboard using data from the dashboard_data directory.
All dashboard-related data should be consolidated in dashboard_data/.
"""

from pathlib import Path
from dataset_citations.dashboard.core import DashboardGenerator
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_dashboard(
    dashboard_type: str = "nemar", output_dir: str = ".", lazy_load: bool = True
):
    """
    Generate the citation analysis dashboard.

    Args:
        dashboard_type: Type of dashboard to generate ("nemar" or "standard")
        output_dir: Directory to save the dashboard HTML
        lazy_load: Whether to use lazy loading for performance

    Returns:
        Path to the generated dashboard file
    """
    # IMPORTANT: All dashboard data must be in dashboard_data/
    dashboard_data_dir = Path("dashboard_data")
    citations_dir = Path("citations/json")
    datasets_dir = Path("datasets")
    output_path = Path(output_dir)

    # Verify dashboard_data exists
    if not dashboard_data_dir.exists():
        logger.error(f"Dashboard data directory not found: {dashboard_data_dir}")
        logger.info("Please ensure all analysis results are in dashboard_data/")
        sys.exit(1)

    # Check for required subdirectories
    required_dirs = ["network", "temporal", "themes"]
    missing_dirs = [d for d in required_dirs if not (dashboard_data_dir / d).exists()]
    if missing_dirs:
        logger.warning(f"Missing data directories: {missing_dirs}")
        logger.info("Dashboard may have incomplete data")

    # Initialize generator with dashboard_data as the results directory
    generator = DashboardGenerator(
        results_dir=dashboard_data_dir,  # Always use dashboard_data
        output_dir=output_path,
        citations_dir=citations_dir if citations_dir.exists() else None,
        datasets_dir=datasets_dir if datasets_dir.exists() else None,
    )

    # Generate the dashboard
    try:
        dashboard_path = generator.generate_dashboard(
            dashboard_type=dashboard_type, lazy_load=lazy_load
        )
        logger.info(f"Dashboard successfully generated: {dashboard_path}")
        return dashboard_path
    except Exception as e:
        logger.error(f"Failed to generate dashboard: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate NEMAR citation dashboard")
    parser.add_argument(
        "--type",
        choices=["nemar", "standard"],
        default="nemar",
        help="Type of dashboard to generate",
    )
    parser.add_argument(
        "--output-dir", default=".", help="Output directory for the dashboard HTML"
    )
    parser.add_argument(
        "--no-lazy-load",
        action="store_true",
        help="Disable lazy loading (embed all data in HTML)",
    )

    args = parser.parse_args()

    # Generate dashboard
    dashboard_path = generate_dashboard(
        dashboard_type=args.type,
        output_dir=args.output_dir,
        lazy_load=not args.no_lazy_load,
    )

    print("\nDashboard generated successfully!")
    print(f"Open the dashboard: {dashboard_path}")
    print("\nNOTE: All dashboard data is consolidated in dashboard_data/")
    print("      Raw results remain in results/ for analysis purposes")
