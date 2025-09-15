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
                showNodeDetails('dataset', data);
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
                showNodeDetails('citation', data);
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
        
        function showNodeDetails(type, data) {{
            let content = '';
            if (type === 'dataset') {{
                content = `
                    <h5>${{data.label || data.id}}</h5>
                    <p><strong>Dataset ID:</strong> ${{data.id}}</p>
                    <p><strong>Citations:</strong> ${{data.citations || 0}}</p>
                `;
            }} else if (type === 'citation') {{
                content = `
                    <h5>${{data.title || data.label}}</h5>
                    <p><strong>Year:</strong> ${{data.year || 'N/A'}}</p>
                    <p><strong>Impact Score:</strong> ${{data.impact || 0}}</p>
                `;
            }}
            
            // Show in a modal or tooltip
            const modal = new bootstrap.Modal(document.getElementById('nodeDetailsModal') || createNodeDetailsModal());
            document.querySelector('#nodeDetailsModal .modal-body').innerHTML = content;
            modal.show();
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
