#!/usr/bin/env python3
"""
Create a properly optimized dashboard that maintains all functionality
while reducing file size through intelligent data management.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any


def extract_all_data(html_content: str) -> Dict[str, Any]:
    """Extract ALL data constants from the HTML."""

    # Find analysisData - the main large dataset
    analysis_match = re.search(
        r"const analysisData = ({.*?});(?=\s*(?:const|//|</script>|$))",
        html_content,
        re.DOTALL | re.MULTILINE,
    )

    if not analysis_match:
        raise ValueError("Could not find analysisData in HTML")

    analysis_data = json.loads(analysis_match.group(1))

    # Also extract other important data constants
    extracted_data = {"analysisData": analysis_data}

    # Find citation similarity data
    similarity_match = re.search(
        r"const citationSimilarities_(\w+) = (\[.*?\]);", html_content, re.DOTALL
    )
    if similarity_match:
        extracted_data["citationSimilarities"] = {
            "id": similarity_match.group(1),
            "data": json.loads(similarity_match.group(2)),
        }

    # Find UMAP coordinates
    umap_match = re.search(
        r"const citationUMAPCoords = ({.*?});", html_content, re.DOTALL
    )
    if umap_match:
        extracted_data["citationUMAPCoords"] = json.loads(umap_match.group(1))

    return extracted_data


def create_optimized_dashboard_v2(
    original_path: Path, output_path: Path, data_dir: Path
) -> None:
    """Create an optimized dashboard that properly loads data."""

    with open(original_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Extract all data
    print("📊 Extracting all embedded data...")
    all_data = extract_all_data(html_content)

    # Save complete data to external file
    data_file = data_dir / "complete_analysis_data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, separators=(",", ":"))

    data_size_mb = data_file.stat().st_size / (1024 * 1024)
    print(f"   ✓ Saved complete data: {data_size_mb:.1f} MB")

    # Create minimal inline data for immediate rendering
    minimal_data = {
        "network_analysis": {
            "author_influence": [],
            "bridge_papers": [],
            "dataset_co_citations": [],
            "multi_dataset_citations": [],
            "dataset_popularity": [],
            "citation_impact_rankings": [],
            "temporal_network_evolution": [],
        },
        "theme_analysis": {
            "comprehensive_theme_analysis": [],
            "research_bridge_analysis_20250731_161858": [],
        },
        "temporal_analysis": all_data["analysisData"].get("temporal_analysis", {}),
        "citation_similarities": [],
    }

    # Replace the large data constant with minimal data + lazy loading
    replacement = f"""const analysisData = {json.dumps(minimal_data, separators=(",", ":"))};

// Lazy loading functionality
let fullDataLoaded = false;
let fullDataLoading = false;
let fullDataPromise = null;

async function loadFullData() {{
    if (fullDataLoaded) return;
    if (fullDataLoading) return fullDataPromise;
    
    fullDataLoading = true;
    fullDataPromise = fetch('data/complete_analysis_data.json')
        .then(response => {{
            if (!response.ok) throw new Error('Failed to load data');
            return response.json();
        }})
        .then(data => {{
            // Merge loaded data into analysisData
            Object.assign(analysisData, data.analysisData);
            
            // Set other global variables if they exist
            if (data.citationSimilarities) {{
                window['citationSimilarities_' + data.citationSimilarities.id] = data.citationSimilarities.data;
            }}
            if (data.citationUMAPCoords) {{
                window.citationUMAPCoords = data.citationUMAPCoords;
            }}
            
            fullDataLoaded = true;
            fullDataLoading = false;
            console.log('✅ Full data loaded successfully');
            
            // Trigger re-initialization of charts if needed
            if (window.refreshVisualizationsAfterDataLoad) {{
                window.refreshVisualizationsAfterDataLoad();
            }}
            
            return data;
        }})
        .catch(error => {{
            console.error('Error loading full data:', error);
            fullDataLoading = false;
            // Dashboard will continue with minimal data
        }});
    
    return fullDataPromise;
}}

// Auto-load data when page is ready
document.addEventListener('DOMContentLoaded', function() {{
    setTimeout(() => {{
        loadFullData().then(() => {{
            // Re-initialize any components that need full data
            if (typeof initializeCharts === 'function') {{
                // Refresh network visualizations with full data
                const networkTab = document.querySelector('[role="tab"][aria-controls="network"]');
                if (networkTab && networkTab.classList.contains('active')) {{
                    // If network tab is active, refresh it
                    document.querySelector('#datasetNetworkChart').innerHTML = '';
                    document.querySelector('#citationNetworkChart').innerHTML = '';
                    createNetworkVisualization();
                }}
            }}
        }});
    }}, 100); // Small delay to let initial render complete
}});

// Override tab switching to ensure data is loaded
const originalTabHandler = window.handleTabSwitch;
window.handleTabSwitch = function(tabName) {{
    if (tabName === 'network' || tabName === 'themes') {{
        loadFullData().then(() => {{
            if (originalTabHandler) originalTabHandler(tabName);
        }});
    }} else {{
        if (originalTabHandler) originalTabHandler(tabName);
    }}
}};"""

    # Replace the analysisData declaration
    html_content = re.sub(
        r"const analysisData = {.*?};(?=\s*(?:const|//|</script>|$))",
        replacement,
        html_content,
        flags=re.DOTALL | re.MULTILINE,
    )

    # Add loading indicators CSS
    loading_css = """
    <style>
    /* Loading states */
    .data-loading {
        position: relative;
        min-height: 400px;
    }
    
    .data-loading::after {
        content: "Loading data...";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.2rem;
        color: #666;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    
    /* Optimize large data rendering */
    .tab-pane:not(.active) {
        display: none !important;
    }
    </style>
    """

    html_content = html_content.replace("</head>", f"{loading_css}\n</head>")

    # Save optimized HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    html_size_kb = len(html_content) / 1024
    print(f"✅ Created optimized dashboard: {output_path}")
    print(f"   HTML size: {html_size_kb:.1f} KB")
    print("   Data loads async from: data/complete_analysis_data.json")


def main():
    """Main optimization process."""

    print("🚀 Creating Properly Optimized Dashboard")
    print("=" * 50)

    # Paths
    original_dashboard = Path("interactive_reports/dataset_citations_dashboard.html")
    optimized_dashboard = Path("interactive_reports/dashboard_optimized_v2.html")
    data_dir = Path("interactive_reports/data")

    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)

    # Create optimized dashboard
    create_optimized_dashboard_v2(original_dashboard, optimized_dashboard, data_dir)

    print("\n✅ Optimization Complete!")
    print("\n📦 Testing Instructions:")
    print(
        "   1. Start local server: cd interactive_reports && python3 -m http.server 8000"
    )
    print("   2. Open: http://localhost:8000/dashboard_optimized_v2.html")
    print("   3. Data loads automatically in background")
    print("   4. All features work: networks, modals, themes")
    print("\n⚡ Benefits:")
    print("   - Initial page loads instantly")
    print("   - Data loads async in background")
    print("   - All visualizations work after data loads")
    print("   - Graceful fallback if data fails to load")


if __name__ == "__main__":
    main()
