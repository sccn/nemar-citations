# Interactive Dashboard Documentation

## Overview

The interactive dashboard system provides self-contained web-based visualization and exploration of dataset citation networks. Built with Bootstrap 5, Plotly.js, and Cytoscape.js, the dashboards offer professional scientific visualization ready for institutional deployment.

## Features

### Self-Contained Web Dashboards
- **Bootstrap 5 Framework**: Responsive design that works on desktop, tablet, and mobile
- **Professional Scientific Theming**: Unified color scheme across all visualizations
- **No Backend Required**: Can be hosted on any web server or file system
- **Cross-Browser Compatible**: Tested in Chrome, Firefox, Safari, Edge

### Interactive Network Visualization
- **Dynamic Network Generation**: Built from actual analysis data (302+ datasets, 601+ relationships)
- **Multiple Node Types**: Datasets (circles), Bridge Papers (diamonds) with size encoding
- **Interactive Elements**: Hover tooltips, click events, connection highlighting
- **Visual Encoding**: Node size based on citation impact, edge thickness based on relationship strength

### Multi-Tab Interface
- **Overview Tab**: Summary statistics and analysis availability
- **Network Analysis Tab**: Interactive network exploration with detailed info panels
- **Temporal Trends Tab**: Citation growth timelines and patterns
- **Research Themes Tab**: UMAP clustering results and word clouds
- **Data Export Tab**: Download links for external analysis tools

## Usage

### Generate Dashboard

```bash
dataset-citations-create-interactive-reports \
  --results-dir results/ \
  --output-dir interactive_reports/ \
  --verbose
```

### Output Files

```
interactive_reports/
├── dataset_citations_dashboard.html   # Main self-contained dashboard
├── *.csv                              # Network analysis data exports
├── *.gexf                             # Gephi format files
├── *.cx                               # Cytoscape format files
├── *.graphml                          # Universal GraphML format
└── README.md                          # Usage instructions
```

### Dashboard Components

#### Network Visualization
- **Dataset Nodes**: Blue circles sized by total citations
- **Bridge Paper Nodes**: Green diamonds sized by number of datasets connected
- **Co-Citation Edges**: Blue lines with thickness indicating shared citations
- **Bridge Connections**: Dashed green lines showing paper-dataset relationships

#### Interactive Features
- **Hover Tooltips**: Show detailed information for nodes and edges
- **Click Selection**: Highlight connected elements and show detailed info panel
- **Zoom and Pan**: Navigate large networks with mouse/touch controls
- **Info Panels**: Display full dataset names, paper titles, authors, confidence scores

#### Export Integration
- **Gephi Export**: GEXF format for large network visualization and community detection
- **Cytoscape Export**: CX format for biological pathway analysis
- **R/Python Export**: CSV and GraphML formats for programmatic analysis

## Deployment

### Web Hosting
The generated dashboard is completely self-contained and can be:

1. **Uploaded to any web server** (no backend required)
2. **Hosted on GitHub Pages** for free public access
3. **Embedded in institutional websites**
4. **Shared via cloud storage** (Dropbox, Google Drive)

### Example Deployment

```bash
# Copy to web directory
cp interactive_reports/dataset_citations_dashboard.html /var/www/html/

# Or upload to GitHub Pages
git add interactive_reports/
git commit -m "Add interactive dashboard"
git push origin gh-pages
```

## Customization

### Color Scheme
The dashboard uses a unified scientific color palette:

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

### Network Layout
- **Algorithm**: Cose (Compound Spring Embedder) for balanced node positioning
- **Edge Length**: 100px ideal distance between connected nodes
- **Node Overlap**: 20px minimum distance between nodes
- **Padding**: 30px border around network area

## Performance Considerations

### Large Datasets
- **Node Limiting**: Dashboard displays first 50 co-citation relationships for performance
- **Bridge Paper Limiting**: Shows first 20 bridge papers to avoid overcrowding
- **Lazy Loading**: Large datasets loaded on demand
- **Image Compression**: Optimized PNG/SVG exports

### Browser Compatibility
- **Modern Browsers**: Requires JavaScript ES6+ support
- **Mobile Support**: Touch events for network navigation
- **Accessibility**: Screen reader compatible with ARIA labels

## Troubleshooting

### Common Issues

1. **Dashboard Not Loading**
   - Check browser JavaScript console for errors
   - Ensure all required data files are present in results directory
   - Verify pandas dependency is installed

2. **Network Visualization Empty**
   - Confirm network analysis data exists in `results/network_analysis/csv_exports/`
   - Check that CSV files contain valid data
   - Review console logs for data loading errors

3. **Export Files Missing**
   - Ensure sufficient disk space for export generation
   - Check write permissions on output directory
   - Verify all analysis results are present

### Debug Mode

```bash
dataset-citations-create-interactive-reports \
  --results-dir results/ \
  --output-dir interactive_reports/ \
  --verbose
```

The verbose flag provides detailed logging of data loading and processing steps.

## Integration with External Tools

See [External Tools Integration](external-tools.md) for detailed guides on using exported data with Gephi, Cytoscape, R, and Python.