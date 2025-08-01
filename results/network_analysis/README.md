# Network Analysis Results

This directory contains comprehensive network analysis results exploring relationships between datasets, citations, and authors in the BIDS dataset ecosystem.

## Contents

### CSV Exports (`csv_exports/`)
- **`multi_dataset_citations.csv`** (82 papers): Papers that cite multiple BIDS datasets
- **`dataset_co_citations.csv`** (601 relationships): Which datasets are commonly cited together
- **`author_influence.csv`** (87 authors): Most influential authors by citation impact
- **`bridge_papers.csv`** (82 papers): Papers connecting different research areas
- **`citation_impact_rankings.csv`** (7 top citations): Highest-impact citations
- **`dataset_popularity.csv`** (313 datasets): Dataset rankings by citations and impact
- **`temporal_network_evolution.csv`** (14 time periods): How networks change over time

### Summary Reports (`summary_reports/`)
- **`neo4j_network_analysis_summary.json`**: Complete analysis summary with statistics

### Visualizations (`visualizations/`)
- Currently empty - future location for static network plots

## Key Findings

### Multi-Dataset Citation Analysis
- **82 papers** cite multiple BIDS datasets simultaneously
- Shows cross-dataset research patterns and methodological studies
- Identifies papers that validate methods across multiple datasets

### Dataset Co-Citation Network
- **601 co-citation relationships** between datasets
- Reveals which datasets are commonly used together in research
- Shows research domain clustering (e.g., visual cortex studies, language processing)

### Author Influence Network
- **87 influential authors** identified by citation impact
- Measures influence through cumulative citations to their papers
- Identifies key researchers bridging dataset creation and usage

### Bridge Papers
- **82 papers** identified as research area connectors
- Papers that cite datasets from different research domains
- Critical for understanding interdisciplinary research patterns

## How to Reproduce

### Prerequisites
```bash
# Ensure Neo4j is running with data loaded
dataset-citations-load-graph

# Activate environment
conda activate dataset-citations
```

### Generate Network Analysis
```bash
# Run complete network analysis
dataset-citations-analyze-networks

# Results will be saved to:
# - results/network_analysis/csv_exports/
# - results/network_analysis/summary_reports/
```

### Query Neo4j Directly
```cypher
// Example: Find papers citing multiple datasets
MATCH (p:Paper)-[:CITES]->(d:Dataset)
WITH p, COUNT(d) as dataset_count
WHERE dataset_count > 1
RETURN p.title, dataset_count
ORDER BY dataset_count DESC
```

## Analysis Details

### Confidence Filtering
- Only citations with confidence scores ≥ 0.4 are included
- Ensures high-quality citation-dataset relationships
- Reduces noise from false positive matches

### Temporal Scope
- Analysis covers citations from early 2000s to 2025
- Temporal evolution tracks network changes over time
- Useful for understanding research trend evolution

### Statistical Significance
- Co-citation strength measured by frequency of joint citations
- Author influence calculated using citation impact scores
- Bridge detection uses graph centrality measures

## Data Schema

### CSV Column Descriptions

**multi_dataset_citations.csv**:
- `paper_title`: Title of the paper
- `datasets_cited`: Number of datasets cited
- `dataset_list`: Comma-separated list of dataset IDs
- `total_citations`: Total citations received by the paper

**dataset_co_citations.csv**:
- `dataset1`, `dataset2`: Dataset pair
- `co_citation_count`: Number of papers citing both datasets
- `dataset1_total_citations`, `dataset2_total_citations`: Individual citation counts

**author_influence.csv**:
- `author_name`: Author name
- `total_influence`: Cumulative citation impact
- `papers_count`: Number of papers by this author
- `avg_influence_per_paper`: Average influence per paper

## Integration with Other Results
- Links to `../network_visualizations/` for interactive network diagrams
- Connects to `../temporal_analysis/` for timeline context
- Relates to `../impact_analysis/` for citation influence metrics