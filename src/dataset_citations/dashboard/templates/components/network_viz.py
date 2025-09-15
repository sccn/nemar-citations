"""
Cytoscape.js network visualization component.
"""

from typing import Dict, Any


class NetworkVisualization:
    """Generate Cytoscape.js network visualization JavaScript."""

    @staticmethod
    def generate_javascript(network_data: Dict[str, Any]) -> str:
        """
        Generate JavaScript code for network visualization.

        Args:
            network_data: Network data with nodes, edges, and configuration

        Returns:
            JavaScript code string
        """
        return f"""
        // Network Visualization with Cytoscape.js
        let cyDataset = null;
        let cyCitation = null;
        
        function initializeNetworkVisualizations() {{
            // Dataset Network
            createDatasetNetwork();
            
            // Citation Network  
            createCitationNetwork();
            
            // Add resize listeners
            window.addEventListener('resize', () => {{
                if (cyDataset) cyDataset.resize();
                if (cyCitation) cyCitation.resize();
            }});
        }}
        
        function createDatasetNetwork() {{
            const container = document.getElementById('networkViz');
            if (!container) return;
            
            // Clear loading message
            container.innerHTML = '';
            
            // Create Cytoscape instance
            cyDataset = cytoscape({{
                container: container,
                elements: {{
                    nodes: {network_data.get("dataset_network", {}).get("nodes", []).__repr__()},
                    edges: {network_data.get("dataset_network", {}).get("edges", []).__repr__()}
                }},
                style: {network_data.get("cytoscape_config", {}).get("style", []).__repr__()},
                layout: {{
                    name: 'preset',
                    fit: true,
                    padding: 30
                }},
                minZoom: 0.2,
                maxZoom: 5,
                wheelSensitivity: 0.2
            }});
            
            // Add interactivity
            cyDataset.on('tap', 'node', function(evt) {{
                const node = evt.target;
                const data = node.data();
                showNodeDetails('dataset', data, 'networkViz');
            }});
            
            // Add controls
            addNetworkControls('networkViz', cyDataset);
        }}
        
        function createCitationNetwork() {{
            const container = document.getElementById('citationNetworkViz');
            if (!container) return;
            
            // Clear loading message
            container.innerHTML = '';
            
            // Create Cytoscape instance
            cyCitation = cytoscape({{
                container: container,
                elements: {{
                    nodes: {network_data.get("citation_network", {}).get("nodes", []).__repr__()},
                    edges: {network_data.get("citation_network", {}).get("edges", []).__repr__()}
                }},
                style: {network_data.get("cytoscape_config", {}).get("style", []).__repr__()},
                layout: {{
                    name: 'preset',
                    fit: true,
                    padding: 30
                }},
                minZoom: 0.2,
                maxZoom: 5,
                wheelSensitivity: 0.2
            }});
            
            // Add interactivity
            cyCitation.on('tap', 'node', function(evt) {{
                const node = evt.target;
                const data = node.data();
                showNodeDetails('citation', data, 'citationNetworkViz');
            }});
            
            // Add controls
            addNetworkControls('citationNetworkViz', cyCitation);
        }}
        
        function addNetworkControls(containerId, cy) {{
            const container = document.getElementById(containerId);
            const controls = document.createElement('div');
            controls.className = 'network-controls';
            controls.style.cssText = 'position: absolute; top: 10px; right: 10px; z-index: 1000;';
            controls.innerHTML = `
                <div class="btn-group-vertical" role="group">
                    <button class="btn btn-sm btn-outline-secondary" onclick="networkZoomIn('${{containerId}}')">
                        <i class="fas fa-plus"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="networkZoomOut('${{containerId}}')">
                        <i class="fas fa-minus"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="networkFit('${{containerId}}')">
                        <i class="fas fa-expand"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="networkCenter('${{containerId}}')">
                        <i class="fas fa-crosshairs"></i>
                    </button>
                </div>
            `;
            container.appendChild(controls);
        }}
        
        function networkZoomIn(containerId) {{
            const cy = containerId === 'networkViz' ? cyDataset : cyCitation;
            if (cy) cy.zoom(cy.zoom() * 1.2);
        }}
        
        function networkZoomOut(containerId) {{
            const cy = containerId === 'networkViz' ? cyDataset : cyCitation;
            if (cy) cy.zoom(cy.zoom() * 0.8);
        }}
        
        function networkFit(containerId) {{
            const cy = containerId === 'networkViz' ? cyDataset : cyCitation;
            if (cy) cy.fit();
        }}
        
        function networkCenter(containerId) {{
            const cy = containerId === 'networkViz' ? cyDataset : cyCitation;
            if (cy) cy.center();
        }}
        
        function showNodeDetails(type, data, containerId) {{
            // Find or create info panel below the network
            let infoPanel = document.getElementById(containerId + '-info');
            if (!infoPanel) {{
                const container = document.getElementById(containerId);
                infoPanel = document.createElement('div');
                infoPanel.id = containerId + '-info';
                infoPanel.className = 'network-info-panel mt-3';
                container.parentElement.appendChild(infoPanel);
            }}
            
            let content = '';
            if (type === 'dataset') {{
                const nemarUrl = `https://nemar.org/dataexplorer/detail?dataset_id=${{data.id}}`;
                content = `
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <i class="fas fa-database me-2"></i>Dataset Information
                        </div>
                        <div class="card-body">
                            <p><strong>Dataset ID:</strong> <a href="${{nemarUrl}}" target="_blank">${{data.id}}</a></p>
                            <p><strong>Name:</strong> ${{data.name || 'N/A'}}</p>
                            <p><strong>Total Citations:</strong> ${{data.citations || 0}}</p>
                        </div>
                    </div>
                `;
            }} else if (type === 'citation') {{
                // Create Google Scholar search URL
                const googleScholarUrl = data.title ? 
                    `https://scholar.google.com/scholar?q=${{encodeURIComponent(data.title)}}` : 
                    '#';
                
                content = `
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <i class="fas fa-quote-right me-2"></i>Citation Information
                        </div>
                        <div class="card-body">
                            <p><strong>Title:</strong> ${{data.title ? 
                                `<a href="${{googleScholarUrl}}" target="_blank" class="text-decoration-none">
                                    ${{data.title}} <i class="fas fa-external-link-alt ms-1 small"></i>
                                </a>` : 
                                'N/A'}}</p>
                            <p><strong>Citations:</strong> ${{data.citations || 0}}</p>
                            <p><strong>Confidence Score:</strong> ${{data.confidence ? (data.confidence * 100).toFixed(1) + '%' : 'N/A'}}</p>
                            <p class="text-muted small mt-2">
                                <i class="fas fa-search me-1"></i>Click title to search on Google Scholar
                            </p>
                        </div>
                    </div>
                `;
            }}
            
            infoPanel.innerHTML = content;
        }}
        
        function createNodeDetailsModal() {{
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'nodeDetailsModal';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Node Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body"></div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            return modal;
        }}
        
        // Initialize when network tab is shown
        document.addEventListener('DOMContentLoaded', function() {{
            const networkTab = document.getElementById('network-tab');
            if (networkTab) {{
                networkTab.addEventListener('shown.bs.tab', function() {{
                    if (!window.networksInitialized) {{
                        initializeNetworkVisualizations();
                        window.networksInitialized = true;
                    }}
                }});
            }}
        }});
        """

    @staticmethod
    def generate_styles() -> str:
        """Generate CSS styles for network visualization."""
        return """
        <style>
        #networkViz, #citationNetworkViz {
            height: 600px;
            width: 100%;
            position: relative;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }
        
        .network-controls {
            background: white;
            border-radius: 4px;
            padding: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .network-controls .btn {
            padding: 0.25rem 0.5rem;
            margin: 2px 0;
        }
        
        .network-info {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-size: 12px;
        }
        </style>
        """
