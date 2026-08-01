"""
Modal content generation component for dashboard.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModalGenerator:
    """Generate modal dialog content."""

    def generate_modals(
        self, data: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate modal content for detail views.

        Args:
            data: Aggregated data from DataAggregator
            stats: Generated statistics

        Returns:
            Dictionary containing modal configurations
        """
        return {
            "datasets": self._generate_dataset_modal(data, stats),
            "citations": self._generate_citation_modal(data, stats),
            "bridges": self._generate_bridge_modal(data, stats),
            "threshold": self._generate_threshold_modal(stats),
        }

    def _generate_dataset_modal(
        self, data: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate dataset details modal content."""
        # Get top datasets from network analysis
        network_data = data.get("network_analysis", {})
        dataset_popularity = network_data.get("dataset_popularity", [])

        # Count datasets with citations
        total_datasets = len(dataset_popularity)

        # Count datasets with high-confidence citations
        datasets_with_citations = len(
            [
                d
                for d in dataset_popularity
                if int(d.get("high_conf_citations", 0) or 0) > 0
            ]
        )

        # Calculate coverage percentage based on datasets with citations
        coverage = (
            f"{(datasets_with_citations / total_datasets * 100):.0f}%"
            if total_datasets > 0
            else "0%"
        )

        # Sort by high_conf_citations and get top 20, and format for template
        filtered_datasets = [
            d
            for d in dataset_popularity
            if int(d.get("high_conf_citations", 0) or 0) > 0
        ]

        # Load dataset names from metadata files
        dataset_names = self._load_dataset_names()

        top_datasets = []
        for ds in sorted(
            filtered_datasets,
            key=lambda x: int(x.get("high_conf_citations", 0) or 0),
            reverse=True,
        )[:20]:
            dataset_id = ds.get("dataset_id", "")
            high_conf = int(ds.get("high_conf_citations", 0) or 0)
            low_conf = int(ds.get("low_conf_citations", 0) or 0)
            total = int(ds.get("total_citations", 0) or 0)

            top_datasets.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_names.get(
                        dataset_id, dataset_id
                    ),  # Use actual dataset name from metadata
                    "high_confidence_citations": high_conf,
                    "low_confidence_citations": low_conf,
                    "total_citations": total,
                }
            )

        return {
            "title": "Dataset Analysis Details",
            "content": {
                "total_datasets": total_datasets,
                "with_citations": datasets_with_citations,
                "coverage": coverage,
                "top_datasets": top_datasets,
                "description": "Datasets are analyzed from the BIDS (Brain Imaging Data Structure) repository, with citation data collected from Google Scholar and filtered by confidence scores.",
            },
        }

    def _generate_citation_modal(
        self, data: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate citation details modal content."""
        high_conf = stats["summary"].get("high_confidence_citations", 0)
        total = stats["summary"].get("total_citations", 0)
        low_conf = total - high_conf
        percentage = round((high_conf / total * 100) if total > 0 else 0, 1)

        # Get top cited papers from citation impact rankings
        network_data = data.get("network_analysis", {})
        citation_rankings = network_data.get("citation_impact_rankings", [])

        # If we don't have enough from CSV, load from JSON files
        if len(citation_rankings) < 20:
            top_citations = self._get_top_citations_from_json(20)
        else:
            # Sort by citation impact and get top 20
            top_citations = sorted(
                citation_rankings,
                key=lambda x: int(x.get("citation_impact", 0)),
                reverse=True,
            )[:20]

        return {
            "title": "Citation Analysis",
            "content": {
                "high_confidence": high_conf,
                "low_confidence": low_conf,
                "total": total,
                "percentage": percentage,
                "threshold": 0.4,
                "quality_rate": percentage,  # Same as percentage for high-confidence
                "top_citations": top_citations,
            },
        }

    def _generate_bridge_modal(
        self, data: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate bridge papers modal content."""
        network_data = data.get("network_analysis", {})
        bridge_papers = network_data.get("bridge_papers", [])

        # Fix field names and sort by number of datasets bridged
        fixed_papers = [
            {
                "bridge_paper_title": paper.get("title", "Unknown Title"),
                "bridge_paper_author": paper.get("author", "Unknown Authors"),
                "bridge_paper_year": paper.get("year", ""),
                "num_datasets_bridged": int(paper.get("num_datasets", 0)),
                "datasets_bridged": (
                    paper.get("datasets_bridged", "").split(",")
                    if paper.get("datasets_bridged")
                    else []
                ),
            }
            for paper in bridge_papers
        ]

        # Sort by number of datasets bridged and get top 20
        top_papers = sorted(
            fixed_papers,
            key=lambda x: x["num_datasets_bridged"],
            reverse=True,
        )[:20]

        return {
            "title": "Research Bridge Papers",
            "content": {
                "total": len(bridge_papers),
                "top_papers": top_papers,
                "description": "Bridge papers are publications that cite multiple BIDS datasets, connecting different research areas and facilitating cross-domain knowledge transfer in neuroscience.",
            },
        }

    def _generate_threshold_modal(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Generate confidence threshold explanation modal."""
        return {
            "title": "Confidence Threshold Information",
            "content": {
                "threshold": 0.4,
                "description": "Citations must have a confidence score of 0.4 or higher to be included in analysis.",
                "model": "Qwen3-Embedding-0.6B",
                "method": "Sentence-transformer similarity",
                "comparison": "Dataset descriptions vs citation abstracts",
                "validation": "Manual review sample",
                "quality_rate": (
                    stats["summary"].get("high_confidence_citations", 0)
                    / stats["summary"].get("total_citations", 1)
                    * 100
                    if stats["summary"].get("total_citations", 0) > 0
                    else 0
                ),
            },
        }

    def _get_top_citations_from_json(self, limit: int = 20) -> list[dict[str, Any]]:
        """Load top citations directly from JSON files."""
        citation_impacts = defaultdict(
            lambda: {
                "citation_impact": 0,
                "citation_title": "",
                "citation_author": "",
                "citation_year": "",
                "confidence_score": 0,
                "datasets": [],
            }
        )

        citations_dir = Path("citations/json_opencite")
        if not citations_dir.exists():
            return []

        # Aggregate all high-confidence citations
        for json_file in citations_dir.glob("*.json"):
            dataset_id = json_file.stem.replace("_citations", "")

            try:
                with open(json_file) as f:
                    data = json.load(f)

                for citation in data.get("citation_details", []):
                    conf_score = citation.get("confidence_scoring", {}).get(
                        "confidence_score", 0
                    )
                    if conf_score >= 0.4:  # Only high-confidence
                        title = citation.get("title", "")
                        if title:
                            # Use title as key to aggregate across datasets
                            citation_impacts[title]["citation_impact"] = max(
                                citation_impacts[title]["citation_impact"],
                                citation.get("cited_by", 0),
                            )
                            citation_impacts[title]["citation_title"] = title
                            citation_impacts[title]["citation_author"] = citation.get(
                                "author", ""
                            )
                            citation_impacts[title]["citation_year"] = citation.get(
                                "year", ""
                            )
                            citation_impacts[title]["confidence_score"] = max(
                                citation_impacts[title]["confidence_score"], conf_score
                            )
                            citation_impacts[title]["datasets"].append(dataset_id)
            except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning("skipping %s while ranking citations: %s", json_file, e)
                continue

        # Sort by citation impact and return top N
        sorted_citations = sorted(
            citation_impacts.values(), key=lambda x: x["citation_impact"], reverse=True
        )

        return sorted_citations[:limit]

    def _load_dataset_names(self) -> dict[str, str]:
        """Load dataset names from metadata JSON files."""
        dataset_names = {}
        datasets_dir = Path("datasets")

        if not datasets_dir.exists():
            return dataset_names

        for json_file in datasets_dir.glob("*_datasets.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    dataset_id = data.get("dataset_id", "")
                    dataset_desc = data.get("dataset_description")
                    if dataset_desc and isinstance(dataset_desc, dict):
                        dataset_name = dataset_desc.get("Name", dataset_id)
                    else:
                        dataset_name = dataset_id
                    if dataset_id:
                        dataset_names[dataset_id] = dataset_name
            except (OSError, json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.warning(
                    "skipping %s while reading dataset name: %s", json_file, e
                )
                continue

        return dataset_names
