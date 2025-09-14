"""
Data aggregation module for collecting and organizing analysis results.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import csv
from datetime import datetime


class DataAggregator:
    """Aggregates data from various analysis results for dashboard generation."""

    def __init__(
        self,
        results_dir: Path,
        citations_dir: Optional[Path] = None,
        datasets_dir: Optional[Path] = None,
    ):
        """
        Initialize data aggregator.

        Args:
            results_dir: Directory containing analysis results
            citations_dir: Optional directory containing citation JSON files
            datasets_dir: Optional directory containing dataset metadata
        """
        self.results_dir = Path(results_dir)
        self.citations_dir = Path(citations_dir) if citations_dir else None
        self.datasets_dir = Path(datasets_dir) if datasets_dir else None
        self.logger = logging.getLogger(__name__)

    def aggregate_all_data(self) -> Dict[str, Any]:
        """
        Aggregate all available data from analysis results.

        Returns:
            Dictionary containing all aggregated data
        """
        data = {
            "network_analysis": self._load_network_analysis(),
            "temporal_analysis": self._load_temporal_analysis(),
            "theme_analysis": self._load_theme_analysis(),
            "citation_similarities": self._load_citation_similarities(),
            "summary_stats": self._calculate_summary_stats(),
            "metadata": self._get_metadata(),
        }

        return data

    def aggregate_minimal_data(self) -> Dict[str, Any]:
        """
        Aggregate minimal data for testing purposes.

        Returns:
            Dictionary containing minimal data
        """
        return {
            "summary_stats": self._calculate_summary_stats(),
            "metadata": self._get_metadata(),
        }

    def _load_network_analysis(self) -> Dict[str, Any]:
        """Load network analysis results."""
        network_data = {}
        network_dir = self.results_dir / "network_analysis"

        if network_dir.exists():
            # Load CSV files
            csv_files = [
                "author_influence.csv",
                "bridge_papers.csv",
                "dataset_co_citations.csv",
                "multi_dataset_citations.csv",
                "dataset_popularity.csv",
                "citation_impact_rankings.csv",
            ]

            for csv_file in csv_files:
                file_path = network_dir / csv_file
                if file_path.exists():
                    try:
                        network_data[csv_file.replace(".csv", "")] = (
                            self._read_csv_to_dict(file_path)
                        )
                        self.logger.info(f"Loaded network analysis: {csv_file}")
                    except Exception as e:
                        self.logger.warning(f"Could not load {csv_file}: {e}")

        return network_data

    def _load_temporal_analysis(self) -> Dict[str, Any]:
        """Load temporal analysis results."""
        temporal_data = {}
        temporal_dir = self.results_dir / "temporal_analysis"

        if temporal_dir.exists():
            # Load temporal CSV files
            for csv_file in temporal_dir.glob("*.csv"):
                try:
                    temporal_data[csv_file.stem] = self._read_csv_to_dict(csv_file)
                    self.logger.info(f"Loaded temporal analysis: {csv_file.name}")
                except Exception as e:
                    self.logger.warning(f"Could not load {csv_file}: {e}")

        return temporal_data

    def _load_theme_analysis(self) -> Dict[str, Any]:
        """Load theme analysis results."""
        theme_data = {}
        theme_dir = self.results_dir / "theme_analysis"

        if theme_dir.exists():
            # Load theme CSV files
            for csv_file in theme_dir.glob("*.csv"):
                try:
                    theme_data[csv_file.stem] = self._read_csv_to_dict(csv_file)
                    self.logger.info(f"Loaded theme analysis: {csv_file.name}")
                except Exception as e:
                    self.logger.warning(f"Could not load {csv_file}: {e}")

        return theme_data

    def _load_citation_similarities(self) -> List[Dict[str, Any]]:
        """Load citation similarity data if available."""
        similarities = []

        # Check for similarity files in results directory
        for sim_file in self.results_dir.glob("*similarities*.csv"):
            try:
                similarities.extend(self._read_csv_to_dict(sim_file))
                self.logger.info(f"Loaded similarities: {sim_file.name}")
            except Exception as e:
                self.logger.warning(f"Could not load similarities: {e}")

        return similarities

    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics from available data."""
        stats = {
            "total_datasets": 0,
            "total_citations": 0,
            "high_confidence_citations": 0,
            "bridge_papers": 0,
            "confidence_threshold": 0.4,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Count datasets
        if self.citations_dir and self.citations_dir.exists():
            json_files = list(self.citations_dir.glob("*.json"))
            stats["total_datasets"] = len(json_files)

            # Count citations
            for json_file in json_files:
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)
                        citations = data.get("citations", [])
                        stats["total_citations"] += len(citations)

                        # Count high-confidence citations
                        high_conf = [
                            c
                            for c in citations
                            if c.get("confidence_score", 0)
                            >= stats["confidence_threshold"]
                        ]
                        stats["high_confidence_citations"] += len(high_conf)
                except Exception as e:
                    self.logger.warning(f"Could not process {json_file}: {e}")

        # Count bridge papers from network analysis
        bridge_file = self.results_dir / "network_analysis" / "bridge_papers.csv"
        if bridge_file.exists():
            try:
                bridge_data = self._read_csv_to_dict(bridge_file)
                stats["bridge_papers"] = len(bridge_data)
            except Exception:
                pass

        return stats

    def _get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the analysis."""
        return {
            "generator": "NEMAR Dataset Citations Analysis",
            "version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "data_sources": {
                "results_dir": str(self.results_dir),
                "citations_dir": str(self.citations_dir)
                if self.citations_dir
                else None,
                "datasets_dir": str(self.datasets_dir) if self.datasets_dir else None,
            },
        }

    def _read_csv_to_dict(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read CSV file and convert to list of dictionaries."""
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        return data
