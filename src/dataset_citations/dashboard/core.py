"""
Core dashboard generator orchestrating all components.
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from .assets.manager import AssetManager
from .components.charts import ChartGenerator
from .components.modals import ModalGenerator
from .components.networks import NetworkGenerator
from .components.statistics import StatisticsGenerator
from .components.themes import ThemeGenerator
from .data.aggregator import DataAggregator
from .templates.builder import TemplateBuilder


class DashboardGenerator:
    """Main orchestrator for dashboard generation."""

    def __init__(
        self,
        results_dir: Path,
        output_dir: Path,
        citations_dir: Optional[Path] = None,
        datasets_dir: Optional[Path] = None,
    ):
        """
        Initialize dashboard generator.

        Args:
            results_dir: Directory containing analysis results
            output_dir: Directory for output files
            citations_dir: Optional directory containing citation JSON files
            datasets_dir: Optional directory containing dataset metadata
        """
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.citations_dir = Path(citations_dir) if citations_dir else None
        self.datasets_dir = Path(datasets_dir) if datasets_dir else None

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.data_aggregator = DataAggregator(
            results_dir=self.results_dir,
            citations_dir=self.citations_dir,
            datasets_dir=self.datasets_dir,
        )
        self.stats_generator = StatisticsGenerator()
        self.chart_generator = ChartGenerator()
        # Pass embeddings directory to NetworkGenerator
        embeddings_dir = self.results_dir.parent / "embeddings"
        if not embeddings_dir.exists():
            embeddings_dir = Path("embeddings")  # Fallback to current directory
        self.network_generator = NetworkGenerator(embeddings_dir=embeddings_dir)
        self.theme_generator = ThemeGenerator()
        self.modal_generator = ModalGenerator()
        self.template_builder = TemplateBuilder()
        self.asset_manager = AssetManager(output_dir=self.output_dir)

        self.logger = logging.getLogger(__name__)

    def generate_dashboard(
        self,
        dashboard_type: str = "nemar",
        include_full_data: bool = False,
        lazy_load: bool = True,
    ) -> Path:
        """
        Generate the complete dashboard.

        Args:
            dashboard_type: Type of dashboard ("nemar" or "standard")
            include_full_data: Whether to embed full data in HTML
            lazy_load: Whether to use lazy loading for large datasets

        Returns:
            Path to generated dashboard HTML file
        """
        self.logger.info(f"Generating {dashboard_type} dashboard")

        # Step 1: Aggregate all data
        self.logger.info("Aggregating data from analysis results")
        data = self.data_aggregator.aggregate_all_data()

        # Step 2: Generate statistics
        self.logger.info("Generating statistics")
        stats = self.stats_generator.generate_statistics(data)

        # Step 3: Generate chart configurations
        self.logger.info("Generating chart configurations")
        charts = self.chart_generator.generate_all_charts(data)

        # Step 4: Generate network visualizations
        self.logger.info("Generating network visualizations")
        networks = self.network_generator.generate_networks(data)

        # Step 5: Generate theme visualizations
        self.logger.info("Generating theme visualizations")
        themes = self.theme_generator.generate_themes(data)

        # Step 6: Generate modal content
        self.logger.info("Generating modal content")
        modals = self.modal_generator.generate_modals(data, stats)

        # Step 7: Copy assets and prepare data files
        self.logger.info("Managing assets")
        if lazy_load:
            data_file = self.asset_manager.create_data_file(data)
        else:
            data_file = None

        self.asset_manager.copy_support_files()
        # Theme images now use relative paths, no need to copy

        # Step 8: Build final HTML
        self.logger.info("Building final HTML")
        html_content = self.template_builder.build_dashboard(
            dashboard_type=dashboard_type,
            stats=stats,
            charts=charts,
            networks=networks,
            themes=themes,
            modals=modals,
            data=data if not lazy_load else None,
            data_file=data_file,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Step 9: Write output file
        output_file = (
            self.output_dir / f"dataset_citations_dashboard_{dashboard_type}.html"
        )
        output_file.write_text(html_content, encoding="utf-8")

        self.logger.info(f"Dashboard generated successfully: {output_file}")
        return output_file

    def generate_minimal_dashboard(self) -> Path:
        """Generate a minimal dashboard for testing."""
        self.logger.info("Generating minimal test dashboard")

        # Use minimal data for fast generation
        data = self.data_aggregator.aggregate_minimal_data()
        stats = self.stats_generator.generate_statistics(data)

        html_content = self.template_builder.build_minimal_dashboard(
            stats=stats, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        output_file = self.output_dir / "dataset_citations_dashboard_minimal.html"
        output_file.write_text(html_content, encoding="utf-8")

        return output_file
