"""
CLI command for creating interactive HTML reports with unified visualization themes.

This module creates self-contained HTML reports that can be hosted on websites,
combining all analysis results with a consistent visual theme and interactive exploration.
"""

import argparse
import logging
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import base64

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import jinja2

    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class InteractiveReportGenerator:
    """Generate unified interactive HTML reports for dataset citations analysis."""

    def __init__(self, results_dir: Path, output_dir: Path):
        """
        Initialize the report generator.

        Args:
            results_dir: Directory containing analysis results
            output_dir: Directory to save generated reports
        """
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Unified color scheme for scientific visualization
        self.color_scheme = {
            "primary": "#2E86AB",  # Ocean blue
            "secondary": "#A23B72",  # Deep pink
            "accent": "#F18F01",  # Orange
            "success": "#C73E1D",  # Red-orange
            "dataset": "#4A90E2",  # Light blue
            "citation": "#E94B3C",  # Red
            "bridge": "#50C878",  # Emerald green
            "background": "#F8F9FA",  # Light gray
            "text": "#212529",  # Dark gray
            "border": "#DEE2E6",  # Medium gray
        }

    def collect_analysis_results(self) -> Dict[str, Any]:
        """
        Collect all available analysis results from the results directory.

        Returns:
            Dictionary containing organized analysis results
        """
        logging.info("Collecting analysis results from results directory")

        analysis_data = {
            "network_analysis": {},
            "temporal_analysis": {},
            "visualizations": {},
            "theme_analysis": {},
            "research_context": {},
            "summary_stats": {},
        }

        # Collect network analysis results
        network_dir = self.results_dir / "network_analysis"
        if network_dir.exists():
            for csv_file in network_dir.glob("*.csv"):
                try:
                    if PANDAS_AVAILABLE:
                        df = pd.read_csv(csv_file)
                        analysis_data["network_analysis"][csv_file.stem] = df.to_dict(
                            "records"
                        )
                    logging.info(f"Loaded network analysis: {csv_file.name}")
                except Exception as e:
                    logging.warning(f"Could not load {csv_file}: {e}")

        # Collect temporal analysis
        temporal_dir = self.results_dir / "temporal_analysis"
        if temporal_dir.exists():
            temporal_json = temporal_dir / "temporal_analysis.json"
            if temporal_json.exists():
                with open(temporal_json) as f:
                    analysis_data["temporal_analysis"] = json.load(f)
                logging.info("Loaded temporal analysis data")

        # Collect theme analysis results
        theme_dirs = ["theme_analysis", "umap_analysis", "research_context_networks"]
        for theme_dir in theme_dirs:
            dir_path = self.results_dir / theme_dir
            if dir_path.exists():
                for json_file in dir_path.glob("*.json"):
                    try:
                        with open(json_file) as f:
                            analysis_data["theme_analysis"][json_file.stem] = json.load(
                                f
                            )
                        logging.info(f"Loaded theme analysis: {json_file.name}")
                    except Exception as e:
                        logging.warning(f"Could not load {json_file}: {e}")

        # Collect visualization files
        viz_dirs = [
            "network_visualizations",
            "temporal_analysis",
            "dataset_popularity",
            "impact_analysis",
        ]
        for viz_dir in viz_dirs:
            dir_path = self.results_dir / viz_dir
            if dir_path.exists():
                for viz_file in dir_path.glob("*.html"):
                    # Store path for embedding
                    analysis_data["visualizations"][viz_file.stem] = str(viz_file)
                for viz_file in dir_path.glob("*.png"):
                    # Convert to base64 for embedding
                    try:
                        with open(viz_file, "rb") as f:
                            img_data = base64.b64encode(f.read()).decode()
                        analysis_data["visualizations"][f"{viz_file.stem}_png"] = (
                            f"data:image/png;base64,{img_data}"
                        )
                        logging.info(f"Embedded visualization: {viz_file.name}")
                    except Exception as e:
                        logging.warning(f"Could not embed {viz_file}: {e}")

        # Generate summary statistics
        analysis_data["summary_stats"] = self._generate_summary_stats(analysis_data)

        logging.info(f"Collected {len(analysis_data)} analysis categories")
        return analysis_data

    def _generate_summary_stats(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from collected data."""
        stats = {
            "total_datasets": 0,
            "total_citations": 0,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "available_analyses": [],
            "bridge_papers": 0,
            "confidence_threshold": 0.4,
        }

        # Count available analyses
        for category, data in analysis_data.items():
            if data and category != "summary_stats":
                stats["available_analyses"].append(category.replace("_", " ").title())

        # Extract counts from network analysis if available
        if analysis_data.get("network_analysis"):
            for analysis_name, data in analysis_data["network_analysis"].items():
                if "bridge" in analysis_name.lower() and isinstance(data, list):
                    stats["bridge_papers"] = len(data)
                elif "dataset" in analysis_name.lower() and isinstance(data, list):
                    stats["total_datasets"] = len(data)

        # Extract temporal data if available
        if analysis_data.get("temporal_analysis"):
            temporal_data = analysis_data["temporal_analysis"]
            if isinstance(temporal_data, dict):
                stats["total_citations"] = temporal_data.get("total_citations", 0)
                stats["total_datasets"] = temporal_data.get("total_datasets", 0)

        return stats

    def create_dashboard_template(self) -> str:
        """
        Create the main dashboard HTML template using Bootstrap and modern JS libraries.

        Returns:
            HTML template string
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dataset Citations Analysis Dashboard</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- Cytoscape.js -->
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    
    <style>
        :root {
            --primary-color: {{ color_scheme.primary }};
            --secondary-color: {{ color_scheme.secondary }};
            --accent-color: {{ color_scheme.accent }};
            --dataset-color: {{ color_scheme.dataset }};
            --citation-color: {{ color_scheme.citation }};
            --bridge-color: {{ color_scheme.bridge }};
            --bg-color: {{ color_scheme.background }};
            --text-color: {{ color_scheme.text }};
            --border-color: {{ color_scheme.border }};
        }
        
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .navbar {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card {
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease-in-out;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .stat-card {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
        }
        
        .analysis-card {
            border-left: 4px solid var(--primary-color);
        }
        
        .viz-container {
            min-height: 400px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        
        .network-container {
            height: 600px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        
        .section-header {
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        .badge-dataset {
            background-color: var(--dataset-color);
        }
        
        .badge-citation {
            background-color: var(--citation-color);
        }
        
        .badge-bridge {
            background-color: var(--bridge-color);
        }
        
        .nav-pills .nav-link.active {
            background-color: var(--primary-color);
        }
        
        .progress-bar {
            background-color: var(--primary-color);
        }
        
        .footer {
            background: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-network-wired me-2"></i>
                Dataset Citations Analysis
            </a>
            <div class="navbar-nav ms-auto">
                <span class="nav-link">
                    <i class="fas fa-calendar me-1"></i>
                    {{ summary_stats.analysis_date }}
                </span>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="jumbotron bg-light p-5 rounded">
                    <h1 class="display-4">
                        <i class="fas fa-chart-network me-3"></i>
                        BIDS Dataset Citation Analysis
                    </h1>
                    <p class="lead">
                        Comprehensive analysis of citation patterns, research themes, and network relationships 
                        across {{ summary_stats.total_datasets }} BIDS datasets with confidence-filtered citations.
                    </p>
                    <hr class="my-4">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="card stat-card">
                                <div class="card-body text-center">
                                    <h3><i class="fas fa-database me-2"></i>{{ summary_stats.total_datasets }}</h3>
                                    <p class="mb-0">Datasets Analyzed</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card stat-card">
                                <div class="card-body text-center">
                                    <h3><i class="fas fa-quote-left me-2"></i>{{ summary_stats.total_citations }}</h3>
                                    <p class="mb-0">High-Confidence Citations</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card stat-card">
                                <div class="card-body text-center">
                                    <h3><i class="fas fa-bridge me-2"></i>{{ summary_stats.bridge_papers }}</h3>
                                    <p class="mb-0">Research Bridge Papers</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card stat-card">
                                <div class="card-body text-center">
                                    <h3><i class="fas fa-filter me-2"></i>≥{{ summary_stats.confidence_threshold }}</h3>
                                    <p class="mb-0">Confidence Threshold</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="container mt-4">
        <!-- Navigation Tabs -->
        <ul class="nav nav-pills mb-4" id="analysisTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="pill" data-bs-target="#overview" 
                        type="button" role="tab">
                    <i class="fas fa-home me-2"></i>Overview
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="network-tab" data-bs-toggle="pill" data-bs-target="#network" 
                        type="button" role="tab">
                    <i class="fas fa-project-diagram me-2"></i>Network Analysis
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="temporal-tab" data-bs-toggle="pill" data-bs-target="#temporal" 
                        type="button" role="tab">
                    <i class="fas fa-chart-line me-2"></i>Temporal Trends
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="themes-tab" data-bs-toggle="pill" data-bs-target="#themes" 
                        type="button" role="tab">
                    <i class="fas fa-tags me-2"></i>Research Themes
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="exports-tab" data-bs-toggle="pill" data-bs-target="#exports" 
                        type="button" role="tab">
                    <i class="fas fa-download me-2"></i>Data Export
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content" id="analysisTabContent">
            <!-- Overview Tab -->
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                <div class="row">
                    <div class="col-lg-8">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-bar me-2"></i>Analysis Summary</h5>
                            </div>
                            <div class="card-body">
                                <div id="summaryChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-4">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-list-check me-2"></i>Available Analyses</h5>
                            </div>
                            <div class="card-body">
                                {% for analysis in summary_stats.available_analyses %}
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <span>{{ analysis }}</span>
                                    <span class="badge badge-dataset">✓</span>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Network Analysis Tab -->
            <div class="tab-pane fade" id="network" role="tabpanel">
                <h2 class="section-header">Citation Network Analysis</h2>
                <div class="row">
                    <div class="col-12">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-network-wired me-2"></i>Interactive Network Visualization</h5>
                            </div>
                            <div class="card-body">
                                <div id="networkViz" class="network-container"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-bridge me-2"></i>Research Bridge Analysis</h5>
                            </div>
                            <div class="card-body">
                                <div id="bridgeChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-star me-2"></i>Dataset Popularity</h5>
                            </div>
                            <div class="card-body">
                                <div id="popularityChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Temporal Analysis Tab -->
            <div class="tab-pane fade" id="temporal" role="tabpanel">
                <h2 class="section-header">Temporal Citation Trends</h2>
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line me-2"></i>Citation Growth Over Time</h5>
                    </div>
                    <div class="card-body">
                        <div id="temporalChart" class="viz-container"></div>
                    </div>
                </div>
            </div>

            <!-- Research Themes Tab -->
            <div class="tab-pane fade" id="themes" role="tabpanel">
                <h2 class="section-header">Research Theme Analysis</h2>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-cloud me-2"></i>Research Topics</h5>
                            </div>
                            <div class="card-body">
                                <div id="themesChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-sitemap me-2"></i>UMAP Clustering</h5>
                            </div>
                            <div class="card-body">
                                <div id="umapChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Data Export Tab -->
            <div class="tab-pane fade" id="exports" role="tabpanel">
                <h2 class="section-header">Data Export & External Tools</h2>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-external-link-alt me-2"></i>Network Analysis Tools</h5>
                            </div>
                            <div class="card-body">
                                <p>Export network data for advanced analysis in specialized tools:</p>
                                <div class="d-grid gap-2">
                                    <button class="btn btn-outline-primary" onclick="exportToGephi()">
                                        <i class="fas fa-download me-2"></i>Export to Gephi (GEXF)
                                    </button>
                                    <button class="btn btn-outline-primary" onclick="exportToCytoscape()">
                                        <i class="fas fa-download me-2"></i>Export to Cytoscape (CX)
                                    </button>
                                    <button class="btn btn-outline-secondary" onclick="exportToGraphML()">
                                        <i class="fas fa-download me-2"></i>Export as GraphML
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-table me-2"></i>Data Tables</h5>
                            </div>
                            <div class="card-body">
                                <p>Download analysis results as CSV files:</p>
                                <div class="d-grid gap-2">
                                    <button class="btn btn-outline-success" onclick="exportNetworkCSV()">
                                        <i class="fas fa-file-csv me-2"></i>Network Analysis CSV
                                    </button>
                                    <button class="btn btn-outline-success" onclick="exportTemporalCSV()">
                                        <i class="fas fa-file-csv me-2"></i>Temporal Data CSV
                                    </button>
                                    <button class="btn btn-outline-success" onclick="exportThemesCSV()">
                                        <i class="fas fa-file-csv me-2"></i>Theme Analysis CSV
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card analysis-card">
                    <div class="card-header">
                        <h5><i class="fas fa-info-circle me-2"></i>Export Information</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <h6>Gephi (GEXF)</h6>
                                <p class="text-muted">Best for: Large network visualization, layout algorithms, community detection</p>
                            </div>
                            <div class="col-md-4">
                                <h6>Cytoscape (CX)</h6>
                                <p class="text-muted">Best for: Biological networks, pathway analysis, advanced styling</p>
                            </div>
                            <div class="col-md-4">
                                <h6>GraphML</h6>
                                <p class="text-muted">Best for: Universal format, programmatic analysis, custom tools</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer">
        <div class="container text-center">
            <p>&copy; 2025 Dataset Citations Analysis. Generated from BIDS dataset citation tracking system.</p>
            <p class="text-muted">
                Confidence threshold: ≥{{ summary_stats.confidence_threshold }} | 
                Analysis date: {{ summary_stats.analysis_date }}
            </p>
        </div>
    </footer>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Embedded analysis data
        const analysisData = {{ analysis_data | tojson }};
        const colorScheme = {{ color_scheme | tojson }};
        
        // Initialize all visualizations when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
        });
        
        function initializeCharts() {
            // Initialize overview charts
            createSummaryChart();
            
            // Initialize network visualization
            createNetworkVisualization();
            
            // Initialize other charts
            createTemporalChart();
            createBridgeChart();
            createPopularityChart();
            createThemesChart();
            createUMAPChart();
        }
        
        function createSummaryChart() {
            const data = [{
                x: ['Datasets', 'Citations', 'Bridge Papers', 'Analyses'],
                y: [
                    {{ summary_stats.total_datasets }},
                    {{ summary_stats.total_citations }},
                    {{ summary_stats.bridge_papers }},
                    {{ summary_stats.available_analyses | length }}
                ],
                type: 'bar',
                marker: {
                    color: [
                        colorScheme.dataset,
                        colorScheme.citation,
                        colorScheme.bridge,
                        colorScheme.accent
                    ]
                }
            }];
            
            const layout = {
                title: 'Analysis Overview',
                font: { family: 'Segoe UI' },
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            Plotly.newPlot('summaryChart', data, layout, {responsive: true});
        }
        
        function createNetworkVisualization() {
            // Create a sample network visualization with Cytoscape.js
            const cy = cytoscape({
                container: document.getElementById('networkViz'),
                
                elements: [
                    // Sample nodes and edges - replace with actual data
                    { data: { id: 'dataset1', label: 'Dataset 1', type: 'dataset' } },
                    { data: { id: 'citation1', label: 'Citation 1', type: 'citation' } },
                    { data: { id: 'bridge1', label: 'Bridge Paper', type: 'bridge' } },
                    { data: { id: 'e1', source: 'dataset1', target: 'citation1' } },
                    { data: { id: 'e2', source: 'citation1', target: 'bridge1' } }
                ],
                
                style: [
                    {
                        selector: 'node[type="dataset"]',
                        style: {
                            'background-color': colorScheme.dataset,
                            'label': 'data(label)',
                            'width': 30,
                            'height': 30
                        }
                    },
                    {
                        selector: 'node[type="citation"]',
                        style: {
                            'background-color': colorScheme.citation,
                            'label': 'data(label)',
                            'width': 25,
                            'height': 25
                        }
                    },
                    {
                        selector: 'node[type="bridge"]',
                        style: {
                            'background-color': colorScheme.bridge,
                            'label': 'data(label)',
                            'width': 35,
                            'height': 35
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'line-color': colorScheme.border
                        }
                    }
                ],
                
                layout: {
                    name: 'cose',
                    idealEdgeLength: 100,
                    nodeOverlap: 20,
                    refresh: 20,
                    fit: true,
                    padding: 30
                }
            });
        }
        
        function createTemporalChart() {
            // Placeholder for temporal chart
            const data = [{
                x: ['2020', '2021', '2022', '2023', '2024'],
                y: [50, 120, 180, 250, 300],
                type: 'scatter',
                mode: 'lines+markers',
                line: {color: colorScheme.primary}
            }];
            
            const layout = {
                title: 'Citation Growth Over Time',
                xaxis: {title: 'Year'},
                yaxis: {title: 'Cumulative Citations'},
                font: {family: 'Segoe UI'},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            Plotly.newPlot('temporalChart', data, layout, {responsive: true});
        }
        
        function createBridgeChart() {
            // Placeholder for bridge analysis
            const data = [{
                values: [60, 25, 15],
                labels: ['Single Domain', 'Cross-Domain', 'Bridge Papers'],
                type: 'pie',
                marker: {
                    colors: [colorScheme.dataset, colorScheme.citation, colorScheme.bridge]
                }
            }];
            
            const layout = {
                title: 'Research Bridge Distribution',
                font: {family: 'Segoe UI'}
            };
            
            Plotly.newPlot('bridgeChart', data, layout, {responsive: true});
        }
        
        function createPopularityChart() {
            // Placeholder for dataset popularity
            const data = [{
                x: ['ds000117', 'ds000246', 'ds000247', 'ds000248', 'ds001784'],
                y: [45, 38, 32, 28, 25],
                type: 'bar',
                marker: {color: colorScheme.accent}
            }];
            
            const layout = {
                title: 'Top Cited Datasets',
                xaxis: {title: 'Dataset ID'},
                yaxis: {title: 'Citation Count'},
                font: {family: 'Segoe UI'},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            Plotly.newPlot('popularityChart', data, layout, {responsive: true});
        }
        
        function createThemesChart() {
            // Placeholder for themes
            const data = [{
                x: ['Neuroscience', 'fMRI', 'Brain Networks', 'Cognitive', 'Clinical'],
                y: [25, 22, 18, 15, 12],
                type: 'bar',
                marker: {color: colorScheme.secondary}
            }];
            
            const layout = {
                title: 'Research Theme Frequency',
                font: {family: 'Segoe UI'},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            Plotly.newPlot('themesChart', data, layout, {responsive: true});
        }
        
        function createUMAPChart() {
            // Placeholder for UMAP
            const data = [{
                x: [1, 2, 3, 4, 5],
                y: [2, 4, 1, 5, 3],
                mode: 'markers',
                type: 'scatter',
                marker: {
                    size: 12,
                    color: [1, 2, 3, 1, 2],
                    colorscale: 'Viridis'
                }
            }];
            
            const layout = {
                title: 'UMAP Embedding Visualization',
                xaxis: {title: 'UMAP 1'},
                yaxis: {title: 'UMAP 2'},
                font: {family: 'Segoe UI'},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };
            
            Plotly.newPlot('umapChart', data, layout, {responsive: true});
        }
        
        // Export functions
        function exportToGephi() {
            // Implementation for GEXF export
            alert('Exporting to Gephi GEXF format...');
        }
        
        function exportToCytoscape() {
            // Implementation for Cytoscape CX export
            alert('Exporting to Cytoscape CX format...');
        }
        
        function exportToGraphML() {
            // Implementation for GraphML export
            alert('Exporting to GraphML format...');
        }
        
        function exportNetworkCSV() {
            alert('Exporting network analysis CSV...');
        }
        
        function exportTemporalCSV() {
            alert('Exporting temporal data CSV...');
        }
        
        function exportThemesCSV() {
            alert('Exporting themes analysis CSV...');
        }
    </script>
</body>
</html>"""

    def create_export_generators(self) -> Dict[str, Any]:
        """
        Create export generators for external tools.

        Returns:
            Dictionary with export generator functions
        """
        export_generators = {}

        # GEXF export for Gephi
        export_generators["gexf"] = self._create_gexf_exporter()

        # CX export for Cytoscape
        export_generators["cytoscape_cx"] = self._create_cx_exporter()

        # GraphML export (universal)
        export_generators["graphml"] = self._create_graphml_exporter()

        return export_generators

    def _create_gexf_exporter(self) -> str:
        """Create GEXF format exporter for Gephi."""
        return '''
def export_to_gexf(network_data, output_file):
    """Export network data to GEXF format for Gephi."""
    gexf_template = """<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
    <graph mode="static" defaultedgetype="undirected">
        <attributes class="node">
            <attribute id="0" title="type" type="string"/>
            <attribute id="1" title="confidence" type="float"/>
            <attribute id="2" title="cited_by" type="integer"/>
        </attributes>
        <nodes>
            {nodes}
        </nodes>
        <edges>
            {edges}
        </edges>
    </graph>
</gexf>"""
    
    nodes_xml = ""
    edges_xml = ""
    
    # Generate nodes XML
    for node in network_data.get("nodes", []):
        nodes_xml += """
        <node id="%s" label="%s">
            <attvalues>
                <attvalue for="0" value="%s"/>
                <attvalue for="1" value="%s"/>
                <attvalue for="2" value="%s"/>
            </attvalues>
        </node>""" % (
            node['id'], node['label'],
            node.get('type', 'unknown'),
            node.get('confidence', 0.0),
            node.get('cited_by', 0)
        )
    
    # Generate edges XML
    for edge in network_data.get("edges", []):
        edges_xml += """
        <edge id="%s" source="%s" target="%s"/>""" % (
            edge['id'], edge['source'], edge['target']
        )
    
    gexf_content = gexf_template.format(nodes=nodes_xml, edges=edges_xml)
    
    with open(output_file, 'w') as f:
        f.write(gexf_content)
    
    return output_file
'''

    def _create_cx_exporter(self) -> str:
        """Create CX format exporter for Cytoscape."""
        return '''
def export_to_cytoscape_cx(network_data, output_file):
    """Export network data to Cytoscape CX format."""
    cx_data = [
        {"numberVerification": [{"longNumber": 281474976710655}]},
        {"metaData": [
            {"name": "nodes", "elementCount": len(network_data.get("nodes", []))},
            {"name": "edges", "elementCount": len(network_data.get("edges", []))},
            {"name": "nodeAttributes", "elementCount": 0},
            {"name": "edgeAttributes", "elementCount": 0}
        ]},
        {"nodes": [{"@id": i, "n": node["label"]} for i, node in enumerate(network_data.get("nodes", []))]},
        {"edges": [{"@id": i, "s": edge["source"], "t": edge["target"]} 
                  for i, edge in enumerate(network_data.get("edges", []))]},
        {"status": [{"error": "", "success": True}]}
    ]
    
    with open(output_file, 'w') as f:
        json.dump(cx_data, f, indent=2)
    
    return output_file
'''

    def _create_graphml_exporter(self) -> str:
        """Create GraphML format exporter."""
        return '''
def export_to_graphml(network_data, output_file):
    """Export network data to GraphML format."""
    graphml_template = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns
         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
    
    <key id="type" for="node" attr.name="type" attr.type="string"/>
    <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>
    <key id="cited_by" for="node" attr.name="cited_by" attr.type="int"/>
    <key id="weight" for="edge" attr.name="weight" attr.type="double"/>
    
    <graph id="dataset_citations" edgedefault="undirected">
        {nodes}
        {edges}
    </graph>
</graphml>"""
    
    nodes_xml = ""
    edges_xml = ""
    
    # Generate nodes
    for node in network_data.get("nodes", []):
        nodes_xml += """
        <node id="%s">
            <data key="type">%s</data>
            <data key="confidence">%s</data>
            <data key="cited_by">%s</data>
        </node>""" % (
            node['id'],
            node.get('type', 'unknown'),
            node.get('confidence', 0.0),
            node.get('cited_by', 0)
        )
    
    # Generate edges
    for edge in network_data.get("edges", []):
        edges_xml += """
        <edge source="%s" target="%s">
            <data key="weight">%s</data>
        </edge>""" % (
            edge['source'], edge['target'],
            edge.get('weight', 1.0)
        )
    
    graphml_content = graphml_template.format(nodes=nodes_xml, edges=edges_xml)
    
    with open(output_file, 'w') as f:
        f.write(graphml_content)
    
    return output_file
'''

    def generate_dashboard(self, analysis_data: Dict[str, Any]) -> Path:
        """
        Generate the main interactive dashboard.

        Args:
            analysis_data: Collected analysis results

        Returns:
            Path to generated dashboard HTML file
        """
        logging.info("Generating interactive dashboard")

        if not JINJA_AVAILABLE:
            # Fallback: simple string replacement
            template_content = self.create_dashboard_template()

            # Simple replacements
            template_content = template_content.replace(
                "{{ summary_stats.total_datasets }}",
                str(analysis_data["summary_stats"]["total_datasets"]),
            )
            template_content = template_content.replace(
                "{{ summary_stats.total_citations }}",
                str(analysis_data["summary_stats"]["total_citations"]),
            )
            template_content = template_content.replace(
                "{{ summary_stats.bridge_papers }}",
                str(analysis_data["summary_stats"]["bridge_papers"]),
            )
            template_content = template_content.replace(
                "{{ summary_stats.confidence_threshold }}",
                str(analysis_data["summary_stats"]["confidence_threshold"]),
            )
            template_content = template_content.replace(
                "{{ summary_stats.analysis_date }}",
                analysis_data["summary_stats"]["analysis_date"],
            )

            # Replace color scheme and data
            template_content = template_content.replace(
                "{{ color_scheme | tojson }}", json.dumps(self.color_scheme)
            )
            template_content = template_content.replace(
                "{{ analysis_data | tojson }}", json.dumps(analysis_data)
            )

            # Replace available analyses
            analyses_html = ""
            for analysis in analysis_data["summary_stats"]["available_analyses"]:
                analyses_html += '<div class="d-flex justify-content-between align-items-center mb-2">'
                analyses_html += f"<span>{analysis}</span>"
                analyses_html += '<span class="badge badge-dataset">✓</span>'
                analyses_html += "</div>"

            template_content = (
                template_content.replace(
                    "{% for analysis in summary_stats.available_analyses %}", ""
                )
                .replace("{{ analysis }}", "")
                .replace("{% endfor %}", analyses_html)
            )

        else:
            # Use Jinja2 for proper templating
            template = jinja2.Template(self.create_dashboard_template())
            template_content = template.render(
                summary_stats=analysis_data["summary_stats"],
                analysis_data=analysis_data,
                color_scheme=self.color_scheme,
            )

        # Save dashboard
        dashboard_file = self.output_dir / "dataset_citations_dashboard.html"
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(template_content)

        logging.info(f"Dashboard saved to: {dashboard_file}")
        return dashboard_file

    def create_export_files(self, analysis_data: Dict[str, Any]) -> List[Path]:
        """
        Create export files for external tools.

        Args:
            analysis_data: Analysis results to export

        Returns:
            List of created export files
        """
        logging.info("Creating export files for external tools")
        created_files = []

        # Create sample network data for exports
        sample_network = {
            "nodes": [
                {
                    "id": "dataset_001",
                    "label": "Dataset 001",
                    "type": "dataset",
                    "confidence": 1.0,
                    "cited_by": 15,
                },
                {
                    "id": "citation_001",
                    "label": "Paper A",
                    "type": "citation",
                    "confidence": 0.8,
                    "cited_by": 25,
                },
                {
                    "id": "bridge_001",
                    "label": "Bridge Paper",
                    "type": "bridge",
                    "confidence": 0.9,
                    "cited_by": 40,
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "dataset_001",
                    "target": "citation_001",
                    "weight": 0.8,
                },
                {
                    "id": "e2",
                    "source": "citation_001",
                    "target": "bridge_001",
                    "weight": 0.9,
                },
            ],
        }

        # Create GEXF file for Gephi
        gexf_file = self.output_dir / "dataset_citations_network.gexf"
        self._write_gexf_file(sample_network, gexf_file)
        created_files.append(gexf_file)

        # Create CX file for Cytoscape
        cx_file = self.output_dir / "dataset_citations_network.cx"
        self._write_cx_file(sample_network, cx_file)
        created_files.append(cx_file)

        # Create GraphML file
        graphml_file = self.output_dir / "dataset_citations_network.graphml"
        self._write_graphml_file(sample_network, graphml_file)
        created_files.append(graphml_file)

        # Create CSV exports
        csv_files = self._create_csv_exports(analysis_data)
        created_files.extend(csv_files)

        logging.info(f"Created {len(created_files)} export files")
        return created_files

    def _write_gexf_file(self, network_data: Dict[str, Any], output_file: Path) -> None:
        """Write network data to GEXF format."""
        gexf_content = (
            '''<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
    <meta lastmodifieddate="'''
            + datetime.now().strftime("%Y-%m-%d")
            + """">
        <creator>Dataset Citations Analysis</creator>
        <description>BIDS Dataset Citation Network</description>
    </meta>
    <graph mode="static" defaultedgetype="undirected">
        <attributes class="node">
            <attribute id="0" title="type" type="string"/>
            <attribute id="1" title="confidence" type="float"/>
            <attribute id="2" title="cited_by" type="integer"/>
        </attributes>
        <nodes>"""
        )

        for node in network_data.get("nodes", []):
            gexf_content += f'''
            <node id="{node["id"]}" label="{node["label"]}">
                <attvalues>
                    <attvalue for="0" value="{node.get("type", "unknown")}"/>
                    <attvalue for="1" value="{node.get("confidence", 0.0)}"/>
                    <attvalue for="2" value="{node.get("cited_by", 0)}"/>
                </attvalues>
            </node>'''

        gexf_content += """
        </nodes>
        <edges>"""

        for edge in network_data.get("edges", []):
            gexf_content += f'''
            <edge id="{edge["id"]}" source="{edge["source"]}" target="{edge["target"]}"/>'''

        gexf_content += """
        </edges>
    </graph>
</gexf>"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gexf_content)

    def _write_cx_file(self, network_data: Dict[str, Any], output_file: Path) -> None:
        """Write network data to Cytoscape CX format."""
        cx_data = [
            {"numberVerification": [{"longNumber": 281474976710655}]},
            {
                "metaData": [
                    {
                        "name": "nodes",
                        "elementCount": len(network_data.get("nodes", [])),
                    },
                    {
                        "name": "edges",
                        "elementCount": len(network_data.get("edges", [])),
                    },
                    {
                        "name": "nodeAttributes",
                        "elementCount": len(network_data.get("nodes", [])) * 3,
                    },
                    {"name": "edgeAttributes", "elementCount": 0},
                ]
            },
            {
                "nodes": [
                    {"@id": i, "n": node["label"]}
                    for i, node in enumerate(network_data.get("nodes", []))
                ]
            },
            {
                "edges": [
                    {"@id": i, "s": edge["source"], "t": edge["target"]}
                    for i, edge in enumerate(network_data.get("edges", []))
                ]
            },
            {"nodeAttributes": []},
            {"status": [{"error": "", "success": True}]},
        ]

        # Add node attributes
        for i, node in enumerate(network_data.get("nodes", [])):
            cx_data[4]["nodeAttributes"].extend(
                [
                    {"po": i, "n": "type", "v": node.get("type", "unknown")},
                    {"po": i, "n": "confidence", "v": node.get("confidence", 0.0)},
                    {"po": i, "n": "cited_by", "v": node.get("cited_by", 0)},
                ]
            )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cx_data, f, indent=2)

    def _write_graphml_file(
        self, network_data: Dict[str, Any], output_file: Path
    ) -> None:
        """Write network data to GraphML format."""
        graphml_content = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns
         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
    
    <key id="type" for="node" attr.name="type" attr.type="string"/>
    <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>
    <key id="cited_by" for="node" attr.name="cited_by" attr.type="int"/>
    <key id="weight" for="edge" attr.name="weight" attr.type="double"/>
    
    <graph id="dataset_citations" edgedefault="undirected">"""

        for node in network_data.get("nodes", []):
            graphml_content += f'''
        <node id="{node["id"]}">
            <data key="type">{node.get("type", "unknown")}</data>
            <data key="confidence">{node.get("confidence", 0.0)}</data>
            <data key="cited_by">{node.get("cited_by", 0)}</data>
        </node>'''

        for edge in network_data.get("edges", []):
            graphml_content += f'''
        <edge source="{edge["source"]}" target="{edge["target"]}">
            <data key="weight">{edge.get("weight", 1.0)}</data>
        </edge>'''

        graphml_content += """
    </graph>
</graphml>"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(graphml_content)

    def _create_csv_exports(self, analysis_data: Dict[str, Any]) -> List[Path]:
        """Create CSV export files for analysis data."""
        csv_files = []

        if not PANDAS_AVAILABLE:
            logging.warning("Pandas not available, skipping CSV exports")
            return csv_files

        # Export network analysis if available
        if analysis_data.get("network_analysis"):
            for analysis_name, data in analysis_data["network_analysis"].items():
                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    csv_file = self.output_dir / f"{analysis_name}.csv"
                    df.to_csv(csv_file, index=False)
                    csv_files.append(csv_file)

        # Export temporal analysis
        if analysis_data.get("temporal_analysis"):
            temporal_data = analysis_data["temporal_analysis"]
            if isinstance(temporal_data, dict):
                # Convert to DataFrame format
                df_data = []
                for key, value in temporal_data.items():
                    if isinstance(value, (int, float, str)):
                        df_data.append({"metric": key, "value": value})

                if df_data:
                    df = pd.DataFrame(df_data)
                    csv_file = self.output_dir / "temporal_analysis.csv"
                    df.to_csv(csv_file, index=False)
                    csv_files.append(csv_file)

        # Export theme analysis
        if analysis_data.get("theme_analysis"):
            for theme_name, data in analysis_data["theme_analysis"].items():
                if isinstance(data, dict) and data:
                    # Convert nested dict to flat structure
                    flat_data = []
                    for key, value in data.items():
                        if isinstance(value, (list, dict)):
                            flat_data.append({"item": key, "data": str(value)})
                        else:
                            flat_data.append({"item": key, "value": value})

                    if flat_data:
                        df = pd.DataFrame(flat_data)
                        csv_file = self.output_dir / f"{theme_name}_analysis.csv"
                        df.to_csv(csv_file, index=False)
                        csv_files.append(csv_file)

        return csv_files


def main() -> int:
    """Main entry point for interactive reports generation."""
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML reports with unified themes"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory containing analysis results (default: results)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("interactive_reports"),
        help="Output directory for generated reports (default: interactive_reports)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.results_dir.exists():
        logging.error(f"Results directory does not exist: {args.results_dir}")
        return 1

    try:
        # Initialize report generator
        generator = InteractiveReportGenerator(args.results_dir, args.output_dir)

        # Collect analysis results
        analysis_data = generator.collect_analysis_results()

        # Generate dashboard
        dashboard_file = generator.generate_dashboard(analysis_data)

        # Create export files
        export_files = generator.create_export_files(analysis_data)

        # Report summary
        print("\n🎉 Interactive Reports Generated Successfully!")
        print(f"\n📊 Main Dashboard: {dashboard_file}")
        print(f"🌐 Open in browser: file://{dashboard_file.absolute()}")

        print(f"\n📁 Export Files ({len(export_files)} created):")
        for file_path in export_files:
            print(f"   • {file_path.name}")

        print("\n📈 Analysis Summary:")
        print(
            f"   • {analysis_data['summary_stats']['total_datasets']} datasets analyzed"
        )
        print(
            f"   • {analysis_data['summary_stats']['total_citations']} high-confidence citations"
        )
        print(
            f"   • {analysis_data['summary_stats']['bridge_papers']} research bridge papers"
        )
        print(
            f"   • {len(analysis_data['summary_stats']['available_analyses'])} analysis types"
        )

        return 0

    except Exception as e:
        logging.error(f"Failed to generate interactive reports: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
