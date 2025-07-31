# Dataset Popularity Analysis

This directory contains analysis of BIDS dataset popularity based on citation counts and impact metrics.

## Contents

### Visualizations
- **`dataset_popularity_rankings.png`** (211KB): Comprehensive dataset popularity rankings visualization

## Analysis Overview

### Dataset Popularity Rankings
**Purpose**: Rank BIDS datasets by multiple popularity and impact metrics
- **Primary metrics**: Number of citations, total cumulative citations, citation growth
- **Visualization**: Multi-panel dashboard showing different ranking perspectives
- **Scope**: All 302 datasets with available citation data

### Key Metrics

#### Citation-Based Popularity
- **Direct citations**: Number of papers directly citing each dataset
- **Cumulative impact**: Total citations received by all papers citing the dataset
- **Citation velocity**: Rate of citation accumulation over time
- **Recent activity**: Citation activity in the last 2 years

#### Research Impact Indicators
- **Cross-dataset influence**: How often a dataset appears in multi-dataset studies
- **Research diversity**: Breadth of research domains using the dataset
- **Methodological importance**: Usage in methodological vs. applied research
- **Community adoption**: Geographic and institutional distribution

## How to Reproduce

### Prerequisites
```bash
# Ensure Neo4j database is loaded with citation data
dataset-citations-load-graph

# Activate environment
conda activate dataset-citations
```

### Generate Dataset Popularity Analysis
```bash
# Method 1: Through network analysis (includes popularity rankings)
dataset-citations-analyze-networks

# Method 2: Direct visualization creation (if available)
dataset-citations-create-network-visualizations

# Results saved to results/dataset_popularity/
```

### Custom Analysis
```python
# Python script to create custom popularity analysis
from dataset_citations.graph.neo4j_network_analysis import Neo4jNetworkAnalyzer

analyzer = Neo4jNetworkAnalyzer()
popularity_data = analyzer.get_dataset_popularity()
# Create custom visualizations with the data
```

## Interpretation Guide

### Understanding the Rankings

#### High-Impact Datasets
- Datasets with >50 direct citations typically represent:
  - Foundational datasets in specific research domains
  - Large-scale, multi-modal datasets suitable for various analyses
  - Datasets with exceptional data quality or unique characteristics
  - Early BIDS datasets that established methodological standards

#### Emerging Datasets
- Recently created datasets with high citation velocity
- May indicate growing research areas or novel methodologies
- Important for tracking trends in neuroscience research priorities

#### Specialized Datasets
- Lower citation counts but high research diversity
- Often represent specialized populations or unique experimental paradigms
- Critical for niche research areas and methodological development

### Ranking Categories

#### Citation Volume Rankings
1. **Total citations**: Absolute number of citing papers
2. **Cumulative impact**: Sum of all citation impacts
3. **Average impact**: Mean citations per citing paper

#### Growth and Velocity Rankings
1. **Citation growth rate**: Year-over-year percentage increase
2. **Recent activity**: Citations in the last 24 months
3. **Acceleration**: Change in growth rate over time

## Statistical Context

### Dataset Distribution
- **Top 10%**: >20 citations (represents core datasets)
- **Active datasets**: 5-20 citations (mainstream usage)
- **Emerging datasets**: 1-5 citations (new or specialized)
- **Specialized datasets**: <1 citation (niche applications)

### Research Domain Analysis
Popular datasets cluster in key research areas:
- **Visual neuroscience**: Face processing, visual perception studies
- **Language and cognition**: Reading, language processing paradigms
- **Motor and sensorimotor**: Movement, tactile, and coordination studies
- **Clinical populations**: Neurological and psychiatric conditions
- **Methodological validation**: Quality assessment and technique comparison

## Integration with Other Analyses

### Network Analysis Connection
- Popular datasets often serve as network hubs in co-citation analysis
- High-impact datasets frequently appear in multi-dataset studies
- Popularity correlates with bridge paper identification

### Temporal Analysis Connection
- Dataset popularity often shows characteristic growth curves
- Historical popularity data reveals research trend evolution
- Temporal analysis helps distinguish sustained vs. temporary popularity

### Author Network Connection
- Popular datasets often have influential authors
- Creator reputation and dataset popularity show positive correlation
- Community adoption patterns reflect author network effects

## Data Quality and Limitations

### Confidence Filtering
- Only citations with confidence ≥ 0.4 included in popularity calculations
- Reduces inflation from false positive citation matches
- May undercount datasets with generic or common names

### Temporal Bias
- Newer datasets have less opportunity to accumulate citations
- Analysis adjusts for dataset age when possible
- Recent citations may be underrepresented due to reporting delays

### Research Domain Bias
- Some research areas publish more frequently than others
- Dataset popularity may reflect publication patterns rather than usage
- Cross-domain comparisons should consider field-specific norms

## Future Enhancements

### Dynamic Popularity Tracking
- Real-time popularity updates with new citation data
- Predictive modeling for future popularity trends
- Alert systems for rapidly growing datasets

### Advanced Metrics
- Usage diversity indices (research domain breadth)
- International adoption tracking
- Institutional distribution analysis
- Methodological impact assessment

### Interactive Exploration
- Web-based popularity dashboard
- Dataset comparison tools
- Trend analysis and prediction interfaces
- Community feedback integration

## Citation and Usage

When referencing this analysis, please cite:
```
BIDS Dataset Popularity Analysis. Generated using the Dataset Citation Tracking System.
Confidence threshold: ≥0.4, Analysis date: [generation date]
Available at: [repository URL]
```

For questions about specific dataset rankings or methodology, consult the detailed analysis in `../network_analysis/csv_exports/dataset_popularity.csv`.