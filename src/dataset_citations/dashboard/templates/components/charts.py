"""Chart visualization components."""

import json
from typing import Any, Dict


def generate_chart_containers() -> str:
    """Generate HTML containers for charts."""
    return """
                <div class="row">
                    <div class="col-md-4">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-bar me-2"></i>Citation Quality</h5>
                            </div>
                            <div class="card-body">
                                <div id="qualityChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-line me-2"></i>Growth Timeline</h5>
                            </div>
                            <div class="card-body">
                                <div id="growthChart" class="viz-container"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card analysis-card mb-4">
                            <div class="card-header">
                                <h5><i class="fas fa-brain me-2"></i>Data Modalities (EEG/MEG/iEEG)</h5>
                            </div>
                            <div class="card-body">
                                <div id="modalityChart" class="viz-container"></div>
                                <p class="text-muted small mt-2 text-center">
                                    Distribution of electrophysiological data types
                                </p>
                            </div>
                        </div>
                    </div>
                </div>"""


def generate_chart_javascript(stats: Dict[str, Any], charts: Dict[str, Any]) -> str:
    """Generate JavaScript for rendering charts."""

    quality = charts.get("quality_chart", {})
    growth = charts.get("growth_chart", {})
    modality = charts.get("modality_chart", {})

    # Get actual data or use defaults
    quality_x = quality.get("data", {}).get(
        "x", ["High-Confidence\\n(≥0.4)", "Low-Confidence\\n(<0.4)"]
    )
    quality_y = quality.get("data", {}).get("y", [0, 0])

    # Growth series comes from ChartGenerator._generate_growth_chart which
    # reads `temporal_analysis.temporal_summary`. Default to empty arrays so
    # we surface "no data" rather than a misleading hardcoded curve (the
    # source of #77's 10x scale bug).
    growth_x = growth.get("data", {}).get("x", [])
    growth_y = growth.get("data", {}).get("y", [])

    modality_values = modality.get("data", {}).get("values", [120, 45, 25])
    modality_labels = modality.get("data", {}).get("labels", ["EEG", "MEG", "iEEG"])

    return f"""
        function initializeCharts() {{
            createQualityChart();
            createGrowthChart();
            createModalityChart();
        }}
        
        function createQualityChart() {{
            const highConf = {quality_y[0] if quality_y else 0};
            const lowConf = {quality_y[1] if len(quality_y) > 1 else 0};
            const total = highConf + lowConf;
            
            const data = [{{
                x: {json.dumps(quality_x)},
                y: [highConf, lowConf],
                type: 'bar',
                marker: {{
                    color: ['#E94B3C', '#BDC3C7'],
                    line: {{ color: '#FFFFFF', width: 2 }}
                }},
                text: [
                    highConf + '<br>(' + (total > 0 ? Math.round(highConf/total*100) : 0) + '%)',
                    lowConf + '<br>(' + (total > 0 ? Math.round(lowConf/total*100) : 0) + '%)'
                ],
                textposition: 'inside',
                textfont: {{ color: 'white', size: 12, family: 'Arial' }}
            }}];
            
            const layout = {{
                font: {{ family: 'Open Sans, sans-serif', color: '#555555' }},
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                showlegend: false,
                height: 350,
                margin: {{ t: 20, b: 50, l: 50, r: 20 }},
                xaxis: {{ title: '' }},
                yaxis: {{ title: 'Count' }}
            }};
            
            Plotly.newPlot('qualityChart', data, layout, {{responsive: true}});
        }}
        
        function createGrowthChart() {{
            const data = [{{
                x: {json.dumps(growth_x)},
                y: {json.dumps(growth_y)},
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
                height: 350,
                margin: {{ t: 20, b: 50, l: 50, r: 20 }},
                xaxis: {{ title: 'Year' }},
                yaxis: {{ title: 'Cumulative Citations' }}
            }};
            
            Plotly.newPlot('growthChart', data, layout, {{responsive: true}});
        }}
        
        function createModalityChart() {{
            const data = [{{
                values: {json.dumps(modality_values)},
                labels: {json.dumps(modality_labels)},
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#3498DB', '#9B59B6', '#E74C3C']
                }},
                textinfo: 'label+percent',
                textposition: 'outside',
                hovertemplate: '%{{label}}: %{{value}} datasets<br>%{{percent}}<extra></extra>'
            }}];
            
            const layout = {{
                showlegend: true,
                height: 350,
                margin: {{ t: 20, b: 20, l: 20, r: 20 }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: {{ family: 'Open Sans, sans-serif', color: '#555555' }},
                legend: {{
                    orientation: 'v',
                    x: 1,
                    y: 0.5
                }}
            }};
            
            Plotly.newPlot('modalityChart', data, layout, {{responsive: true}});
        }}"""
