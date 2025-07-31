# Temporal Analysis Results

This directory contains timeline analysis of BIDS dataset citations showing how citation patterns evolve over time.

## Contents

### Visualizations
- **`citation_growth_timeline.png`**: Citation growth timeline across all datasets

### Data Files (if generated)
- Timeline data and statistics (CSV/JSON format when exported)

## Analysis Overview

### Citation Growth Timeline
**Purpose**: Visualize how BIDS dataset citations have grown since the early 2000s
- **X-axis**: Publication years
- **Y-axis**: Cumulative citations and new citations per year
- **Scope**: All 302 datasets with 1,004+ high-confidence citations
- **Time range**: Early 2000s to 2025

### Key Insights
- Growth patterns in BIDS dataset adoption
- Peak citation years and their drivers
- Acceleration periods correlating with BIDS specification releases
- Impact of major datasets on citation growth

## How to Reproduce

### Prerequisites
```bash
# Ensure Neo4j contains temporal data
dataset-citations-load-graph

# Activate environment
conda activate dataset-citations
```

### Generate Temporal Analysis
```bash
# Run temporal analysis
dataset-citations-analyze-temporal

# Results saved to results/temporal_analysis/
```

### Alternative Generation
```bash
# Using the CLI module directly
python -m dataset_citations.cli.analyze_temporal --output-dir results/temporal_analysis/
```

## Analysis Parameters

### Confidence Filtering
- Only citations with confidence scores ≥ 0.4 included
- Ensures high-quality temporal trends
- Reduces noise from incorrectly matched citations

### Temporal Granularity
- **Primary analysis**: Annual aggregation
- **Available options**: Monthly, quarterly analysis for detailed periods
- **Cumulative tracking**: Running totals and growth rates

### Data Sources
- Citation years extracted from `citation_details.year` field
- Publication dates validated against external sources when available
- Dataset creation dates from BIDS repository metadata

## Methodology

### Year Extraction
1. Parse citation publication years from JSON files
2. Validate and clean temporal data (remove outliers, fix formatting)
3. Aggregate by dataset and globally
4. Calculate growth metrics and trends

### Visualization Generation
1. **Matplotlib/Seaborn**: Publication-quality static plots
2. **Multiple views**: 
   - Overall citation timeline
   - Individual dataset trajectories
   - Comparative growth rates
   - Seasonal/periodic patterns

### Statistical Analysis
- Growth rate calculations (year-over-year percentage change)
- Trend analysis (linear, exponential, polynomial fits)
- Correlation with external events (BIDS releases, conferences)
- Outlier detection and investigation

## Key Metrics

### Citation Timeline Metrics
- **Total citations by year**: Annual citation counts
- **Cumulative citations**: Running total over time
- **Growth rate**: Year-over-year percentage change
- **Acceleration**: Second derivative of growth
- **Peak periods**: Years with highest citation activity

### Dataset-Specific Metrics
- **First citation date**: When dataset first appeared in literature
- **Citation velocity**: Rate of citation accumulation
- **Popularity phases**: Growth, maturity, decline patterns
- **Impact persistence**: Long-term citation sustainability

## Interpretations

### Growth Phases
1. **Early adoption** (pre-2015): Slow initial growth
2. **BIDS standardization** (2015-2018): Accelerated adoption
3. **Mainstream adoption** (2018+): Sustained high-volume citations
4. **Current trends** (2023-2025): Platform maturity patterns

### Research Impact
- Correlation between dataset availability and research output
- Impact of standardization on reproducible research
- Geographic and institutional adoption patterns
- Methodological vs. applied research citation patterns

## Integration with Other Analyses

### Network Analysis Connection
- Temporal patterns inform network evolution analysis
- Citation timing affects co-citation relationship strength
- Author collaboration patterns change over time

### Impact Analysis Connection
- Temporal data drives impact calculations
- Historical context for current influence metrics
- Trend extrapolation for future impact prediction

## Future Enhancements

### Advanced Temporal Analysis
- Seasonal citation patterns (conference cycles, academic calendars)
- Geographic diffusion patterns over time
- Research domain evolution tracking
- Predictive modeling for future citation trends

### Interactive Temporal Visualization
- Time-slider interactive plots
- Dataset-specific timeline exploration
- Comparative temporal analysis tools
- Animation of network evolution over time

## Data Quality Notes

### Temporal Data Reliability
- Publication years manually validated for major citations
- Outlier detection removes obvious data entry errors
- Missing dates handled through multiple imputation strategies
- Cross-validation with external bibliographic databases when possible

### Known Limitations
- Some early papers may have incomplete date information
- Preprint vs. publication date ambiguity in recent years
- Dataset creation dates may not reflect actual usage start
- Citation reporting delays affect most recent year data