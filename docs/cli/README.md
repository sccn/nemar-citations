# CLI Commands Reference

The dataset citations package provides a comprehensive suite of command-line tools for analysis, visualization, and data management.

## Command Categories

### Data Management Commands
- `dataset-citations-discover` - Discover and catalog BIDS datasets
- `dataset-citations-update` - Update citation data from Google Scholar
- `dataset-citations-retrieve-metadata` - Fetch dataset metadata from GitHub
- `dataset-citations-migrate` - Migrate legacy pickle files to JSON format

### Analysis Commands
- `dataset-citations-score-confidence` - Calculate citation-dataset confidence scores
- `dataset-citations-analyze-networks` - Perform network analysis on citations
- `dataset-citations-analyze-temporal` - Analyze temporal citation patterns
- `dataset-citations-analyze-umap` - Generate UMAP embeddings and clustering

### Visualization Commands
- `dataset-citations-create-interactive-reports` - Generate interactive HTML dashboards
- `dataset-citations-create-network-visualizations` - Create network visualization files
- `dataset-citations-export-external-tools` - Export data for Gephi, Cytoscape, R
- `dataset-citations-create-research-context-networks` - Generate research theme networks

### Database Commands
- `dataset-citations-load-graph` - Load citation data into Neo4j database
- `dataset-citations-generate-embeddings` - Generate and manage embedding storage
- `dataset-citations-manage-embeddings` - Embedding lifecycle management

### Automation Commands
- `dataset-citations-automate-visualization-updates` - Automated update pipelines
- `dataset-citations-automate-updates` - General automation workflows

## Quick Start

```bash
# Activate conda environment
conda activate dataset-citations

# Generate interactive dashboard from existing results
dataset-citations-create-interactive-reports \
  --results-dir results/ \
  --output-dir interactive_reports/ \
  --verbose

# Export network data for external tools
dataset-citations-export-external-tools \
  --input results/network_analysis/ \
  --output-dir exports/ \
  --format all

# Set up automated updates
dataset-citations-automate-visualization-updates \
  --data-dirs citations/ datasets/ embeddings/ \
  --output-dir results/ \
  --schedule daily \
  --schedule-time 02:00
```

## Command Documentation

Each command provides detailed help via the `--help` flag:

```bash
dataset-citations-create-interactive-reports --help
```

For detailed documentation of individual commands, see:
- [Analysis Commands](analysis-commands.md)
- [Visualization Commands](visualization-commands.md) 
- [Data Management Commands](data-management.md)