"""
Data aggregation module for collecting and organizing analysis results.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataAggregator:
    """Aggregates data from various analysis results for dashboard generation."""

    def __init__(
        self,
        results_dir: Path,
        citations_dir: Optional[Path] = None,
        datasets_dir: Optional[Path] = None,
        citations_opencite_dir: Optional[Path] = None,
    ):
        """
        Initialize data aggregator.

        Args:
            results_dir: Directory containing analysis results
            citations_dir: Optional directory containing citation JSON files
            datasets_dir: Optional directory containing dataset metadata
            citations_opencite_dir: Optional directory containing opencite-
                produced citation JSON files (Phase 3 side-by-side output).
                If None, the aggregator auto-detects `citations/json_opencite`
                next to `citations_dir`.
        """
        self.results_dir = Path(results_dir)
        # Check if dashboard_data exists as primary location
        dashboard_data_dir = Path("dashboard_data")
        if dashboard_data_dir.exists() and not self.results_dir.exists():
            self.results_dir = dashboard_data_dir
            self.logger = logging.getLogger(__name__)
            self.logger.info("Using dashboard_data directory as primary source")

        self.citations_dir = Path(citations_dir) if citations_dir else None
        self.datasets_dir = Path(datasets_dir) if datasets_dir else None
        self.citations_opencite_dir = self._resolve_opencite_dir(citations_opencite_dir)
        self.logger = logging.getLogger(__name__)

    def _resolve_opencite_dir(self, explicit: Optional[Path]) -> Optional[Path]:
        """Pick the opencite citations dir: explicit > sibling > None."""
        if explicit is not None:
            p = Path(explicit)
            return p if p.exists() else None
        if self.citations_dir is not None:
            sibling = self.citations_dir.parent / "json_opencite"
            if sibling.exists():
                return sibling
        return None

    def summary_by_backend(self) -> Dict[str, Dict[str, int]]:
        """Return per-dataset citation counts split by discovery backend.

        Shape: `{dataset_id: {"scholarly": N, "opencite": M}}`. Used by Phase 3
        side-by-side reporting to confirm opencite parity before scholarly
        is retired in Phase 4. Datasets that appear in only one directory
        get a 0 for the missing backend.
        """
        out: Dict[str, Dict[str, int]] = {}
        if self.citations_dir is not None and self.citations_dir.exists():
            for entry in self._counts_from_dir(self.citations_dir):
                out.setdefault(entry[0], {"scholarly": 0, "opencite": 0})
                out[entry[0]]["scholarly"] = entry[1]
        if (
            self.citations_opencite_dir is not None
            and self.citations_opencite_dir.exists()
        ):
            for entry in self._counts_from_dir(self.citations_opencite_dir):
                out.setdefault(entry[0], {"scholarly": 0, "opencite": 0})
                out[entry[0]]["opencite"] = entry[1]
        return out

    @staticmethod
    def _counts_from_dir(directory: Path):
        """Yield (dataset_id, num_citations) from each *_citations.json."""
        for path in sorted(directory.glob("*_citations.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            dataset_id = payload.get(
                "dataset_id", path.name.removesuffix("_citations.json")
            )
            yield dataset_id, int(payload.get("num_citations") or 0)

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

        # Try new consolidated location first
        network_dir = self.results_dir / "network"
        if not network_dir.exists():
            # Fallback to old location
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
                # Try multiple possible locations
                possible_paths = [
                    network_dir / csv_file,
                    network_dir / "csv_exports" / csv_file,
                    self.results_dir / "network_analysis" / "csv_exports" / csv_file,
                ]

                for file_path in possible_paths:
                    if file_path.exists():
                        try:
                            network_data[csv_file.replace(".csv", "")] = (
                                self._read_csv_to_dict(file_path)
                            )
                            self.logger.info(f"Loaded network analysis: {csv_file}")
                            break
                        except Exception as e:
                            self.logger.warning(f"Could not load {csv_file}: {e}")

        return network_data

    def _load_temporal_analysis(self) -> Dict[str, Any]:
        """Load temporal analysis results."""
        temporal_data = {}

        # Try new consolidated location first
        temporal_dir = self.results_dir / "temporal"
        if not temporal_dir.exists():
            # Fallback to old location
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

        # Try new consolidated location first
        theme_dir = self.results_dir / "themes"
        if not theme_dir.exists():
            # Fallback to old location for compatibility
            theme_dir = self.results_dir / "theme_analysis"

        if theme_dir.exists():
            # Load theme JSON files
            for json_file in theme_dir.glob("*.json"):
                try:
                    with open(json_file) as f:
                        theme_data[json_file.stem] = json.load(f)
                    self.logger.info(f"Loaded theme analysis: {json_file.name}")
                except Exception as e:
                    self.logger.warning(f"Could not load {json_file}: {e}")

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
                    with open(json_file) as f:
                        data = json.load(f)
                        # Try both possible keys for citations
                        citations = data.get(
                            "citation_details", data.get("citations", [])
                        )
                        stats["total_citations"] += len(citations)

                        # Count high-confidence citations
                        high_conf = [
                            c
                            for c in citations
                            if (
                                c.get("confidence_scoring", {}).get(
                                    "confidence_score", 0
                                )
                                or c.get("confidence_score", 0)
                            )
                            >= stats["confidence_threshold"]
                        ]
                        stats["high_confidence_citations"] += len(high_conf)
                except Exception as e:
                    self.logger.warning(f"Could not process {json_file}: {e}")

        # Count bridge papers from network analysis
        bridge_file = self.results_dir / "network" / "bridge_papers.csv"
        if not bridge_file.exists():
            # Fallback to old location
            bridge_file = (
                self.results_dir
                / "network_analysis"
                / "csv_exports"
                / "bridge_papers.csv"
            )

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
                "citations_dir": (
                    str(self.citations_dir) if self.citations_dir else None
                ),
                "datasets_dir": str(self.datasets_dir) if self.datasets_dir else None,
            },
        }

    def _read_csv_to_dict(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read CSV file and convert to list of dictionaries."""
        data = []
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        return data
