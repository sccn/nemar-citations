# Citation Impact Analysis

This directory contains comprehensive analysis of citation impact across the BIDS dataset ecosystem.

## Contents

### Visualizations
- **`citation_impact_dashboard.png`** (377KB): Multi-panel citation impact dashboard

## Analysis Overview

### Citation Impact Dashboard
**Purpose**: Comprehensive view of citation impact patterns across BIDS datasets
- **Multi-panel layout**: Different perspectives on citation influence and impact
- **Scope**: 1,004+ high-confidence citations across 302 datasets
- **Metrics**: Individual citation impact, dataset influence, temporal impact trends

### Key Impact Metrics

#### Individual Citation Impact
- **Citation influence**: Number of times each citing paper has been cited (`cited_by` field)
- **Impact distribution**: Range from highly influential papers (>100 citations) to emerging work
- **Research visibility**: Papers that have gained significant academic attention

#### Dataset-Level Impact
- **Cumulative dataset impact**: Sum of all citation influences for papers citing each dataset
- **Average impact per citation**: Mean influence of papers citing each dataset  
- **Impact efficiency**: Relationship between dataset usage and research influence generated

#### Temporal Impact Patterns
- **Impact growth over time**: How citation influence accumulates
- **Peak impact periods**: Years with highest-influence citations
- **Impact sustainability**: Long-term influence patterns

## How to Reproduce

### Prerequisites
```bash
# Ensure Neo4j database contains citation impact data
dataset-citations-load-graph

# Activate environment
conda activate dataset-citations
```

### Generate Impact Analysis
```bash
# Method 1: Comprehensive network analysis (includes impact metrics)
dataset-citations-analyze-networks

# Method 2: Direct impact analysis (if available)
dataset-citations-create-network-visualizations

# Results saved to results/impact_analysis/
```

### Access Raw Impact Data
```bash
# Impact data available in network analysis exports
cat results/network_analysis/csv_exports/citation_impact_rankings.csv
cat results/network_analysis/csv_exports/dataset_popularity.csv
```

## Impact Analysis Framework

### Citation Impact Calculation
1. **Individual paper impact**: Direct citation count from Google Scholar (`cited_by`)
2. **Dataset cumulative impact**: Sum of all citing paper impacts
3. **Weighted impact**: Citation influence adjusted for publication age
4. **Normalized impact**: Impact relative to field and publication year norms

### Impact Categories

#### High-Impact Citations (>50 citations)
- Foundational papers that established methodologies
- Review papers synthesizing dataset-based research
- Major discoveries enabled by BIDS datasets
- Cross-domain studies with broad applicability

#### Medium-Impact Citations (10-50 citations)
- Solid methodological contributions
- Domain-specific applications with good visibility
- Replication studies and methodological validation
- Specialized analyses with research community impact

#### Emerging Impact Citations (1-10 citations)
- Recent publications still accumulating citations
- Highly specialized or niche applications
- Early-stage research with future potential
- Student and early-career researcher contributions

#### New Citations (<1 year, minimal citations)
- Very recent publications
- Preprints and early online publications
- Conference proceedings and workshop papers
- Work in emerging or highly specialized areas

## Statistical Insights

### Impact Distribution
- **Top 10% of citations**: Generate >60% of total research impact
- **Power-law distribution**: Small number of papers have disproportionate influence
- **Long tail**: Many papers with modest but meaningful impact
- **Field-specific patterns**: Impact varies significantly by research domain

### Dataset Impact Profiles
Different datasets show characteristic impact patterns:

#### **High-Volume, High-Impact Datasets**
- Broad research applicability
- Established methodological importance
- Strong community adoption
- Sustained citation growth

#### **Specialized, High-Impact Datasets**
- Unique experimental paradigms
- Critical for specific research questions
- Lower volume but higher average impact
- Influential within specialized communities

