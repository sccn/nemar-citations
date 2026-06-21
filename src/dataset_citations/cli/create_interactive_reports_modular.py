"""
CLI command for creating interactive HTML reports using the modular dashboard system.

This replaces the monolithic create_interactive_reports.py with a cleaner implementation.
"""

import argparse
import logging
from pathlib import Path

from dataset_citations.dashboard import DashboardGenerator


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point for the dashboard generation CLI."""
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML dashboards for dataset citation analysis"
    )

    parser.add_argument(
        "--results-dir",
        type=str,
        default="dashboard_data",
        help="Directory containing analysis results (default: dashboard_data)",
    )

    parser.add_argument(
        "--citations-dir",
        type=str,
        default="citations/json_opencite",
        help="Directory containing citation JSON files (default: citations/json_opencite)",
    )

    parser.add_argument(
        "--datasets-dir",
        type=str,
        default="datasets",
        help="Directory containing dataset metadata (default: datasets)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="interactive_reports",
        help="Directory to save generated reports (default: interactive_reports)",
    )

    parser.add_argument(
        "--dashboard-type",
        choices=["nemar", "standard", "minimal"],
        default="nemar",
        help="Type of dashboard to generate (default: nemar)",
    )

    parser.add_argument(
        "--no-lazy-load",
        action="store_true",
        help="Embed all data in HTML instead of using lazy loading",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Create dashboard generator
    generator = DashboardGenerator(
        results_dir=Path(args.results_dir),
        output_dir=Path(args.output_dir),
        citations_dir=Path(args.citations_dir),
        datasets_dir=Path(args.datasets_dir),
    )

    # Generate appropriate dashboard
    if args.dashboard_type == "minimal":
        output_file = generator.generate_minimal_dashboard()
    else:
        output_file = generator.generate_dashboard(
            dashboard_type=args.dashboard_type, lazy_load=not args.no_lazy_load
        )

    logging.info(f"Dashboard generated successfully: {output_file}")


if __name__ == "__main__":
    main()
