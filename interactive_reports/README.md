# NEMAR Dataset Citations Dashboard

## 🎯 **Overview**

This directory contains the **NEMAR Dataset Citations Dashboard** - an interactive web-based visualization of citation patterns, research themes, and network relationships for 302 BIDS datasets hosted on NEMAR.org. The dashboard provides comprehensive analysis with confidence-filtered citations to ensure only relevant neuroscience papers are included.

## ✨ **Key Features**

### **🌐 Interactive HTML Reports**
- **Self-contained web dashboards** that can be hosted anywhere
- **Responsive design** with Bootstrap 5 framework
- **Unified color scheme** across all visualizations
- **Interactive exploration** with Plotly.js and Cytoscape.js
- **Professional theming** suitable for scientific publications

### **🔗 External Tool Integration**
- **Gephi Export**: GEXF format for large network visualization
- **Cytoscape Export**: CX, XGMML, and SIF formats for biological networks
- **Universal Export**: GraphML, CSV for programmatic analysis
- **R/igraph Support**: NCOL, LGL formats for R analysis

### **🔄 Automated Updates**
- **Change detection** for citation and dataset files
- **Scheduled updates** with cron/Task Scheduler integration
- **Pipeline automation** with stage-wise execution
- **Incremental processing** to avoid unnecessary work

## 🚀 **Quick Start**

### **1. Generate NEMAR Dashboard**

```bash
# Activate conda environment
conda activate dataset-citations

# Generate the dashboard
python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('dashboard_data'),
    output_dir=Path('interactive_reports')
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
print(f'Dashboard generated: {output_path}')
"
```

Or without activating the environment:
```bash
~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('dashboard_data'),
    output_dir=Path('interactive_reports')
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
"
```

**Output**: Self-contained HTML dashboard at `interactive_reports/dataset_citations_dashboard_nemar.html`

### **2. Export for External Tools**

```bash
# Export network data for all external tools
dataset-citations-export-external-tools \
  --input results/network_analysis/ \
  --output-dir exports/ \
  --format all
```

**Exports**:
- `network_export.gexf` (Gephi)
- `network_export.cx` (Cytoscape)
- `network_export.graphml` (Universal)
- `network_export_nodes.csv` + `network_export_edges.csv`

### **3. Set Up Automated Updates**

```bash
# Configure daily automated updates
dataset-citations-automate-visualization-updates \
  --data-dirs citations/ datasets/ embeddings/ \
  --output-dir results/ \
  --schedule daily \
  --schedule-time 02:00
```

## 📊 **Dashboard Components**

### **Navigation Tabs**
1. **Overview**: 
   - Summary cards showing 302 datasets analyzed
   - 1000+ high-confidence citations (≥0.4 score)
   - 80 research bridge papers
   - Interactive charts for citation trends and modality distribution

2. **Network Analysis**: 
   - **Dataset Map**: 285 datasets with UMAP semantic positioning
     - Node sizes based on `num_citations` from JSON files (0-78 range)
     - Click nodes to view dataset details with NEMAR.org links
   - **Citation Map**: 500+ high-confidence neuroscience papers
     - Node sizes based on `cited_by` count (0-522 range)
     - Only includes papers with confidence ≥ 0.4
     - Real paper titles displayed on click

3. **Research Themes**: 
   - Word clouds for different research clusters
   - Theme evolution visualizations
   - UMAP-based semantic clustering

### **Visualization Features**
- **Interactive Networks**: Zoom, pan, hover information
- **Dynamic Charts**: Plotly.js charts with export capabilities
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Professional Styling**: Scientific color palette and typography

## 🛠 **Technical Architecture**

### **Frontend Stack**
- **HTML5 + Bootstrap 5**: Responsive framework
- **Plotly.js**: Interactive scientific charts
- **Cytoscape.js**: Web-based network visualization
- **Jinja2**: Server-side templating (optional)

### **Export Formats**

| Tool | Format | Extension | Best For |
|------|--------|-----------|----------|
| **Gephi** | GEXF | `.gexf` | Large networks, community detection |
| **Cytoscape** | CX | `.cx` | Biological pathways, rich metadata |
| **Cytoscape** | SIF | `.sif` | Simple interaction files |
| **Universal** | GraphML | `.graphml` | Programmatic analysis |
| **R/Python** | CSV | `.csv` | Data analysis, spreadsheets |

### **Color Scheme**

```javascript
{
  "primary": "#2E86AB",      // Ocean blue
  "secondary": "#A23B72",    // Deep pink  
  "accent": "#F18F01",       // Orange
  "dataset": "#4A90E2",      // Light blue
  "citation": "#E94B3C",     // Red
  "bridge": "#50C878",       // Emerald green
  "background": "#F8F9FA",   // Light gray
  "text": "#212529"          // Dark gray
}
```

## 📁 **File Structure**

