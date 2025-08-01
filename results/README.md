# Dataset Citations Analysis Results

This directory contains comprehensive analysis results from the BIDS dataset citation tracking system. All results are generated from 302 datasets with 1,004+ high-confidence citations (confidence score ≥ 0.4).

## Directory Structure

```
results/
├── network_analysis/           # Network analysis exports and summaries
│   ├── csv_exports/           # Raw data exports for further analysis
│   ├── summary_reports/       # JSON summary reports
│   └── visualizations/        # Future location for static plots
├── network_visualizations/     # Interactive network diagrams
├── temporal_analysis/         # Citation timeline analysis
├── dataset_popularity/        # Dataset ranking and popularity metrics
├── impact_analysis/           # Citation impact dashboards
└── author_networks/           # Author collaboration networks
```

## How to Reproduce Results

### Prerequisites
1. **Neo4j Database**: Ensure Neo4j is running with the citation graph loaded
   ```bash
   # Load data into Neo4j (if not already done)
   dataset-citations-load-graph
   ```

2. **Environment**: Use the `dataset-citations` conda environment
   ```bash
   conda activate dataset-citations
   ```

### Generate All Analysis Results
```bash
# Run comprehensive network analysis (generates most results)
dataset-citations-analyze-networks

# Run temporal analysis
dataset-citations-analyze-temporal

# Create custom visualizations (for specific analysis types)
dataset-citations-create-network-visualizations
```

### Individual Analysis Commands
Each analysis type can be run separately - see the README files in each subdirectory for specific reproduction steps.

## Data Quality Notes
- **Confidence filtering**: Only citations with confidence scores ≥ 0.4 are included
- **Dataset scope**: 302 BIDS datasets with complete metadata
- **Citation scope**: 1,004+ verified citations with full bibliographic data
- **Temporal range**: Citations from early 2000s to 2025
- **Update frequency**: Results reflect data as of the last citation update run

## Analysis Overview

| Analysis Type | Description | Key Outputs |
|---------------|-------------|-------------|
| **Network Analysis** | Multi-dataset citations, co-citations, collaborations | CSV exports, network diagrams |
| **Temporal Analysis** | Citation growth over time, dataset timeline | Timeline plots, growth statistics |
| **Impact Analysis** | Citation influence, dataset popularity rankings | Impact dashboards, ranking tables |
| **Author Networks** | Dataset creator ↔ citation author relationships | Collaboration networks |
| **Bridge Analysis** | Papers connecting different research areas | Bridge paper identification |

## Citation Format
When using these results in publications, please cite:
```
Dataset Citations Analysis Results. Generated using the BIDS Dataset Citation Tracking System.
Available at: [repository URL]
```

## Reproducibility
All results can be regenerated using the CLI commands above. The underlying data comes from:
- Google Scholar API via `scholarly` library
- BIDS dataset metadata from GitHub repositories  
- Confidence scoring using sentence-transformers (Qwen3-Embedding-0.6B)
- Neo4j graph database for network analysis