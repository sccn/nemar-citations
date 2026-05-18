"""
Tests for the dashboard data aggregator module.
"""

import csv
import json
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from dataset_citations.dashboard.data.aggregator import DataAggregator


class TestDataAggregator(TestCase):
    """Test the DataAggregator class."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir) / "results"
        self.citations_dir = Path(self.temp_dir) / "citations"
        self.datasets_dir = Path(self.temp_dir) / "datasets"

        # Create directories
        self.results_dir.mkdir(parents=True)
        self.citations_dir.mkdir(parents=True)
        self.datasets_dir.mkdir(parents=True)

        # Create test data
        self._create_test_data()

        # Initialize aggregator
        self.aggregator = DataAggregator(
            results_dir=self.results_dir,
            citations_dir=self.citations_dir,
            datasets_dir=self.datasets_dir,
        )

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def _create_test_data(self):
        """Create test data files."""
        # Create network analysis directory and files
        network_dir = self.results_dir / "network_analysis"
        network_dir.mkdir()

        # Create csv_exports subdirectory for bridge papers (matches expected path)
        csv_exports_dir = network_dir / "csv_exports"
        csv_exports_dir.mkdir()

        # Bridge papers CSV in expected location
        bridge_papers = [
            {"paper_id": "1", "title": "Test Paper 1", "confidence": "0.8"},
            {"paper_id": "2", "title": "Test Paper 2", "confidence": "0.7"},
        ]
        self._write_csv(csv_exports_dir / "bridge_papers.csv", bridge_papers)
        # Also write to main directory for backward compatibility
        self._write_csv(network_dir / "bridge_papers.csv", bridge_papers)

        # Dataset popularity CSV
        popularity = [
            {"dataset_id": "ds001", "citations": "10"},
            {"dataset_id": "ds002", "citations": "5"},
        ]
        self._write_csv(network_dir / "dataset_popularity.csv", popularity)

        # Create citation JSON files
        citation1 = {
            "dataset_id": "ds001",
            "citations": [
                {"title": "Citation 1", "confidence_score": 0.8},
                {"title": "Citation 2", "confidence_score": 0.3},
                {"title": "Citation 3", "confidence_score": 0.6},
            ],
        }
        with open(self.citations_dir / "ds001.json", "w") as f:
            json.dump(citation1, f)

        citation2 = {
            "dataset_id": "ds002",
            "citations": [
                {"title": "Citation 4", "confidence_score": 0.9},
                {"title": "Citation 5", "confidence_score": 0.2},
            ],
        }
        with open(self.citations_dir / "ds002.json", "w") as f:
            json.dump(citation2, f)

    def _write_csv(self, path: Path, data: list):
        """Helper to write CSV data."""
        if not data:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    def test_aggregate_all_data(self):
        """Test aggregating all available data."""
        data = self.aggregator.aggregate_all_data()

        # Check structure
        self.assertIn("network_analysis", data)
        self.assertIn("temporal_analysis", data)
        self.assertIn("theme_analysis", data)
        self.assertIn("summary_stats", data)
        self.assertIn("metadata", data)

        # Check network analysis data
        self.assertIn("bridge_papers", data["network_analysis"])
        self.assertIn("dataset_popularity", data["network_analysis"])
        self.assertEqual(len(data["network_analysis"]["bridge_papers"]), 2)

        # Check summary stats
        stats = data["summary_stats"]
        self.assertEqual(stats["total_datasets"], 2)
        self.assertEqual(stats["total_citations"], 5)
        self.assertEqual(
            stats["high_confidence_citations"], 3
        )  # conf >= 0.4 (0.8, 0.6, 0.9)
        self.assertEqual(stats["bridge_papers"], 2)

    def test_aggregate_minimal_data(self):
        """Test aggregating minimal data for testing."""
        data = self.aggregator.aggregate_minimal_data()

        # Should only have summary stats and metadata
        self.assertIn("summary_stats", data)
        self.assertIn("metadata", data)
        self.assertEqual(len(data), 2)

    def test_calculate_summary_stats(self):
        """Test summary statistics calculation."""
        stats = self.aggregator._calculate_summary_stats()

        self.assertEqual(stats["total_datasets"], 2)
        self.assertEqual(stats["total_citations"], 5)
        self.assertEqual(stats["high_confidence_citations"], 3)  # 0.8, 0.6, 0.9
        self.assertEqual(stats["confidence_threshold"], 0.4)
        self.assertIn("analysis_date", stats)

    def test_load_network_analysis(self):
        """Test loading network analysis data."""
        network_data = self.aggregator._load_network_analysis()

        self.assertIn("bridge_papers", network_data)
        self.assertIn("dataset_popularity", network_data)

        # Check bridge papers data
        bridge_papers = network_data["bridge_papers"]
        self.assertEqual(len(bridge_papers), 2)
        self.assertEqual(bridge_papers[0]["title"], "Test Paper 1")

    def test_read_csv_to_dict(self):
        """Test CSV reading functionality."""
        csv_path = self.results_dir / "test.csv"
        test_data = [{"col1": "val1", "col2": "val2"}, {"col1": "val3", "col2": "val4"}]
        self._write_csv(csv_path, test_data)

        result = self.aggregator._read_csv_to_dict(csv_path)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["col1"], "val1")
        self.assertEqual(result[1]["col2"], "val4")

    def test_empty_directories(self):
        """Test behavior with empty directories."""
        # Create aggregator with empty directories
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()

        aggregator = DataAggregator(results_dir=empty_dir)
        data = aggregator.aggregate_all_data()

        # Should return empty structures
        self.assertEqual(data["network_analysis"], {})
        self.assertEqual(data["temporal_analysis"], {})
        self.assertEqual(data["summary_stats"]["total_datasets"], 0)

    def test_missing_directories(self):
        """Test behavior with missing directories."""
        # Create aggregator with non-existent directories
        missing_dir = Path(self.temp_dir) / "missing"

        aggregator = DataAggregator(
            results_dir=missing_dir, citations_dir=missing_dir / "citations"
        )

        # Should handle gracefully
        data = aggregator.aggregate_all_data()
        self.assertIsNotNone(data)
        self.assertEqual(data["summary_stats"]["total_datasets"], 0)


class TestSummaryByBackend(TestCase):
    """Phase 3: aggregator surfaces per-dataset counts for scholarly vs opencite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.results_dir = Path(self.temp_dir) / "results"
        self.results_dir.mkdir(parents=True)
        self.citations_dir = Path(self.temp_dir) / "citations" / "json"
        self.citations_dir.mkdir(parents=True)
        self.opencite_dir = Path(self.temp_dir) / "citations" / "json_opencite"
        self.opencite_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write(self, directory: Path, dataset_id: str, num: int):
        (directory / f"{dataset_id}_citations.json").write_text(
            json.dumps({"dataset_id": dataset_id, "num_citations": num})
        )

    def test_auto_detects_sibling_opencite_dir(self):
        self._write(self.citations_dir, "ds000117", 75)
        self._write(self.opencite_dir, "ds000117", 100)
        agg = DataAggregator(
            results_dir=self.results_dir, citations_dir=self.citations_dir
        )
        # Auto-detection picked up the sibling directory.
        self.assertEqual(agg.citations_opencite_dir, self.opencite_dir)
        summary = agg.summary_by_backend()
        self.assertEqual(summary, {"ds000117": {"scholarly": 75, "opencite": 100}})

    def test_dataset_only_in_opencite(self):
        # ds-only-in-opencite is what we expect for nm-datasets that the
        # legacy scholarly path never produced output for.
        self._write(self.opencite_dir, "nm000103", 174)
        agg = DataAggregator(
            results_dir=self.results_dir,
            citations_dir=self.citations_dir,
            citations_opencite_dir=self.opencite_dir,
        )
        summary = agg.summary_by_backend()
        self.assertEqual(summary["nm000103"], {"scholarly": 0, "opencite": 174})

    def test_dataset_only_in_scholarly(self):
        self._write(self.citations_dir, "ds002001", 5)
        agg = DataAggregator(
            results_dir=self.results_dir,
            citations_dir=self.citations_dir,
            citations_opencite_dir=self.opencite_dir,
        )
        summary = agg.summary_by_backend()
        self.assertEqual(summary["ds002001"], {"scholarly": 5, "opencite": 0})

    def test_explicit_opencite_dir_overrides_autodetect(self):
        # Explicit param wins even when a sibling exists.
        alt = Path(self.temp_dir) / "alt_opencite"
        alt.mkdir()
        self._write(alt, "ds000117", 42)
        self._write(self.opencite_dir, "ds000117", 999)
        agg = DataAggregator(
            results_dir=self.results_dir,
            citations_dir=self.citations_dir,
            citations_opencite_dir=alt,
        )
        summary = agg.summary_by_backend()
        self.assertEqual(summary["ds000117"]["opencite"], 42)
