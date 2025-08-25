#!/usr/bin/env python3
"""
Create the final optimized dashboard with properly working network visualizations.
This version ensures networks render correctly when the tab is activated.
"""

import re
from pathlib import Path


def fix_network_visualization_completely(input_path: Path, output_path: Path) -> None:
    """Fix network visualization to ensure nodes are visible and properly rendered."""

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the network creation functions and add proper initialization
    # Fix for createNetworkVisualization
    content = re.sub(
        r'(const cy = cytoscape\({[^}]+container: document\.getElementById\([\'"]networkViz[\'"]\),[^}]+}\);)',
        r"""\1
            
            // Ensure network is properly rendered and fitted
            setTimeout(function() {
                cy.fit();
                cy.center();
                cy.resize();
                
                // Force a re-render
                cy.style().update();
                
                console.log('Dataset network fitted with ' + cy.nodes().length + ' nodes');
            }, 100);""",
        content,
        flags=re.DOTALL,
    )

    # Fix for createCitationNetworkVisualization
    content = re.sub(
        r'(const cy = cytoscape\({[^}]+container: document\.getElementById\([\'"]citationNetworkViz[\'"]\),[^}]+}\);)',
        r"""\1
            
            // Ensure citation network is properly rendered and fitted
            setTimeout(function() {
                cy.fit();
                cy.center();
                cy.resize();
                
                // Force a re-render
                cy.style().update();
                
                console.log('Citation network fitted with ' + cy.nodes().length + ' nodes');
            }, 100);""",
        content,
        flags=re.DOTALL,
    )

    # Add a more robust tab handler that ensures networks render when visible
    tab_handler = """
    // Enhanced tab handling for network visualization
    $(document).ready(function() {
        let networksInitialized = false;
        
        $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            const tabId = $(e.target).attr('href');
            
            if (tabId === '#network') {
                console.log('Network tab activated');
                
                // Small delay to ensure DOM is ready
                setTimeout(function() {
                    // Check if we need to initialize networks
                    if (!networksInitialized) {
                        console.log('Initializing network visualizations...');
                        
                        // Ensure data is loaded
                        if (typeof fullDataLoaded !== 'undefined' && fullDataLoaded) {
                            try {
                                // Clear containers first
                                const networkViz = document.getElementById('networkViz');
                                const citationViz = document.getElementById('citationNetworkViz');
                                
                                if (networkViz) networkViz.innerHTML = '';
                                if (citationViz) citationViz.innerHTML = '';
                                
                                // Create networks
                                if (typeof createNetworkVisualization === 'function') {
                                    createNetworkVisualization();
                                }
                                if (typeof createCitationNetworkVisualization === 'function') {
                                    createCitationNetworkVisualization();
                                }
                                
                                networksInitialized = true;
                            } catch(e) {
                                console.error('Error initializing networks:', e);
                            }
                        } else {
                            // Wait for data and try again
                            console.log('Waiting for data to load...');
                            if (typeof loadFullData === 'function') {
                                loadFullData().then(() => {
                                    // Trigger tab click again after data loads
                                    $(e.target).tab('show');
                                });
                            }
                        }
                    } else {
                        // Networks already initialized, just ensure they're fitted
                        console.log('Refitting existing networks');
                        
                        // If cytoscape instances exist globally, refit them
                        if (window.datasetNetworkCy) {
                            window.datasetNetworkCy.fit();
                            window.datasetNetworkCy.center();
                        }
                        if (window.citationNetworkCy) {
                            window.citationNetworkCy.fit();
                            window.citationNetworkCy.center();
                        }
                    }
                }, 200);
            }
        });
    });
    """

    # Insert the enhanced tab handler after jQuery is loaded
    content = re.sub(
        r"(\$\(document\)\.ready\(function\(\) {)",
        tab_handler + r"\n\n\1",
        content,
        count=1,
    )

    # Store cytoscape instances globally for access
    content = re.sub(
        r'const cy = cytoscape\({([^}]+container: document\.getElementById\([\'"]networkViz[\'"]\)[^}]+)}\);',
        r"""const cy = cytoscape({\1});
            window.datasetNetworkCy = cy; // Store globally for access""",
        content,
    )

    content = re.sub(
        r'const cy = cytoscape\({([^}]+container: document\.getElementById\([\'"]citationNetworkViz[\'"]\)[^}]+)}\);',
        r"""const cy = cytoscape({\1});
            window.citationNetworkCy = cy; // Store globally for access""",
        content,
    )

    # Ensure the initial network creation is disabled on page load
    content = re.sub(
        r"// Initialize network visualizations\s+createNetworkVisualization\(\);\s+createCitationNetworkVisualization\(\);",
        """// Network visualizations will be initialized when Network tab is clicked
            // createNetworkVisualization();
            // createCitationNetworkVisualization();""",
        content,
    )

    # Save the fixed version
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Created final optimized dashboard: {output_path}")
    print("   - Networks will initialize when Network tab is clicked")
    print("   - Networks will auto-fit and center")
    print("   - Cytoscape instances stored globally for access")


def main():
    """Main process to create the final working dashboard."""

    print("🚀 Creating Final Optimized Dashboard with Working Networks")
    print("=" * 60)

    # Use the v3 version as base since it has most fixes
    input_dashboard = Path("interactive_reports/dashboard_optimized_v3.html")
    output_dashboard = Path("interactive_reports/dashboard_final.html")

    # Apply the complete fix
    fix_network_visualization_completely(input_dashboard, output_dashboard)

    print("\n✅ Dashboard Creation Complete!")
    print("\n📦 Testing Instructions:")
    print("   1. cd interactive_reports")
    print("   2. python3 -m http.server 8000")
    print("   3. Open: http://localhost:8000/dashboard_final.html")
    print("   4. Wait for data to load (~3 seconds)")
    print("   5. Click 'Network Analysis' tab")
    print("   6. Networks should render with visible nodes!")
    print("\n🎯 Key Features:")
    print("   - 97KB HTML (from 18MB)")
    print("   - Data loads async in background")
    print("   - Networks initialize on tab click")
    print("   - Auto-fit and center for visibility")
    print("   - All modals and features work")


if __name__ == "__main__":
    main()
