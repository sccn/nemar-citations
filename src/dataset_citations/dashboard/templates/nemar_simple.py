"""
Simplified NEMAR dashboard template using modular components.
"""

from typing import Dict, Any, Optional
import json

from .components.header import generate_header
from .components.styles import get_nemar_styles
from .components.hero import generate_hero_section
from .components.charts import generate_chart_containers, generate_chart_javascript


def generate_nemar_dashboard(
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

    cards = stats.get("cards", [])

    # Build HTML sections
    header = generate_header(data_file=data_file)
    styles = get_nemar_styles()
    hero = generate_hero_section(cards)
    chart_containers = generate_chart_containers()
    chart_js = generate_chart_javascript(stats, charts)

    # Build themes section
    theme_list = themes.get("themes", [])
    themes_html = '<div class="row">'
    for theme in theme_list:
        themes_html += f"""
                    <div class="col-md-6 mb-4">
                        <div class="card analysis-card">
                            <div class="card-header">
                                <h5><i class="fas fa-cloud me-2"></i>{theme["title"]}</h5>
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
    themes_html += "</div>"

    # Build network containers
    networks_html = """
                <div class="row">
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-network-wired me-2"></i>Dataset Map</h5>
                                <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                                    Datasets positioned using semantic coordinates
                                </small>
                            </div>
                            <div class="card-body">
                                <div id="networkViz" class="network-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-quote-left me-2"></i>Citation Map</h5>
                                <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                                    Citations positioned using semantic coordinates
                                </small>
                            </div>
                            <div class="card-body">
                                <div id="citationNetworkViz" class="network-container"></div>
                            </div>
                        </div>
                    </div>
                </div>"""

    # Assemble complete HTML
    html = f"""{header}
{styles}
<body style="background-color: #ffffff;">
    {hero}

    <!-- Main Content -->
    <div class="container mt-4">
        <!-- Navigation Tabs -->
        <ul class="nav nav-pills mb-4" id="analysisTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="pill" 
                        data-bs-target="#overview" type="button" role="tab">
                    <i class="fas fa-home me-2"></i>Overview
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="network-tab" data-bs-toggle="pill" 
                        data-bs-target="#network" type="button" role="tab">
                    <i class="fas fa-project-diagram me-2"></i>Network Analysis
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="themes-tab" data-bs-toggle="pill" 
                        data-bs-target="#themes" type="button" role="tab">
                    <i class="fas fa-tags me-2"></i>Research Themes
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content" id="analysisTabContent">
            <!-- Overview Tab -->
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                {chart_containers}
            </div>
            
            <!-- Network Analysis Tab -->
            <div class="tab-pane fade" id="network" role="tabpanel">
                <h2>Network Analysis</h2>
                <p class="text-muted mb-4">
                    Interactive network visualizations showing relationships between datasets and citations.
                </p>
                {networks_html}
            </div>

            <!-- Research Themes Tab -->
            <div class="tab-pane fade" id="themes" role="tabpanel">
                <h2>Research Theme Analysis</h2>
                <p class="text-muted mb-4">
                    Word clouds showing key terms for each research theme cluster.
                </p>
                {themes_html}
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer">
        <div class="container text-center">
            <p>&copy; 2025 <a href="https://github.com/sccn/nemar-citations" target="_blank">
                <strong>NEMAR Dataset Citation Analysis</strong></a></p>
            <p class="text-muted mb-2">
                <a href="https://nemar.org" target="_blank"><strong>NEMAR</strong></a> 
                is a window to <a href="https://openneuro.org" target="_blank">OpenNeuro</a>
            </p>
            <p class="text-muted small">Generated: {timestamp}</p>
        </div>
    </footer>
    
    <!-- Modals -->
    <div class="modal fade" id="detailModal" tabindex="-1" aria-labelledby="detailModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="detailModalLabel">Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" id="detailModalBody">
                    <!-- Content will be dynamically inserted here -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Embedded data or lazy loading
        const analysisData = {json.dumps(data) if data else "{}"};
        
        {chart_js}
        
        // Simple network visualization
        function createNetworkVisualization() {{
            const container = document.getElementById('networkViz');
            container.innerHTML = '<p class="text-center mt-5">Network visualization loading...</p>';
        }}
        
        function createCitationNetworkVisualization() {{
            const container = document.getElementById('citationNetworkViz');
            container.innerHTML = '<p class="text-center mt-5">Citation network loading...</p>';
        }}
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            initializeCharts();
            
            // Load networks when tab is shown
            document.getElementById('network-tab').addEventListener('shown.bs.tab', function() {{
                if (!window.networksInitialized) {{
                    createNetworkVisualization();
                    createCitationNetworkVisualization();
                    window.networksInitialized = true;
                }}
            }});
        }});
        
        // Modal handler
        function showDetailModal(type) {{
            const modal = new bootstrap.Modal(document.getElementById('detailModal'));
            const modalTitle = document.getElementById('detailModalLabel');
            const modalBody = document.getElementById('detailModalBody');
            
            let content = '';
            
            switch(type) {{
                case 'datasets':
                    modalTitle.textContent = 'Dataset Analysis Details';
                    content = `
                        <h6>Overview</h6>
                        <p>Analyzing <strong>302 BIDS datasets</strong> from the NEMAR/OpenNeuro repository.</p>
                        <ul>
                            <li>Total datasets analyzed: 302</li>
                            <li>Datasets with citations: 302</li>
                            <li>Coverage: 100%</li>
                        </ul>
                        <p class="text-muted">Datasets are from the Brain Imaging Data Structure (BIDS) repository, 
                        with citation data collected from Google Scholar and filtered by confidence scores.</p>
                    `;
                    break;
                    
                case 'citations':
                    modalTitle.textContent = 'Citation Details';
                    content = `
                        <h6>High-Confidence Citations</h6>
                        <p>Found <strong>1004 high-confidence citations</strong> out of 1191 total citations.</p>
                        <ul>
                            <li>High-confidence (≥0.4): 1004 citations (84%)</li>
                            <li>Low-confidence (<0.4): 187 citations (16%)</li>
                            <li>Confidence threshold: 0.4</li>
                        </ul>
                        <p class="text-muted">Citations are scored using AI-based relevance matching with 
                        sentence transformers to ensure accuracy.</p>
                    `;
                    break;
                    
                case 'bridges':
                    modalTitle.textContent = 'Research Bridge Papers';
                    content = `
                        <h6>Papers Connecting Multiple Datasets</h6>
                        <p>Identified <strong>80 research bridge papers</strong> that cite multiple datasets.</p>
                        <p>These papers represent interdisciplinary research that connects different datasets, 
                        enabling cross-dataset analysis and validation.</p>
                        <p class="text-muted">Bridge papers are crucial for understanding relationships between 
                        different neuroscience datasets and research domains.</p>
                    `;
                    break;
                    
                case 'threshold':
                    modalTitle.textContent = 'Confidence Scoring Methodology';
                    content = `
                        <h6>AI-Based Confidence Scoring</h6>
                        <p>Using confidence threshold of <strong>≥0.4</strong> for citation filtering.</p>
                        <h6>How it works:</h6>
                        <ul>
                            <li>Citations are embedded using sentence transformers</li>
                            <li>Semantic similarity is computed between citation and dataset descriptions</li>
                            <li>Confidence scores range from 0 (unrelated) to 1 (perfect match)</li>
                            <li>Threshold of 0.4 ensures high-quality, relevant citations</li>
                        </ul>
                        <p class="text-muted">This approach reduces false positives and ensures that only 
                        genuinely relevant citations are included in the analysis.</p>
                    `;
                    break;
                    
                default:
                    modalTitle.textContent = 'Information';
                    content = '<p>No additional information available.</p>';
            }}
            
            modalBody.innerHTML = content;
            modal.show();
        }}
    </script>
</body>
</html>"""

    return html
