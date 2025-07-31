# Network Visualizations

This directory contains interactive network visualizations generated from the BIDS dataset citation analysis.

## Contents

### Interactive HTML Networks
- **`author_dataset_network.html`** (4.5MB): Interactive author-dataset collaboration network
- **`dataset_co_citation_network.html`** (4.5MB): Interactive dataset co-citation relationships

### Static Network Images  
- **`dataset_co_citation_network.png`** (4.3MB): High-resolution co-citation network diagram

## Visualization Details

### Author-Dataset Network (`author_dataset_network.html`)
**Purpose**: Shows relationships between dataset creators and citation authors
- **Nodes**: 
  - Blue circles = BIDS datasets
  - Red circles = Authors (both dataset creators and citation authors)
- **Edges**: Relationships between authors and datasets they created or cited
- **Interactive features**:
  - Hover for node details
  - Zoom and pan
  - Physics simulation for automatic layout
  - Search functionality

### Dataset Co-Citation Network (`dataset_co_citation_network.html`)
**Purpose**: Visualizes which datasets are commonly cited together
- **Nodes**: BIDS datasets (size proportional to citation count)
- **Edges**: Co-citation relationships (thickness = co-citation frequency)
- **Layout**: Force-directed to cluster related datasets
- **Interactive features**:
  - Click nodes to highlight connections
  - Filter by co-citation strength
  - Community detection coloring

### Static Co-Citation Network (`dataset_co_citation_network.png`)
**Purpose**: Publication-ready static version of the co-citation network
- High-resolution PNG suitable for papers and presentations
- Color-coded by research domain clusters
- Professional layout with clear labels

## How to Reproduce

### Prerequisites
```bash
# Ensure Neo4j is running with loaded data
dataset-citations-load-graph

# Activate environment  
conda activate dataset-citations
```

### Generate Network Visualizations
```bash
# Create all network visualizations
dataset-citations-create-network-visualizations

# Results saved to results/network_visualizations/
```

### View Interactive Networks
1. **Local viewing**: Open HTML files directly in web browser
2. **Sharing**: HTML files are self-contained and can be shared/hosted
3. **Customization**: Edit HTML files to modify colors, layouts, or interactions

## Technical Implementation

### Libraries Used
- **NetworkX**: Graph data structures and algorithms
- **Pyvis**: Interactive HTML network generation
- **Matplotlib**: Static PNG generation
- **Neo4j Python Driver**: Database connectivity

### Data Sources
- Dataset metadata from `citations/json/` directory
- Citation relationships from Neo4j graph database
- Confidence scores ≥ 0.4 for filtering high-quality relationships

### Network Algorithms
- **Force-directed layout**: Automatic positioning based on connections
- **Community detection**: Clustering related datasets/authors
- **Centrality measures**: Identifying key nodes in the network
- **Edge bundling**: Reducing visual clutter in dense networks

## Customization

### Modifying Visualizations
1. **Colors**: Edit HTML files or modify source code color schemes
2. **Layout**: Adjust physics parameters in HTML or regenerate with different algorithms
3. **Filtering**: Modify confidence thresholds or citation count minimums
4. **Styling**: CSS modifications for node/edge appearance

### Adding New Networks
The visualization system can be extended to create:
- Author collaboration networks
- Temporal network evolution animations
- Research topic clustering networks
- Citation impact networks

## Performance Notes

### File Sizes
- HTML files are large (4.5MB) due to embedded network data
- Consider web hosting for sharing rather than email attachment
- PNG files provide smaller alternative for static viewing

### Browser Compatibility
- Modern browsers recommended (Chrome, Firefox, Safari, Edge)
- JavaScript required for interactive features
- Mobile devices may have performance limitations with large networks

## Integration

### Related Analysis
- Raw network data available in `../network_analysis/csv_exports/`
- Statistical summaries in `../network_analysis/summary_reports/`
- Temporal context in `../temporal_analysis/`

### Export Options
- HTML networks can be embedded in web pages
- PNG images ready for publications
- Network data exportable to Gephi, Cytoscape, or other tools