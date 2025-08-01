"""
CLI command for exporting network data to external analysis tools.

This module provides comprehensive export functionality for Gephi, Cytoscape,
and other network analysis tools with proper format specifications.
"""

import argparse
import logging
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class ExternalToolExporter:
    """Export network data to various external analysis tools."""

    def __init__(self, output_dir: Path):
        """
        Initialize the exporter.

        Args:
            output_dir: Directory to save exported files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Supported export formats
        self.supported_formats = {
            "gephi": ["gexf", "gdf"],
            "cytoscape": ["cx", "xgmml", "sif"],
            "universal": ["graphml", "gml", "pajek", "csv"],
            "r_igraph": ["ncol", "lgl"],
            "networkx": ["json", "yaml"],
        }

    def load_network_data(
        self, data_source: Union[str, Path, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Load network data from various sources.

        Args:
            data_source: Path to data file, directory, or data dictionary

        Returns:
            Standardized network data structure
        """
        logging.info(f"Loading network data from: {data_source}")

        if isinstance(data_source, dict):
            return data_source

        data_path = Path(data_source)
        network_data = {"nodes": [], "edges": [], "metadata": {}}

        if data_path.is_file():
            # Load from single file
            if data_path.suffix == ".json":
                with open(data_path) as f:
                    raw_data = json.load(f)
                network_data = self._standardize_network_data(raw_data)
            elif data_path.suffix == ".csv":
                network_data = self._load_from_csv(data_path)
            else:
                logging.warning(f"Unsupported file format: {data_path.suffix}")

        elif data_path.is_dir():
            # Load from directory structure
            network_data = self._load_from_directory(data_path)

        else:
            logging.error(f"Data source not found: {data_source}")

        logging.info(
            f"Loaded {len(network_data['nodes'])} nodes and {len(network_data['edges'])} edges"
        )
        return network_data

    def _standardize_network_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize network data to common format."""
        standardized = {"nodes": [], "edges": [], "metadata": {}}

        # Handle different input formats
        if "nodes" in raw_data and "edges" in raw_data:
            # Already in standard format
            standardized = raw_data
        elif "citation_details" in raw_data:
            # From citation JSON format
            standardized = self._convert_citation_data(raw_data)
        elif "elements" in raw_data:
            # From Cytoscape.js format
            standardized = self._convert_cytoscape_js(raw_data)

        return standardized

    def _convert_citation_data(self, citation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert citation JSON data to network format."""
        network_data = {"nodes": [], "edges": [], "metadata": {}}

        dataset_id = citation_data.get("dataset_id", "unknown")

        # Add dataset node
        dataset_node = {
            "id": f"dataset_{dataset_id}",
            "label": dataset_id,
            "type": "dataset",
            "num_citations": citation_data.get("num_citations", 0),
            "total_cumulative_citations": citation_data.get("metadata", {}).get(
                "total_cumulative_citations", 0
            ),
        }
        network_data["nodes"].append(dataset_node)

        # Add citation nodes and edges
        for i, citation in enumerate(citation_data.get("citation_details", [])):
            citation_id = f"citation_{dataset_id}_{i}"

            # Extract confidence score
            confidence_data = citation.get("confidence_scoring", {})
            confidence_score = confidence_data.get("confidence_score", 0.0)

            citation_node = {
                "id": citation_id,
                "label": citation.get("title", f"Citation {i + 1}")[:50],
                "type": "citation",
                "title": citation.get("title", ""),
                "author": citation.get("author", ""),
                "year": citation.get("year"),
                "venue": citation.get("venue", ""),
                "confidence_score": confidence_score,
                "cited_by": citation.get("cited_by", 0),
                "abstract": citation.get("abstract", "")[:200],
            }
            network_data["nodes"].append(citation_node)

            # Add edge between dataset and citation
            edge = {
                "id": f"edge_{dataset_id}_{i}",
                "source": dataset_node["id"],
                "target": citation_id,
                "type": "cites",
                "weight": confidence_score,
            }
            network_data["edges"].append(edge)

        # Add metadata
        network_data["metadata"] = {
            "dataset_id": dataset_id,
            "date_created": datetime.now().isoformat(),
            "confidence_threshold": 0.4,
            "description": f"Citation network for dataset {dataset_id}",
        }

        return network_data

    def _convert_cytoscape_js(self, cyjs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Cytoscape.js format to standard format."""
        network_data = {"nodes": [], "edges": [], "metadata": {}}

        elements = cyjs_data.get("elements", {})

        # Convert nodes
        for node in elements.get("nodes", []):
            node_data = node.get("data", {})
            standardized_node = {
                "id": node_data.get("id"),
                "label": node_data.get("name", node_data.get("id")),
                "type": node_data.get("type", "unknown"),
            }
            # Add all other attributes
            for key, value in node_data.items():
                if key not in ["id", "name"]:
                    standardized_node[key] = value

            network_data["nodes"].append(standardized_node)

        # Convert edges
        for edge in elements.get("edges", []):
            edge_data = edge.get("data", {})
            standardized_edge = {
                "id": edge_data.get("id"),
                "source": edge_data.get("source"),
                "target": edge_data.get("target"),
                "type": edge_data.get("interaction", "unknown"),
            }
            # Add all other attributes
            for key, value in edge_data.items():
                if key not in ["id", "source", "target"]:
                    standardized_edge[key] = value

            network_data["edges"].append(standardized_edge)

        return network_data

    def _load_from_csv(self, csv_path: Path) -> Dict[str, Any]:
        """Load network data from CSV file."""
        network_data = {"nodes": [], "edges": [], "metadata": {}}

        if not PANDAS_AVAILABLE:
            logging.warning("Pandas not available, using basic CSV reader")
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else:
            df = pd.read_csv(csv_path)
            rows = df.to_dict("records")

        # Detect CSV format (nodes vs edges)
        if rows and any(col in ["source", "target"] for col in rows[0].keys()):
            # Edge list format
            node_ids = set()
            for row in rows:
                source = row.get("source")
                target = row.get("target")
                if source and target:
                    node_ids.update([source, target])

                    edge = {
                        "id": f"edge_{len(network_data['edges'])}",
                        "source": source,
                        "target": target,
                    }
                    # Add other columns as edge attributes
                    for key, value in row.items():
                        if key not in ["source", "target"]:
                            edge[key] = value

                    network_data["edges"].append(edge)

            # Create nodes from unique IDs
            for node_id in node_ids:
                network_data["nodes"].append(
                    {"id": node_id, "label": node_id, "type": "unknown"}
                )

        else:
            # Node list format
            for row in rows:
                node = {
                    "id": row.get("id", f"node_{len(network_data['nodes'])}"),
                    "label": row.get("label", row.get("name", row.get("id", ""))),
                    "type": row.get("type", "unknown"),
                }
                # Add other columns as node attributes
                for key, value in row.items():
                    if key not in ["id", "label", "name"]:
                        node[key] = value

                network_data["nodes"].append(node)

        return network_data

    def _load_from_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Load and combine network data from directory."""
        network_data = {"nodes": [], "edges": [], "metadata": {}}

        # Look for citation JSON files
        citation_files = list(dir_path.glob("**/*citations.json"))

        if citation_files:
            logging.info(f"Found {len(citation_files)} citation files")

            for citation_file in citation_files:
                try:
                    with open(citation_file) as f:
                        citation_data = json.load(f)

                    file_network = self._convert_citation_data(citation_data)

                    # Merge networks
                    network_data["nodes"].extend(file_network["nodes"])
                    network_data["edges"].extend(file_network["edges"])

                except Exception as e:
                    logging.warning(f"Could not load {citation_file}: {e}")

        # Look for other network files
        for pattern in ["*.graphml", "*.gexf", "*.json"]:
            for file_path in dir_path.glob(f"**/{pattern}"):
                if "citations" not in file_path.name:
                    try:
                        file_network = self.load_network_data(file_path)
                        network_data["nodes"].extend(file_network["nodes"])
                        network_data["edges"].extend(file_network["edges"])
                    except Exception as e:
                        logging.warning(f"Could not load {file_path}: {e}")

        return network_data

    def export_to_gephi_gexf(
        self, network_data: Dict[str, Any], filename: Optional[str] = None
    ) -> Path:
        """
        Export network data to Gephi GEXF format.

        Args:
            network_data: Network data to export
            filename: Output filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"network_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gexf"

        output_file = self.output_dir / filename

        logging.info(f"Exporting to Gephi GEXF format: {output_file}")

        # Create GEXF XML structure
        gexf = ET.Element(
            "gexf", {"xmlns": "http://www.gexf.net/1.2draft", "version": "1.2"}
        )

        # Meta information
        meta = ET.SubElement(
            gexf, "meta", {"lastmodifieddate": datetime.now().strftime("%Y-%m-%d")}
        )
        ET.SubElement(meta, "creator").text = "Dataset Citations Analysis"
        ET.SubElement(meta, "description").text = "BIDS Dataset Citation Network"

        # Graph element
        graph = ET.SubElement(
            gexf, "graph", {"mode": "static", "defaultedgetype": "directed"}
        )

        # Node attributes
        node_attrs = ET.SubElement(graph, "attributes", {"class": "node"})
        attr_mapping = {}

        # Detect node attributes
        if network_data["nodes"]:
            sample_node = network_data["nodes"][0]
            attr_id = 0
            for key in sample_node.keys():
                if key not in ["id", "label"]:
                    attr_type = "string"
                    if isinstance(sample_node[key], (int, float)):
                        attr_type = (
                            "float"
                            if isinstance(sample_node[key], float)
                            else "integer"
                        )
                    elif isinstance(sample_node[key], bool):
                        attr_type = "boolean"

                    ET.SubElement(
                        node_attrs,
                        "attribute",
                        {"id": str(attr_id), "title": key, "type": attr_type},
                    )
                    attr_mapping[key] = str(attr_id)
                    attr_id += 1

        # Nodes
        nodes_elem = ET.SubElement(graph, "nodes")
        for node in network_data["nodes"]:
            node_elem = ET.SubElement(
                nodes_elem,
                "node",
                {"id": str(node["id"]), "label": str(node.get("label", node["id"]))},
            )

            # Node attributes
            if len(attr_mapping) > 0:
                attvalues = ET.SubElement(node_elem, "attvalues")
                for key, value in node.items():
                    if key in attr_mapping:
                        ET.SubElement(
                            attvalues,
                            "attvalue",
                            {"for": attr_mapping[key], "value": str(value)},
                        )

        # Edges
        edges_elem = ET.SubElement(graph, "edges")
        for i, edge in enumerate(network_data["edges"]):
            edge_attrs = {
                "id": str(edge.get("id", i)),
                "source": str(edge["source"]),
                "target": str(edge["target"]),
            }

            # Add weight if available
            if "weight" in edge:
                edge_attrs["weight"] = str(edge["weight"])

            ET.SubElement(edges_elem, "edge", edge_attrs)

        # Write to file with proper formatting
        rough_string = ET.tostring(gexf, "unicode")
        reparsed = minidom.parseString(rough_string)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(reparsed.toprettyxml(indent="  "))

        logging.info(f"GEXF export completed: {output_file}")
        return output_file

    def export_to_cytoscape_cx(
        self, network_data: Dict[str, Any], filename: Optional[str] = None
    ) -> Path:
        """
        Export network data to Cytoscape CX format.

        Args:
            network_data: Network data to export
            filename: Output filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"network_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cx"

        output_file = self.output_dir / filename

        logging.info(f"Exporting to Cytoscape CX format: {output_file}")

        # Build CX data structure
        cx_data = [
            {"numberVerification": [{"longNumber": 281474976710655}]},
            {
                "metaData": [
                    {"name": "nodes", "elementCount": len(network_data["nodes"])},
                    {"name": "edges", "elementCount": len(network_data["edges"])},
                    {"name": "nodeAttributes", "elementCount": 0},
                    {"name": "edgeAttributes", "elementCount": 0},
                    {"name": "networkAttributes", "elementCount": 1},
                ]
            },
        ]

        # Nodes
        nodes_aspect = {"nodes": []}
        for i, node in enumerate(network_data["nodes"]):
            nodes_aspect["nodes"].append(
                {"@id": i, "n": node.get("label", node["id"]), "r": node["id"]}
            )
        cx_data.append(nodes_aspect)

        # Edges
        edges_aspect = {"edges": []}
        node_id_mapping = {
            node["id"]: i for i, node in enumerate(network_data["nodes"])
        }

        for i, edge in enumerate(network_data["edges"]):
            source_idx = node_id_mapping.get(edge["source"])
            target_idx = node_id_mapping.get(edge["target"])

            if source_idx is not None and target_idx is not None:
                edge_data = {"@id": i, "s": source_idx, "t": target_idx}

                if "type" in edge:
                    edge_data["i"] = edge["type"]

                edges_aspect["edges"].append(edge_data)
        cx_data.append(edges_aspect)

        # Node attributes
        node_attrs_aspect = {"nodeAttributes": []}
        for i, node in enumerate(network_data["nodes"]):
            for key, value in node.items():
                if key not in ["id", "label"]:
                    node_attrs_aspect["nodeAttributes"].append(
                        {"po": i, "n": key, "v": value}
                    )

        if node_attrs_aspect["nodeAttributes"]:
            cx_data.append(node_attrs_aspect)
            cx_data[1]["metaData"][2]["elementCount"] = len(
                node_attrs_aspect["nodeAttributes"]
            )

        # Edge attributes
        edge_attrs_aspect = {"edgeAttributes": []}
        for i, edge in enumerate(network_data["edges"]):
            for key, value in edge.items():
                if key not in ["id", "source", "target", "type"]:
                    edge_attrs_aspect["edgeAttributes"].append(
                        {"po": i, "n": key, "v": value}
                    )

        if edge_attrs_aspect["edgeAttributes"]:
            cx_data.append(edge_attrs_aspect)
            cx_data[1]["metaData"][3]["elementCount"] = len(
                edge_attrs_aspect["edgeAttributes"]
            )

        # Network attributes
        cx_data.append(
            {
                "networkAttributes": [
                    {
                        "n": "name",
                        "v": network_data.get("metadata", {}).get(
                            "description", "Dataset Citations Network"
                        ),
                    }
                ]
            }
        )

        # Status
        cx_data.append({"status": [{"error": "", "success": True}]})

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cx_data, f, indent=2)

        logging.info(f"CX export completed: {output_file}")
        return output_file

    def export_to_cytoscape_sif(
        self, network_data: Dict[str, Any], filename: Optional[str] = None
    ) -> Path:
        """
        Export network data to Cytoscape SIF format.

        Args:
            network_data: Network data to export
            filename: Output filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"network_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sif"

        output_file = self.output_dir / filename

        logging.info(f"Exporting to Cytoscape SIF format: {output_file}")

        with open(output_file, "w", encoding="utf-8") as f:
            for edge in network_data["edges"]:
                interaction_type = edge.get("type", "interacts_with")
                f.write(f"{edge['source']}\t{interaction_type}\t{edge['target']}\n")

        logging.info(f"SIF export completed: {output_file}")
        return output_file

    def export_to_graphml(
        self, network_data: Dict[str, Any], filename: Optional[str] = None
    ) -> Path:
        """
        Export network data to GraphML format.

        Args:
            network_data: Network data to export
            filename: Output filename (optional)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = (
                f"network_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.graphml"
            )

        output_file = self.output_dir / filename

        logging.info(f"Exporting to GraphML format: {output_file}")

        # Create GraphML XML structure
        graphml = ET.Element(
            "graphml",
            {
                "xmlns": "http://graphml.graphdrawing.org/xmlns",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd",
            },
        )

        # Define keys for node and edge attributes
        key_mapping = {}
        key_id = 0

        # Detect node attributes
        if network_data["nodes"]:
            sample_node = network_data["nodes"][0]
            for key in sample_node.keys():
                if key not in ["id", "label"]:
                    attr_type = "string"
                    if isinstance(sample_node[key], (int, float)):
                        attr_type = (
                            "double" if isinstance(sample_node[key], float) else "int"
                        )
                    elif isinstance(sample_node[key], bool):
                        attr_type = "boolean"

                    ET.SubElement(
                        graphml,
                        "key",
                        {
                            "id": f"k{key_id}",
                            "for": "node",
                            "attr.name": key,
                            "attr.type": attr_type,
                        },
                    )
                    key_mapping[("node", key)] = f"k{key_id}"
                    key_id += 1

        # Detect edge attributes
        if network_data["edges"]:
            sample_edge = network_data["edges"][0]
            for key in sample_edge.keys():
                if key not in ["id", "source", "target"]:
                    attr_type = "string"
                    if isinstance(sample_edge[key], (int, float)):
                        attr_type = (
                            "double" if isinstance(sample_edge[key], float) else "int"
                        )
                    elif isinstance(sample_edge[key], bool):
                        attr_type = "boolean"

                    ET.SubElement(
                        graphml,
                        "key",
                        {
                            "id": f"k{key_id}",
                            "for": "edge",
                            "attr.name": key,
                            "attr.type": attr_type,
                        },
                    )
                    key_mapping[("edge", key)] = f"k{key_id}"
                    key_id += 1

        # Graph element
        graph = ET.SubElement(
            graphml, "graph", {"id": "dataset_citations", "edgedefault": "directed"}
        )

        # Nodes
        for node in network_data["nodes"]:
            node_elem = ET.SubElement(graph, "node", {"id": str(node["id"])})

            for key, value in node.items():
                if key != "id" and ("node", key) in key_mapping:
                    data_elem = ET.SubElement(
                        node_elem, "data", {"key": key_mapping[("node", key)]}
                    )
                    data_elem.text = str(value)

        # Edges
        for edge in network_data["edges"]:
            edge_elem = ET.SubElement(
                graph,
                "edge",
                {"source": str(edge["source"]), "target": str(edge["target"])},
            )

            for key, value in edge.items():
                if key not in ["source", "target"] and ("edge", key) in key_mapping:
                    data_elem = ET.SubElement(
                        edge_elem, "data", {"key": key_mapping[("edge", key)]}
                    )
                    data_elem.text = str(value)

        # Write to file with proper formatting
        rough_string = ET.tostring(graphml, "unicode")
        reparsed = minidom.parseString(rough_string)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(reparsed.toprettyxml(indent="  "))

        logging.info(f"GraphML export completed: {output_file}")
        return output_file

    def export_to_csv(
        self, network_data: Dict[str, Any], filename_base: Optional[str] = None
    ) -> List[Path]:
        """
        Export network data to CSV format (separate node and edge files).

        Args:
            network_data: Network data to export
            filename_base: Base filename (optional)

        Returns:
            List of exported file paths
        """
        if filename_base is None:
            filename_base = f"network_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        exported_files = []

        # Export nodes
        if network_data["nodes"]:
            nodes_file = self.output_dir / f"{filename_base}_nodes.csv"

            if PANDAS_AVAILABLE:
                df_nodes = pd.DataFrame(network_data["nodes"])
                df_nodes.to_csv(nodes_file, index=False)
            else:
                # Fallback to basic CSV writing
                with open(nodes_file, "w", newline="", encoding="utf-8") as f:
                    if network_data["nodes"]:
                        fieldnames = network_data["nodes"][0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(network_data["nodes"])

            exported_files.append(nodes_file)
            logging.info(f"Nodes CSV exported: {nodes_file}")

        # Export edges
        if network_data["edges"]:
            edges_file = self.output_dir / f"{filename_base}_edges.csv"

            if PANDAS_AVAILABLE:
                df_edges = pd.DataFrame(network_data["edges"])
                df_edges.to_csv(edges_file, index=False)
            else:
                # Fallback to basic CSV writing
                with open(edges_file, "w", newline="", encoding="utf-8") as f:
                    if network_data["edges"]:
                        fieldnames = network_data["edges"][0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(network_data["edges"])

            exported_files.append(edges_file)
            logging.info(f"Edges CSV exported: {edges_file}")

        return exported_files

    def export_all_formats(
        self, network_data: Dict[str, Any], base_filename: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Export network data to all supported formats.

        Args:
            network_data: Network data to export
            base_filename: Base filename for exports

        Returns:
            Dictionary mapping format names to file paths
        """
        if base_filename is None:
            base_filename = (
                f"dataset_citations_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        exported_files = {}

        logging.info("Exporting to all supported formats...")

        try:
            # Gephi GEXF
            exported_files["gexf"] = self.export_to_gephi_gexf(
                network_data, f"{base_filename}.gexf"
            )
        except Exception as e:
            logging.error(f"GEXF export failed: {e}")

        try:
            # Cytoscape CX
            exported_files["cx"] = self.export_to_cytoscape_cx(
                network_data, f"{base_filename}.cx"
            )
        except Exception as e:
            logging.error(f"CX export failed: {e}")

        try:
            # Cytoscape SIF
            exported_files["sif"] = self.export_to_cytoscape_sif(
                network_data, f"{base_filename}.sif"
            )
        except Exception as e:
            logging.error(f"SIF export failed: {e}")

        try:
            # GraphML
            exported_files["graphml"] = self.export_to_graphml(
                network_data, f"{base_filename}.graphml"
            )
        except Exception as e:
            logging.error(f"GraphML export failed: {e}")

        try:
            # CSV files
            csv_files = self.export_to_csv(network_data, base_filename)
            exported_files["csv_nodes"] = csv_files[0] if len(csv_files) > 0 else None
            exported_files["csv_edges"] = csv_files[1] if len(csv_files) > 1 else None
        except Exception as e:
            logging.error(f"CSV export failed: {e}")

        logging.info(f"Export completed. {len(exported_files)} formats exported.")
        return exported_files


def main() -> int:
    """Main entry point for external tool exports."""
    parser = argparse.ArgumentParser(
        description="Export network data for external analysis tools"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input data source (file or directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("exports"),
        help="Output directory for exported files (default: exports)",
    )
    parser.add_argument(
        "--format",
        choices=["gexf", "cx", "sif", "graphml", "csv", "all"],
        default="all",
        help="Export format (default: all)",
    )
    parser.add_argument(
        "--filename",
        help="Base filename for exports (optional)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.input.exists():
        logging.error(f"Input source does not exist: {args.input}")
        return 1

    try:
        # Initialize exporter
        exporter = ExternalToolExporter(args.output_dir)

        # Load network data
        network_data = exporter.load_network_data(args.input)

        if not network_data["nodes"] and not network_data["edges"]:
            logging.error("No network data found in input source")
            return 1

        # Export to requested format(s)
        exported_files = {}

        if args.format == "all":
            exported_files = exporter.export_all_formats(network_data, args.filename)
        elif args.format == "gexf":
            exported_files["gexf"] = exporter.export_to_gephi_gexf(
                network_data, args.filename
            )
        elif args.format == "cx":
            exported_files["cx"] = exporter.export_to_cytoscape_cx(
                network_data, args.filename
            )
        elif args.format == "sif":
            exported_files["sif"] = exporter.export_to_cytoscape_sif(
                network_data, args.filename
            )
        elif args.format == "graphml":
            exported_files["graphml"] = exporter.export_to_graphml(
                network_data, args.filename
            )
        elif args.format == "csv":
            csv_files = exporter.export_to_csv(network_data, args.filename)
            exported_files["csv"] = csv_files

        # Report results
        print("\n🎉 Network Export Completed Successfully!")
        print("\n📊 Network Summary:")
        print(f"   • {len(network_data['nodes'])} nodes")
        print(f"   • {len(network_data['edges'])} edges")
        print(f"   • {len(exported_files)} format(s) exported")

        print("\n📁 Exported Files:")
        for format_name, file_path in exported_files.items():
            if file_path:
                if isinstance(file_path, list):
                    for f in file_path:
                        print(f"   • {f.name} ({format_name})")
                else:
                    print(f"   • {file_path.name} ({format_name})")

        print("\n🔗 Usage Instructions:")
        print("   📊 Gephi: Import .gexf file for large network visualization")
        print(
            "   🧬 Cytoscape: Import .cx or .sif file for biological network analysis"
        )
        print("   🔄 Universal: Use .graphml for programmatic analysis")
        print("   📈 Spreadsheet: Open .csv files in Excel/R/Python")

        return 0

    except Exception as e:
        logging.error(f"Export failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