```text
interactive_reports/
├── dataset_citations_dashboard.html    # Main dashboard
└── README.md                          # Usage instructions

exports/
├── dataset_citations_network.gexf     # Gephi format
├── dataset_citations_network.cx       # Cytoscape CX
├── dataset_citations_network.sif      # Cytoscape SIF  
├── dataset_citations_network.graphml  # Universal GraphML
├── network_analysis_nodes.csv         # Node data
├── network_analysis_edges.csv         # Edge data
└── README.md                          # Export guide

results/
├── network_analysis/                  # Network analysis results
├── temporal_analysis/                 # Timeline data
├── theme_analysis/                    # UMAP clustering
├── research_context_networks/         # Context networks
└── README.md                         # Results overview
```

## 🔧 **Advanced Usage**

### **Custom Export Sources**

```bash
# Export from citation JSON files directly
dataset-citations-export-external-tools \
  --input citations/json/ \
  --output-dir exports/ \
  --format gephi

# Export from specific analysis results
dataset-citations-export-external-tools \
  --input results/research_context_networks/ \
  --output-dir cytoscape_exports/ \
  --format cx
```

### **Pipeline Automation**

```bash
# Check pipeline status
dataset-citations-automate-visualization-updates --status

# Force complete update
dataset-citations-automate-visualization-updates \
  --force-update \
  --confidence-threshold 0.5 \
  --verbose

# Run specific stages only
dataset-citations-automate-visualization-updates \
  --stages interactive_reports external_exports \
  --force-update
```

### **Scheduled Updates**

The automation system can set up scheduled updates:

```bash
# Daily updates at 2 AM
dataset-citations-automate-visualization-updates \
  --schedule daily --schedule-time 02:00

# Weekly updates on Sunday at midnight  
dataset-citations-automate-visualization-updates \
  --schedule weekly --schedule-time 00:00
```

This creates a script that can be added to:
- **Linux/Mac**: `crontab -e`
- **Windows**: Task Scheduler

## 🌐 **Web Hosting**

### **Self-Contained Deployment**
The generated dashboard is completely self-contained and can be:

1. **Uploaded to any web server** (no backend required)
2. **Hosted on GitHub Pages** for free public access
3. **Embedded in institutional websites**
4. **Shared via cloud storage** (Dropbox, Google Drive)

### **Example Deployment**

```bash
# Copy dashboard to web directory
cp interactive_reports/dataset_citations_dashboard.html /var/www/html/

# Or upload to GitHub Pages
git add interactive_reports/
git commit -m "Add interactive dashboard"
git push origin gh-pages
```

## 📈 **Integration with External Tools**

### **Gephi Workflow**
1. Export network: `dataset-citations-export-external-tools --format gexf`
2. Open Gephi → File → Open → Select `.gexf` file
3. Apply layout algorithms (Force Atlas 2, etc.)
4. Customize appearance and export high-quality images

### **Cytoscape Workflow**
1. Export network: `dataset-citations-export-external-tools --format cx`
2. Open Cytoscape → File → Import → Network from File
3. Apply biological network styles and layouts
4. Perform advanced pathway analysis

### **R/igraph Analysis**

```r
# Load network data
library(igraph)
nodes <- read.csv("exports/network_export_nodes.csv")
edges <- read.csv("exports/network_export_edges.csv")

# Create igraph object
g <- graph_from_data_frame(edges, vertices=nodes, directed=TRUE)

# Analyze network properties
betweenness(g)
clustering_fast_greedy(g)
```

## 🔍 **Quality Assurance**

### **Automated Testing**
- **Export format validation**: Ensures compatibility with target tools
- **HTML validation**: W3C compliant dashboards
- **Cross-browser testing**: Works in Chrome, Firefox, Safari, Edge
- **Responsive testing**: Mobile and desktop layouts

### **Performance Optimization**
- **Lazy loading**: Large datasets loaded on demand
- **Image compression**: Optimized PNG/SVG exports
- **Minified assets**: Compressed CSS/JS for faster loading
- **Caching strategies**: Efficient data reuse

## 📊 **Example Use Cases**

### **1. Research Publication**
- Generate interactive dashboard for supplementary materials
- Export high-quality network diagrams for figures
- Provide raw data in CSV format for reproducibility

### **2. Institutional Reporting**
- Host dashboard on university website
- Schedule weekly updates for current data
- Export specialized formats for different stakeholders

### **3. Collaborative Research**
- Share self-contained HTML reports with collaborators
- Export to Cytoscape for biological pathway analysis
- Provide Gephi files for network topology studies

## 🚀 **What's Next?**

Phase 4.7 completes the core visualization and reporting capabilities. Potential future enhancements:

- **Real-time updates** with WebSocket integration
- **Advanced filtering** with URL parameters
- **Collaborative annotations** for shared analysis
- **API endpoints** for programmatic access
- **Custom branding** options for institutions

---

## 📞 **Support**

For questions about Phase 4.7:
1. Check the generated `README.md` files in output directories
2. Review the CLI help: `dataset-citations-create-interactive-reports --help`
3. Examine example outputs in the `results/` directory
4. Review the visualization color scheme and theming options

**🎉 Phase 4.7 provides a complete, professional solution for sharing and analyzing dataset citation networks!**