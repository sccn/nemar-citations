#!/usr/bin/env python3
"""
Fix network visualization issues in the optimized dashboard.
"""

import re
from pathlib import Path


def fix_network_initialization(html_path: Path, output_path: Path) -> None:
    """Fix network visualization initialization issues."""

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find and replace the tab switching logic to properly initialize networks
    # Look for the Bootstrap tab event handler
    tab_handler_pattern = r"(\$\('a\[data-toggle=\"tab\"\]'\)\.on\('shown\.bs\.tab', function \(e\) \{[^}]+\})"

    # Create improved tab handler that initializes networks when needed
    improved_handler = """$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        const tabId = $(e.target).attr('href');
        
        if (tabId === '#network') {
            // Initialize network visualizations when Network tab is shown
            setTimeout(function() {
                // Check if networks are already initialized
                const datasetChart = document.querySelector('#datasetNetworkChart');
                const citationChart = document.querySelector('#citationNetworkChart');
                
                if (datasetChart && citationChart) {
                    // Check if charts are empty (not initialized)
                    if (!datasetChart.querySelector('canvas')) {
                        console.log('Initializing network visualizations...');
                        
                        // Ensure data is loaded before creating visualizations
                        if (fullDataLoaded) {
                            createNetworkVisualization();
                            createCitationNetworkVisualization();
                        } else {
                            // Wait for data to load
                            loadFullData().then(() => {
                                createNetworkVisualization();
                                createCitationNetworkVisualization();
                            });
                        }
                    }
                }
            }, 100); // Small delay to ensure DOM is ready
        }
    })"""

    # Replace the tab handler
    if re.search(tab_handler_pattern, content):
        content = re.sub(tab_handler_pattern, improved_handler, content)
        print("✅ Fixed tab handler for network initialization")
    else:
        # If no existing handler, add it after document ready
        ready_pattern = r"(\$\(document\)\.ready\(function\(\) \{)"
        if re.search(ready_pattern, content):
            content = re.sub(
                ready_pattern, r"\1\n    " + improved_handler + ";\n", content
            )
            print("✅ Added tab handler for network initialization")

    # Also fix the initial network initialization - don't run on page load
    # Comment out the automatic initialization
    content = re.sub(
        r"(\s+// Initialize network visualizations\s+createNetworkVisualization\(\);\s+createCitationNetworkVisualization\(\);)",
        r"""
            // Network visualizations will be initialized when tab is shown
            // createNetworkVisualization();
            // createCitationNetworkVisualization();""",
        content,
    )

    # Fix the refresh after data load
    content = re.sub(
        r"(// Refresh network visualizations with full data\s+const networkTab[^}]+})",
        r"""// Refresh network visualizations with full data
                const networkTab = document.querySelector('[role="tab"][aria-controls="network"]');
                if (networkTab && networkTab.classList.contains('active')) {
                    // If network tab is currently active, refresh it
                    setTimeout(function() {
                        const datasetChart = document.querySelector('#datasetNetworkChart');
                        const citationChart = document.querySelector('#citationNetworkChart');
                        if (datasetChart && citationChart) {
                            datasetChart.innerHTML = '';
                            citationChart.innerHTML = '';
                            createNetworkVisualization();
                            createCitationNetworkVisualization();
                        }
                    }, 100);
                }""",
        content,
    )

    # Save fixed version
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Created fixed dashboard: {output_path}")
    print("   Network visualizations will now initialize when tab is clicked")


def main():
    """Main fixing process."""

    print("🔧 Fixing Network Visualization Issues")
    print("=" * 50)

    # Paths
    input_dashboard = Path("interactive_reports/dashboard_optimized_v2.html")
    output_dashboard = Path("interactive_reports/dashboard_optimized_v3.html")

    # Fix the dashboard
    fix_network_initialization(input_dashboard, output_dashboard)

    print("\n✅ Fix Complete!")
    print("\n📦 Testing Instructions:")
    print("   1. Start server: cd interactive_reports && python3 -m http.server 8000")
    print("   2. Open: http://localhost:8000/dashboard_optimized_v3.html")
    print("   3. Click on 'Network Analysis' tab")
    print("   4. Networks should now render properly!")


if __name__ == "__main__":
    main()
