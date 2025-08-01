# Dataset Citations Graph Visualization

This module provides comprehensive graph visualization and analytics capabilities for BIDS dataset citations, implemented as Phase 4 of the dataset citations project.

## Overview

The graph module enables:
- **Temporal Analysis**: Timeline visualization of citation patterns over time
- **Neo4j Integration**: Loading citation data into Neo4j graph database
- **Interactive Visualization**: Neo4j Bloom perspectives for exploring citation networks
- **Confidence Scoring**: Quality-based filtering and analysis of citations
- **Embedding Support**: Future UMAP clustering and similarity analysis

## Architecture

```
graph/
├── schemas.py           # Pydantic data models for datasets, citations, years
├── temporal.py          # Temporal analysis and timeline functions
├── neo4j_loader.py      # Neo4j database loading and initialization
└── perspectives/        # Neo4j Bloom visualization configurations
    ├── temporal_perspective.json      # Timeline-focused visualization
    └── confidence_perspective.json   # Quality-focused visualization
```

## Quick Start

### 1. Temporal Analysis

Analyze citation timelines and trends:

```bash
# Analyze all citations with default confidence threshold (0.4)
dataset-citations-analyze-temporal citations/json --output-dir temporal_results

# Analyze with custom confidence threshold
dataset-citations-analyze-temporal citations/json --confidence-threshold 0.6

# Analyze specific dataset
dataset-citations-analyze-temporal citations/json --dataset-id ds000117

# Verbose output
dataset-citations-analyze-temporal citations/json --verbose
```

**Output includes:**
- `temporal_analysis.json`: Complete timeline data
- `temporal_summary.csv`: Yearly citation statistics
- Console summary with key insights

### 2. Neo4j Graph Loading

Load citation data into Neo4j for interactive visualization:

```bash
# Prerequisites: Install and start Neo4j
# Set environment variable: export NEO4J_PASSWORD="your-password"

# Load citation graph (basic)
dataset-citations-load-graph citations/json

# Load with dataset metadata enhancement
dataset-citations-load-graph citations/json --datasets-dir datasets/

# Custom Neo4j connection
dataset-citations-load-graph citations/json \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-username neo4j \
  --neo4j-password your-password

# Clear database before loading (WARNING: deletes all data)
dataset-citations-load-graph citations/json --clear-db

# Custom confidence threshold and batch size
dataset-citations-load-graph citations/json \
  --confidence-threshold 0.5 \
  --batch-size 500
```

### 3. Neo4j Bloom Visualization

After loading data into Neo4j:

1. **Open Neo4j Bloom** (part of Neo4j Desktop or Browser)
2. **Import Perspectives**:
   - Go to Perspective settings
   - Import `perspectives/temporal_perspective.json` for timeline analysis
   - Import `perspectives/confidence_perspective.json` for quality analysis
3. **Start Exploring**:
   - Use search templates for common queries
   - Apply scene actions for interactive exploration
   - Filter by confidence scores, years, or data types

## Data Model

### Nodes
- **Dataset**: BIDS datasets with metadata and citation counts
- **Citation**: Research papers citing datasets with confidence scores
- **Year**: Temporal nodes for timeline analysis

### Relationships
- **CITES**: Dataset → Citation (dataset is cited by paper)
- **CITED_IN**: Citation → Year (paper published in year)

### Key Properties
- `confidence_score`: Citation relevance score (0.0-1.0)
- `is_high_confidence`: Boolean flag for citations ≥ 0.4 confidence
- `num_citations`: Direct citation count per dataset
- `total_cumulative_citations`: Sum of all citation impacts

## Visualization Perspectives

### Temporal Perspective
Focus on timeline analysis:
- **Color coding**: By confidence score
- **Size scaling**: By citation count
- **Templates**: Year range queries, timeline analysis
- **Scene Actions**: Show citations by year, dataset timeline

### Confidence Perspective  
Focus on citation quality:
- **Color coding**: Confidence score gradient (red=low, green=high)
- **Size scaling**: By citation impact (`cited_by` count)
- **Filtering**: High vs. low confidence citations
- **Templates**: Quality analysis, confidence distribution

## Configuration

### Environment Variables
```bash
# Neo4j connection (optional, defaults provided)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

### Confidence Thresholds
- **Default**: 0.4 (recommended based on Phase 3 analysis)
- **High Quality**: 0.6+ for stricter filtering
- **Research**: 0.8+ for highest confidence only

## Advanced Usage

### Custom Temporal Analysis
```python
from dataset_citations.graph.temporal import analyze_citation_timeline

# Programmatic analysis
timeline_data = analyze_citation_timeline(
    citations_dir=Path("citations/json"),
    confidence_threshold=0.5
)

# Access specific dataset stats
dataset_stats = timeline_data['datasets']['ds000117']
print(f"First citation: {dataset_stats['first_year']}")
print(f"Total citations: {dataset_stats['total_citations']}")
```

### Custom Neo4j Queries
```cypher
-- Find datasets with most citations in recent years
MATCH (d:Dataset)-[:CITES]->(c:Citation)-[:CITED_IN]->(y:Year)
WHERE y.value >= 2020
RETURN d.name, COUNT(c) as recent_citations
ORDER BY recent_citations DESC
LIMIT 10;

-- Analyze confidence score distribution
MATCH (c:Citation)
RETURN 
  CASE 
    WHEN c.confidence_score >= 0.8 THEN 'High'
    WHEN c.confidence_score >= 0.6 THEN 'Medium'
    WHEN c.confidence_score >= 0.4 THEN 'Low'
    ELSE 'Very Low'
  END as confidence_level,
  COUNT(c) as count
ORDER BY confidence_level;
```

## Future Development

Phase 4 continues with:
- **UMAP Clustering**: Thematic analysis of citations and datasets
- **Embedding Integration**: Semantic similarity visualization
- **Advanced Perspectives**: Research collaboration networks
- **Real-time Updates**: Dynamic graph updates with new citations

## Troubleshooting

### Common Issues

**Neo4j Connection Failed**
```bash
# Check Neo4j is running
sudo systemctl status neo4j  # Linux
# or check Neo4j Desktop

# Test connection
echo "RETURN 1" | cypher-shell -u neo4j -p your-password
```

**No Citation Data Found**
```bash
# Verify citations directory structure
ls citations/json/*.json | head -5

# Check JSON file format
jq '.citation_details[0]' citations/json/ds000117_citations.json
```

**Low Confidence Citations**
- Review confidence threshold (default 0.4)
- Check Phase 3 confidence scoring implementation
- Manually validate some low-confidence citations

### Performance Optimization

**Large Datasets**
- Increase `--batch-size` for faster loading
- Use confidence filtering to reduce data volume
- Consider temporal subsets for initial analysis

**Neo4j Memory**
- Adjust Neo4j heap size in neo4j.conf
- Create indexes on frequently queried properties
- Use LIMIT clauses in large queries

---

For more information, see the main project documentation and Phase 4 implementation notes in `scratch_notes.md`.