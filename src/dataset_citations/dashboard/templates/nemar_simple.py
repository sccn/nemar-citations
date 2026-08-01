"""
Simplified NEMAR dashboard template using modular components.
"""

import html as html_lib
import json
from typing import Any

from .components.charts import generate_chart_containers, generate_chart_javascript
from .components.header import generate_header
from .components.hero import generate_hero_section
from .components.network_viz import NetworkVisualization
from .components.styles import get_nemar_styles
from .modal_handler import ModalHandler


def generate_nemar_dashboard(
    stats: dict[str, Any],
    charts: dict[str, Any],
    networks: dict[str, Any],
    themes: dict[str, Any],
    modals: dict[str, Any],
    data: dict[str, Any] | None,
    data_file: str | None,
    timestamp: str,
) -> str:
    """Generate complete NEMAR dashboard HTML."""

    cards = stats.get("cards", [])

    # Build HTML sections
    header = generate_header(data_file=data_file)
    styles = get_nemar_styles() + NetworkVisualization.generate_styles()
    hero = generate_hero_section(cards)
    chart_containers = generate_chart_containers()
    chart_js = generate_chart_javascript(stats, charts)

    # Build themes section. Closes #79: each card always renders the
    # `top_words` as a styled tag cloud so the Research Themes tab has
    # content even if the wordcloud PNG generation failed. When the PNG is
    # present it is shown above the tags.
    theme_list = themes.get("themes", [])
    themes_html = '<div class="row">'
    for theme in theme_list:
        title = html_lib.escape(str(theme.get("title", "")))
        subtitle = html_lib.escape(str(theme.get("subtitle", "")))
        # `wordcloud` is None when PNG rendering failed (or no output_dir
        # was supplied); only emit the <img> tag when a real path is set.
        wordcloud_path = theme.get("wordcloud")
        wordcloud_src = html_lib.escape(str(wordcloud_path)) if wordcloud_path else None
        top_words = theme.get("top_words", []) or []
        # Decaying font sizes (1.6rem -> ~0.75rem) so the first phrase is
        # visually the largest, mirroring the upstream ranking.
        if top_words:
            tags = []
            n = max(len(top_words), 1)
            for idx, phrase in enumerate(top_words):
                phrase_text = html_lib.escape(str(phrase))
                weight = 1 - (idx / (n + 1))
                size_rem = round(0.75 + weight * 0.85, 2)
                tags.append(
                    f'<span class="theme-word" '
                    f'style="display:inline-block;'
                    f"margin:0.15rem 0.35rem;"
                    f"font-size:{size_rem}rem;"
                    f'color:#083d94;">{phrase_text}</span>'
                )
            tags_html = (
                '<div class="theme-words" style="line-height:1.8;'
                'text-align:center;margin-top:0.5rem;">' + "".join(tags) + "</div>"
            )
        else:
            tags_html = (
                '<p class="text-muted small">No top words available for this theme.</p>'
            )
        themes_html += f"""
                    <div class="col-md-6 mb-4">
                        <div class="card analysis-card">
                            <div class="card-header">
                                <h5><i class="fas fa-cloud me-2"></i>{title}</h5>
                                <small class="text-muted" style="color: rgba(255, 255, 255, 0.9) !important;">
                                    {subtitle}
                                </small>
                            </div>
                            <div class="card-body text-center">
                                {
            (
                f'<img src="{wordcloud_src}" '
                f'alt="{title} Word Cloud" '
                f'class="img-fluid rounded theme-wordcloud-img" '
                f'style="max-height: 300px; width: auto;" '
                f"onerror=\"this.style.display='none';\">"
            )
            if wordcloud_src
            else ""
        }
                                {tags_html}
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
            <p>&copy; 2025 <a href="https://github.com/nemarOrg/nemar-citations" target="_blank">
                <strong>NEMAR Dataset Citation Analysis</strong></a>, by <a href="https://neuromechanist.github.io" target="_blank">Seyed Yahya Shirazi</a></p>
            <p class="text-muted mb-2">
                <a href="https://nemar.org" target="_blank"><strong>NEMAR</strong></a> 
                is a window to <a href="https://openneuro.org" target="_blank">OpenNeuro</a>
            </p>
            <p class="text-muted small">Generated: {timestamp}</p>
        </div>
    </footer>
    
    <!-- Modals -->
    {ModalHandler.generate_modal_html()}

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Embedded data or lazy loading
        const analysisData = {json.dumps(data) if data else "{}"};
        
        {ModalHandler.generate_modal_javascript(modals)}
        
        {chart_js}
        
        {NetworkVisualization.generate_javascript(networks)}
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            initializeCharts();
        }});
    </script>
</body>
</html>"""

    return html
