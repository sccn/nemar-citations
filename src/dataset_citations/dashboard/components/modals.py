"""
Modal content generation component for dashboard.
"""

from typing import Dict, Any, List
from pathlib import Path
import json
from collections import defaultdict


class ModalGenerator:
    """Generate modal dialog content."""

    def generate_modals(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate dataset details modal content."""
        # Get top datasets from network analysis
        network_data = data.get("network_analysis", {})
        dataset_popularity = network_data.get("dataset_popularity", [])

        # Count datasets with citations
        total_datasets = len(dataset_popularity)

        # Count datasets with actual high-confidence citations
        datasets_with_high_conf = len(
            [
                d
                for d in dataset_popularity
                if int(d.get("high_confidence_citations", 0) or 0) > 0
            ]
        )

        # Calculate coverage percentage based on high-confidence citations
        coverage = (
            f"{(datasets_with_high_conf / total_datasets * 100):.0f}%"
            if total_datasets > 0
            else "0%"
        )

        # Sort by high confidence citations and get top 20
        top_datasets = sorted(
            [
                d
                for d in dataset_popularity
                if int(d.get("high_confidence_citations", 0) or 0) > 0
            ],
            key=lambda x: int(x.get("high_confidence_citations", 0) or 0),
            reverse=True,
        )[:20]

        return {
            "title": "Dataset Analysis Details",
            "content": {
                "total_datasets": total_datasets,
                "with_citations": datasets_with_high_conf,
                "coverage": coverage,
                "top_datasets": top_datasets,
                "description": "Datasets are analyzed from the BIDS (Brain Imaging Data Structure) repository, with citation data collected from Google Scholar and filtered by confidence scores.",
            },
        }

    def _generate_citation_modal(
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        self, data: Dict[str, Any], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate bridge papers modal content."""
        network_data = data.get("network_analysis", {})
        bridge_papers = network_data.get("bridge_papers", [])

        # Sort by number of datasets bridged and get top 20
        top_papers = sorted(
            bridge_papers,
            key=lambda x: int(x.get("num_datasets_bridged", 0)),
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

    def _generate_threshold_modal(self, stats: Dict[str, Any]) -> Dict[str, Any]:
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
                "quality_rate": stats["summary"].get("high_confidence_citations", 0)
                / stats["summary"].get("total_citations", 1)
                * 100
                if stats["summary"].get("total_citations", 0) > 0
                else 0,
            },
        }

    def _get_top_citations_from_json(self, limit: int = 20) -> List[Dict[str, Any]]:
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

        citations_dir = Path("citations/json")
        if not citations_dir.exists():
            return []

        # Aggregate all high-confidence citations
        for json_file in citations_dir.glob("*.json"):
            dataset_id = json_file.stem.replace("_citations", "")

            try:
                with open(json_file, "r") as f:
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
            except Exception:
                continue

        # Sort by citation impact and return top N
        sorted_citations = sorted(
            citation_impacts.values(), key=lambda x: x["citation_impact"], reverse=True
        )

        return sorted_citations[:limit]
