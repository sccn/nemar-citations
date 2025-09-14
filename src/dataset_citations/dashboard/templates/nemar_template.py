"""
NEMAR dashboard HTML template using modular components.
"""

from typing import Dict, Any, Optional, List
import json


class NEMARTemplate:
    """Generate complete NEMAR dashboard HTML using modular components."""

    @staticmethod
    def generate_html(
        stats: Dict[str, Any],
        charts: Dict[str, Any],
        networks: Dict[str, Any],
        themes: Dict[str, Any],
        modals: Dict[str, Any],
        data: Optional[Dict[str, Any]],
        data_file: Optional[str],
        timestamp: str,
    ) -> str:
        """Generate complete NEMAR dashboard HTML."""

        # Extract statistics
        cards = stats.get("cards", [])
        stats.get("summary", {})

        # Build statistics cards HTML
        stat_cards_html = NEMARTemplate._build_stat_cards(cards)

        # Build chart containers
        charts_html = NEMARTemplate._build_chart_containers()

        # Build network containers
        networks_html = NEMARTemplate._build_network_containers()

        # Build theme containers
        themes_html = NEMARTemplate._build_theme_containers(themes)

        # Build modals HTML
        modals_html = NEMARTemplate._build_modals(modals)

        # Build JavaScript for charts
        chart_js = NEMARTemplate._build_chart_javascript(stats, charts, data_file)

        # Build network JavaScript
        network_js = NEMARTemplate._build_network_javascript(networks, data)

        # Build the complete HTML
        html = f"""<!DOCTYPE html>
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
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <!-- Cytoscape.js -->
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    
    <!-- Dashboard Templates -->
    <script src="dashboard_templates.js"></script>
    <!-- Dashboard Styles -->
    <link href="dashboard_styles.css" rel="stylesheet">
    
    {NEMARTemplate._get_nemar_styles()}
</head>
<body style="background-color: #ffffff;">
    <!-- Hero Section -->
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="jumbotron bg-light p-5 rounded">
                    <h1 class="display-4">
                        <i class="fas fa-chart-network me-3"></i>
                        NEMAR Dataset Citation Analysis
                    </h1>
                    <p class="lead">
                        Comprehensive analysis of citation patterns, research themes, and network relationships 
                        across {cards[0]["value"] if cards else 0} BIDS datasets on NEMAR with confidence-filtered citations.
                    </p>
                    <hr class="my-4">
                    <div class="row">
                        {stat_cards_html}
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
                <button class="nav-link" id="themes-tab" data-bs-toggle="pill" data-bs-target="#themes" 
                        type="button" role="tab">
                    <i class="fas fa-tags me-2"></i>Research Themes
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content" id="analysisTabContent">
            <!-- Overview Tab -->
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                {charts_html}
            </div>
            
            <!-- Network Analysis Tab -->
            <div class="tab-pane fade" id="network" role="tabpanel">
                <h2 class="section-header">Network Analysis</h2>
                <p class="text-muted mb-4">
                    <i class="fas fa-info-circle me-1"></i>
                    Interactive network visualizations showing relationships between datasets and citations.
                </p>
                {networks_html}
            </div>

            <!-- Research Themes Tab -->
            <div class="tab-pane fade" id="themes" role="tabpanel">
                <h2 class="section-header">Research Theme Analysis</h2>
                <p class="text-muted mb-4">
                    <i class="fas fa-info-circle me-1"></i>
                    Word clouds showing key terms for each research theme cluster identified through UMAP analysis.
                </p>
                {themes_html}
            </div>
        </div>
    </div>

    <!-- Modals -->
    {modals_html}

    <!-- Footer -->
    <footer class="footer">
        <div class="container text-center">
            <p>&copy; 2025 <a href="https://github.com/sccn/nemar-citations" target="_blank" class="text-decoration-none">
                <strong>NEMAR Dataset Citation Analysis</strong></a>.</p>
            <p class="text-muted mb-2">
                <a href="https://nemar.org" target="_blank" class="text-decoration-none"><strong>NEMAR</strong></a> 
                is a window to <a href="https://openneuro.org" target="_blank" class="text-decoration-none">OpenNeuro</a> 
                for hosting and analyzing electrophysiological data (EEG, MEG, iEEG) from around the world.
            </p>
            <p class="text-muted small">
                Analysis: {timestamp}
            </p>
        </div>
    </footer>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Embedded analysis data (if not lazy loading)
        const analysisData = {json.dumps(data) if data else "{}"};
        
        {chart_js}
        
        {network_js}
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            initializeCharts();
            
            // Initialize networks when tab is shown
            document.getElementById('network-tab').addEventListener('shown.bs.tab', function() {{
                if (!window.networksInitialized) {{
                    createNetworkVisualization();
                    createCitationNetworkVisualization();
                    window.networksInitialized = true;
                }}
            }});
        }});
        
        // Modal functions
        function showDetailModal(type) {{
            const modal = new bootstrap.Modal(document.getElementById('detailModal'));
            updateModalContent(type);
            modal.show();
        }}
        
        function updateModalContent(type) {{
            // Update modal content based on type
            const modalBody = document.getElementById('detailModalBody');
            const modalTitle = document.getElementById('detailModalLabel');
            
            // Set content based on type (datasets, citations, bridges, threshold)
            // This would be populated from the modals data
        }}
    </script>
</body>
</html>"""

        return html

    @staticmethod
    def _build_stat_cards(cards: List[Dict[str, Any]]) -> str:
        """Build statistics cards HTML."""
        cards_html = ""
        for card in cards:
            cards_html += f"""
                <div class="col-md-3">
                    <div class="card stat-card" onclick="showDetailModal('{card["id"]}')" 
                         title="Click to see details">
                        <div class="card-body text-center">
                            <h3><i class="{card["icon"]} me-2"></i>{card["value"]}</h3>
                            <p class="mb-0">{card["label"]}</p>
                            <small class="text-muted">{card["detail"]}</small>
                        </div>
                    </div>
                </div>"""
        return cards_html

    @staticmethod
    def _build_chart_containers() -> str:
        """Build chart containers HTML."""
        return """
        <div class="row">
            <div class="col-md-4">
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-chart-bar me-2"></i>Citation Quality
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="qualityChart" class="viz-container"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-chart-line me-2"></i>Growth Timeline
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="growthChart" class="viz-container"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-brain me-2"></i>Data Modalities
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="modalityChart" class="viz-container"></div>
                    </div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _build_network_containers() -> str:
        """Build network visualization containers."""
        return """
        <div class="row">
            <div class="col-md-6">
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-network-wired me-2"></i>Dataset Map
                        </h5>
                        <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                            Datasets positioned using semantic coordinates
                        </small>
                    </div>
                    <div class="card-body">
                        <div id="networkViz" class="network-container" style="height: 500px;"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card analysis-card mb-4">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-quote-left me-2"></i>Citation Map
                        </h5>
                        <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                            Citations positioned using semantic coordinates
                        </small>
                    </div>
                    <div class="card-body">
                        <div id="citationNetworkViz" class="network-container" style="height: 500px;"></div>
                    </div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _build_theme_containers(themes: Dict[str, Any]) -> str:
        """Build theme visualization containers."""
        theme_list = themes.get("themes", [])
        html = '<div class="row">'

        for theme in theme_list:
            html += f"""
            <div class="col-md-6 mb-4">
                <div class="card analysis-card">
                    <div class="card-header">
                        <h5 style="color: #ffffff !important;">
                            <i class="fas fa-cloud me-2"></i>{theme["title"]}
                        </h5>
                        <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                            {theme["subtitle"]}
                        </small>
                    </div>
                    <div class="card-body text-center">
                        <img src="{theme["wordcloud"]}" 
                             alt="{theme["title"]} Word Cloud" 
                             class="img-fluid rounded" 
                             style="max-height: 300px; width: auto;">
                    </div>
                </div>
            </div>"""

        html += "</div>"
        return html

    @staticmethod
    def _build_modals(modals: Dict[str, Any]) -> str:
        """Build modal dialogs HTML."""
        return """
        <div class="modal fade" id="detailModal" tabindex="-1" aria-labelledby="detailModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="detailModalLabel">Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="detailModalBody">
                        <!-- Dynamic content will be inserted here -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _build_chart_javascript(
        stats: Dict[str, Any], charts: Dict[str, Any], data_file: Optional[str]
    ) -> str:
        """Build JavaScript for charts."""
        stats.get("summary", {})
        quality = charts.get("quality_chart", {})
        growth = charts.get("growth_chart", {})
        modality = charts.get("modality_chart", {})

        return f"""
        // Color scheme
        const colorScheme = {{
            primary: '#083d94',
            accent: '#e1d295',
            citation: '#E94B3C',
            bridge: '#50C878'
        }};
        
        function initializeCharts() {{
            createQualityChart();
            createGrowthChart();
            createModalityChart();
        }}
        
        function createQualityChart() {{
            const data = [{{
                x: {json.dumps(quality.get("data", {}).get("x", []))},
                y: {json.dumps(quality.get("data", {}).get("y", []))},
                type: 'bar',
                marker: {{
                    color: ['#E94B3C', '#BDC3C7'],
                    line: {{ color: '#FFFFFF', width: 2 }}
                }},
                textposition: 'inside',
                textfont: {{ color: 'white', size: 12 }}
            }}];
            
            const layout = {{
                font: {{ family: 'Open Sans, sans-serif', color: '#555555' }},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                showlegend: false,
                margin: {{ t: 20, b: 50, l: 50, r: 20 }},
                xaxis: {{ title: '' }},
                yaxis: {{ title: 'Count' }}
            }};
            
            Plotly.newPlot('qualityChart', data, layout, {{responsive: true}});
        }}
        
        function createGrowthChart() {{
            const data = [{{
                x: {json.dumps(growth.get("data", {}).get("x", []))},
                y: {json.dumps(growth.get("data", {}).get("y", []))},
                type: 'scatter',
                mode: 'lines+markers',
                line: {{ 
                    color: '#083d94', 
                    width: 4,
                    shape: 'spline'
                }},
                marker: {{ 
                    size: 8, 
                    color: '#083d94',
                    line: {{ color: '#FFFFFF', width: 2 }}
                }},
                fill: 'tonexty',
                fillcolor: 'rgba(8, 61, 148, 0.1)'
            }}];
            
            const layout = {{
                font: {{ family: 'Open Sans, sans-serif', color: '#555555' }},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                showlegend: false,
                margin: {{ t: 20, b: 50, l: 50, r: 20 }},
                xaxis: {{ title: 'Year' }},
                yaxis: {{ title: 'Cumulative Citations' }}
            }};
            
            Plotly.newPlot('growthChart', data, layout, {{responsive: true}});
        }}
        
        function createModalityChart() {{
            const data = [{{
                values: {json.dumps(modality.get("data", {}).get("values", []))},
                labels: {json.dumps(modality.get("data", {}).get("labels", []))},
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#3498DB', '#9B59B6', '#E74C3C']
                }},
                textinfo: 'label+percent',
                hovertemplate: '%{{label}}: %{{value}} datasets<br>%{{percent}}<extra></extra>'
            }}];
            
            const layout = {{
                showlegend: true,
                height: 385,
                margin: {{ t: 20, b: 20, l: 20, r: 20 }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {{ family: 'Open Sans, sans-serif', color: '#555555' }}
            }};
            
            Plotly.newPlot('modalityChart', data, layout, {{responsive: true}});
        }}"""

    @staticmethod
    def _build_network_javascript(
        networks: Dict[str, Any], data: Optional[Dict[str, Any]]
    ) -> str:
        """Build JavaScript for network visualizations."""
        dataset_net = networks.get("dataset_network", {})
        citation_net = networks.get("citation_network", {})

        return f"""
        function createNetworkVisualization() {{
            const elements = {json.dumps(dataset_net.get("nodes", []))};
            
            const cy = cytoscape({{
                container: document.getElementById('networkViz'),
                elements: elements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'background-color': '#4A90E2',
                            'label': 'data(label)',
                            'width': 'mapData(citations, 0, 100, 10, 30)',
                            'height': 'mapData(citations, 0, 100, 10, 30)'
                        }}
                    }}
                ],
                layout: {{
                    name: 'grid',
                    fit: true,
                    padding: 30
                }}
            }});
        }}
        
        function createCitationNetworkVisualization() {{
            const elements = {json.dumps(citation_net.get("nodes", []))};
            
            const cy = cytoscape({{
                container: document.getElementById('citationNetworkViz'),
                elements: elements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'background-color': '#E94B3C',
                            'width': 'mapData(impact, 0, 100, 8, 20)',
                            'height': 'mapData(impact, 0, 100, 8, 20)'
                        }}
                    }}
                ],
                layout: {{
                    name: 'grid',
                    fit: true,
                    padding: 30
                }}
            }});
        }}"""

    @staticmethod
    def _get_nemar_styles() -> str:
        """Get NEMAR-specific styles."""
        return """
    <style>
        /* NEMAR Theme Styles */
        :root {
            --nemar-primary-blue: #083d94;
            --nemar-text-gray: #555555;
            --nemar-accent-gold: #e1d295;
            --nemar-light-gray: #f8f9fa;
            --nemar-border-gray: #dee2e6;
        }
        
        body {
            font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            color: var(--nemar-text-gray);
            font-size: 14px;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: var(--nemar-primary-blue);
            font-weight: 600;
        }
        
        h1 {
            border-bottom: 3px solid var(--nemar-accent-gold);
            padding-bottom: 0.75rem;
        }
        
        .stat-card {
            background: white;
            border: 2px solid var(--nemar-border-gray);
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .stat-card:hover {
            border-color: var(--nemar-primary-blue);
            box-shadow: 0 6px 20px rgba(8, 61, 148, 0.12);
            transform: translateY(-3px);
        }
        
        .card-header {
            background-color: var(--nemar-primary-blue) !important;
            color: white !important;
            border-bottom: 3px solid var(--nemar-accent-gold) !important;
        }
        
        .nav-pills .nav-link {
            color: var(--nemar-text-gray);
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            margin-right: 0.5rem;
        }
        
        .nav-pills .nav-link.active {
            background-color: var(--nemar-primary-blue);
        }
        
        .viz-container {
            min-height: 300px;
        }
        
        .network-container {
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        footer {
            background: linear-gradient(to bottom, white, var(--nemar-light-gray));
            border-top: 3px solid var(--nemar-accent-gold);
            padding: 2rem 0;
            margin-top: 3rem;
        }
    </style>"""