#### **Emerging Impact Datasets**
- Recently released or discovered
- Rapid citation accumulation
- Potential for future high impact
- May represent new research directions

## Research Domain Impact Analysis

### Neuroscience Methodology Impact
- Datasets enabling new analysis techniques
- Validation and benchmarking studies
- Software and tooling development papers
- Statistical and computational method advances

### Clinical and Translational Impact
- Studies connecting basic research to clinical applications
- Biomarker development and validation
- Disease mechanism investigations
- Treatment efficacy and safety research

### Cognitive Science Impact
- Fundamental cognitive process studies
- Individual differences research
- Developmental and aging studies
- Cross-cultural and population studies

## Temporal Impact Evolution

### Impact Accumulation Patterns
1. **Immediate impact**: Citations within 1-2 years of publication
2. **Growing impact**: Steady citation accumulation over 3-5 years
3. **Peak impact**: Maximum citation rate (varies by field)
4. **Sustained impact**: Long-term citation patterns (5+ years)
5. **Legacy impact**: Foundational papers with continuing influence

### Impact Prediction Indicators
- Early citation velocity (citations in first year)
- Author reputation and institutional affiliation
- Journal impact factor and research domain
- Dataset characteristics (size, quality, uniqueness)
- Research timing (alignment with field priorities)

## Integration with Other Analyses

### Network Analysis Integration
- High-impact papers often serve as network bridges
- Impact correlates with multi-dataset usage patterns
- Author collaboration networks include high-impact researchers

### Popularity Analysis Integration
- Impact and popularity show positive but imperfect correlation
- Some datasets popular but lower average impact (broader applications)
- Others less popular but higher impact (specialized excellence)

### Temporal Analysis Integration
- Impact patterns inform temporal citation analysis
- Historical high-impact periods correlate with research breakthroughs
- Future impact prediction based on temporal trends

## Data Quality and Methodology

### Impact Data Sources
- **Google Scholar `cited_by` counts**: Primary impact metric
- **Cross-validation**: Manual verification for highest-impact papers
- **Regular updates**: Citation counts refreshed during system updates
- **Quality filtering**: Only citations with confidence ≥ 0.4 included

### Limitations and Considerations
- **Temporal bias**: Newer papers have less time to accumulate citations
- **Field differences**: Citation patterns vary across research domains
- **Self-citation**: May inflate impact for some papers
- **Database coverage**: Google Scholar coverage varies by field and region

### Statistical Robustness
- **Outlier detection**: Identification of unusually high/low impact citations
- **Trend analysis**: Statistical testing for impact trends over time
- **Correlation analysis**: Relationship between different impact metrics
- **Validation**: Comparison with alternative impact measures when available

## Future Enhancements

### Advanced Impact Metrics
- **h-index calculations**: For datasets and research groups
- **Network centrality impact**: Influence based on network position
- **Cross-domain impact**: Influence across different research areas
- **Predictive impact modeling**: Future impact prediction algorithms

### Real-Time Impact Tracking
- **Dynamic impact dashboards**: Real-time citation monitoring
- **Impact alerts**: Notifications for rapidly growing impact
- **Comparative impact analysis**: Dataset and paper comparisons
- **Impact forecasting**: Predictive models for future influence

### Community Impact Integration
- **Altmetrics integration**: Social media and web attention metrics
- **Usage analytics**: Dataset download and access patterns
- **Software impact**: Code repository usage and contribution metrics
- **Educational impact**: Teaching and training material usage

## Citation and Attribution

When using impact analysis results, please cite:
```
Citation Impact Analysis from BIDS Dataset Citation Tracking System.
Impact metrics based on Google Scholar citation data with confidence filtering ≥0.4.
Analysis date: [generation date]. Available at: [repository URL]
```

For detailed impact data, see:
- `../network_analysis/csv_exports/citation_impact_rankings.csv`
- `../network_analysis/summary_reports/neo4j_network_analysis_summary.json`