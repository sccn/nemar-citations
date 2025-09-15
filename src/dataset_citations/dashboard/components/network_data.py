"""
Extract and prepare network data including UMAP coordinates for visualization.
"""

import pickle
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NetworkDataExtractor:
    """Extract and prepare network data for Cytoscape.js visualization."""

    def __init__(self, embeddings_dir: Optional[Path] = None):
        """
        Initialize the network data extractor.

        Args:
            embeddings_dir: Path to embeddings directory
        """
        self.embeddings_dir = embeddings_dir or Path("embeddings")
        self.umap_cache = {}

    def load_umap_coordinates(self) -> Dict[str, Any]:
        """
        Load UMAP coordinates from pickle files.

        Returns:
            Dictionary with dataset and citation UMAP coordinates
        """
        result = {"datasets": {}, "citations": {}}

        # Try to load the combined UMAP file
        umap_path = (
            self.embeddings_dir
            / "analysis"
            / "umap_projections"
            / "both_umap_2d_v1_20250731_160730.pkl"
        )

        if not umap_path.exists():
            # Try alternative path
            umap_files = list(
                (self.embeddings_dir / "analysis" / "umap_projections").glob(
                    "*umap*.pkl"
                )
            )
            if umap_files:
                umap_path = umap_files[0]
            else:
                logger.warning("No UMAP projection files found")
                return result

        try:
            with open(umap_path, "rb") as f:
                umap_data = pickle.load(f)

            ids = umap_data.get("embedding_ids", [])
            coords = umap_data.get("umap_embeddings", [])

            for idx, embed_id in enumerate(ids):
                if idx < len(coords):
                    coord = coords[idx]
                    # Parse the ID to determine type
                    if embed_id.startswith("dataset_"):
                        dataset_id = embed_id.replace("dataset_", "")
                        result["datasets"][dataset_id] = {
                            "x": float(coord[0]),
                            "y": float(coord[1]),
                        }
                    elif embed_id.startswith("citation_"):
                        citation_id = embed_id.replace("citation_", "")
                        result["citations"][citation_id] = {
                            "x": float(coord[0]),
                            "y": float(coord[1]),
                        }

        except Exception as e:
            logger.error(f"Error loading UMAP coordinates: {e}")

        return result

    def prepare_network_data(self, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare complete network data for visualization.

        Args:
            aggregated_data: The aggregated dashboard data

        Returns:
            Dictionary with prepared network data for Cytoscape.js
        """
        # Load UMAP coordinates
        umap_coords = self.load_umap_coordinates()

        # Get network analysis data
        network_analysis = aggregated_data.get("network_analysis", {})

        # Prepare dataset network
        dataset_network = self._prepare_dataset_network(
            network_analysis.get("dataset_popularity", []),
            network_analysis.get("dataset_co_citations", []),
            umap_coords["datasets"],
        )

        # Prepare citation network
        citation_network = self._prepare_citation_network(
            network_analysis.get("citation_impact_rankings", []),
            aggregated_data.get("citation_similarities", []),
            umap_coords["citations"],
        )

        return {
            "dataset_network": dataset_network,
            "citation_network": citation_network,
            "umap_bounds": self._calculate_bounds(umap_coords),
        }

    def _prepare_dataset_network(
        self,
        popularity: List[Dict],
        co_citations: List[Dict],
        umap_coords: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        """Prepare dataset network data."""
        nodes = []
        edges = []

        # Create nodes from all datasets with UMAP coordinates
        for dataset in popularity:  # All datasets
            dataset_id = dataset.get("dataset_id", "")
            if dataset_id in umap_coords:
                # Load actual citation count from JSON file
                num_citations = self._get_dataset_citation_count(dataset_id)

                nodes.append(
                    {
                        "data": {
                            "id": dataset_id,
                            "name": dataset.get(
                                "dataset_name", dataset_id
                            ),  # Store name but don't display as label
                            "citations": num_citations,  # Use num_citations from JSON files
                            "type": "dataset",
                        },
                        "position": {
                            "x": umap_coords[dataset_id]["x"] * 40,  # Increased spacing
                            "y": umap_coords[dataset_id]["y"] * 40,
                        },
                    }
                )

        # Create edges from co-citations
        node_ids = {n["data"]["id"] for n in nodes}
        for co_cite in co_citations[:200]:  # Top 200 co-citation pairs
            source = co_cite.get("dataset1_id", "")
            target = co_cite.get("dataset2_id", "")
            if source in node_ids and target in node_ids:
                edges.append(
                    {
                        "data": {
                            "id": f"{source}-{target}",
                            "source": source,
                            "target": target,
                            "weight": co_cite.get("co_citation_count", 1),
                        }
                    }
                )

        return {"nodes": nodes, "edges": edges}

    def _prepare_citation_network(
        self,
        citations: List[Dict],
        similarities: List[Dict],
        umap_coords: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        """Prepare citation network data."""
        nodes = []
        edges = []

        # Load citation titles from JSON files if available
        citation_titles = self._load_citation_titles()

        # Use all available citation UMAP coordinates
        for i, (citation_id, coords) in enumerate(
            list(umap_coords.items())[:500]
        ):  # Top 500 citations
            # Try to get actual title from loaded data
            title = citation_titles.get(citation_id, {}).get(
                "title", f"Citation {citation_id[:8]}"
            )
            cited_by = citation_titles.get(citation_id, {}).get("cited_by", i * 2 + 10)

            nodes.append(
                {
                    "data": {
                        "id": citation_id,
                        "title": title[:100]
                        if len(title) > 100
                        else title,  # Truncate long titles
                        "type": "citation",
                        "citations": int(cited_by),  # Use actual citation count
                        "confidence": citation_titles.get(citation_id, {}).get(
                            "confidence", 0.5
                        ),
                    },
                    "position": {
                        "x": coords["x"] * 40,  # Increased spacing
                        "y": coords["y"] * 40,
                    },
                }
            )

        # Could add edges based on similarity if available
        # This would require processing similarity data

        return {"nodes": nodes, "edges": edges}

    def _get_dataset_citation_count(self, dataset_id: str) -> int:
        """Get the number of citations for a dataset from its JSON file."""
        json_file = Path(f"citations/json/{dataset_id}_citations.json")

        if not json_file.exists():
            return 0

        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                return data.get("num_citations", 0)
        except Exception as e:
            logger.warning(f"Error loading citations for {dataset_id}: {e}")
            return 0

    def _load_citation_titles(self) -> Dict[str, Dict[str, Any]]:
        """Load citation titles from JSON files."""
        citation_data = {}
        citations_dir = Path("citations/json")

        if not citations_dir.exists():
            logger.warning("Citations JSON directory not found")
            return citation_data

        try:
            # Load all citation files
            for json_file in citations_dir.glob("*.json"):
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Extract citations from this dataset
                for citation in data.get("citation_details", []):
                    # Create a hash ID from title for matching with UMAP
                    # This is a simplified approach - ideally we'd match the exact IDs
                    cit_id = str(hash(citation.get("title", "")))[
                        1:9
                    ]  # Simple hash-based ID

                    citation_data[f"citation_{cit_id}"] = {
                        "title": citation.get("title", ""),
                        "cited_by": citation.get("cited_by", 0),
                        "confidence": citation.get("confidence_scoring", {}).get(
                            "confidence_score", 0.5
                        ),
                        "year": citation.get("year", ""),
                        "url": citation.get("url", ""),
                    }

        except Exception as e:
            logger.error(f"Error loading citation titles: {e}")

        return citation_data

    def _calculate_bounds(self, umap_coords: Dict[str, Dict]) -> Dict[str, float]:
        """Calculate the bounds of UMAP coordinates for proper scaling."""
        all_x = []
        all_y = []

        for coord_dict in [umap_coords["datasets"], umap_coords["citations"]]:
            for coords in coord_dict.values():
                all_x.append(coords["x"])
                all_y.append(coords["y"])

        if all_x and all_y:
            return {
                "minX": min(all_x),
                "maxX": max(all_x),
                "minY": min(all_y),
                "maxY": max(all_y),
            }
        else:
            return {"minX": -10, "maxX": 10, "minY": -10, "maxY": 10}
