# Cleanup Plan for Issue #23

## Objective
Consolidate all analysis outputs to `dashboard_data/` and remove obsolete components.

## Directories to Remove

### Test Output Directories
- `test_output/` - Old test output
- `test_output_*/` - Multiple test output directories
- `test_modular_output/` - Test modular output
- `test_output_nemar/` - Test NEMAR output
- `.playwright-mcp/` - Screenshot directory (move needed files first)

### Obsolete Analysis Directories
- `results/` - Old results directory (check for needed files first)
- `embeddings/analysis/` - Duplicate analysis in embeddings
- `interactive_reports/data/` - Should be generated from dashboard_data
- `data/` - Old data directory

## Files to Remove
- `dashboard_data/aggregated_data_old.json` - Old aggregated data
- `interactive_reports/*.png` - Unused network images
- `interactive_reports/*.graphml` - Unused graph files
- `interactive_reports/*.gexf` - Unused graph files
- `interactive_reports/*.cx` - Unused graph files

## Consolidation Plan

### Target Structure
```
dashboard_data/
├── aggregated_data.json     # Main aggregated data
├── network/                 # Network analysis results
│   ├── *.csv                # CSV exports
│   └── *.json               # JSON summaries
├── themes/                  # Theme analysis
│   ├── comprehensive_theme_analysis.json
│   └── theme_*_wordcloud.png
├── temporal/                # Temporal analysis
│   └── *.csv
└── visualizations/          # All generated visualizations
    └── *.png
```

### Dashboard Dependencies
The dashboard needs:
1. `dashboard_data/aggregated_data.json` - Main data source
2. `dashboard_data/themes/*.png` - Wordcloud images
3. `dashboard_data/themes/comprehensive_theme_analysis.json` - Theme data
4. `citations/json/*.json` - Citation data (keep as-is)
5. `datasets/*.json` - Dataset metadata (keep as-is)

## CLI Commands to Keep

### Essential Commands
- `dataset-citations-discover` - Dataset discovery
- `dataset-citations-update` - Citation updates
- `dataset-citations-retrieve-metadata` - Metadata retrieval
- `dataset-citations-score-confidence` - Confidence scoring
- `dataset-citations-generate-embeddings` - Embedding generation

### Analysis Commands (to simplify)
- `dataset-citations-analyze-temporal` - Keep but simplify
- `dataset-citations-analyze-temporal-themes` - Keep for wordclouds

### Commands to Remove
- `dataset-citations-analyze-networks` - Requires Neo4j, not used
- `dataset-citations-create-network-visualizations` - Obsolete
- `dataset-citations-create-research-context-networks` - Not used
- `dataset-citations-create-theme-networks` - Not used
- `dataset-citations-load-graph` - Neo4j related
- `dataset-citations-export-external-tools` - Not used
- `dataset-citations-analyze-umap` - Replaced by themes
- `dataset-citations-automate-visualization-updates` - Obsolete

## Python Modules to Remove
- `src/dataset_citations/graph/neo4j_*.py` - Neo4j dependencies
- `src/dataset_citations/graph/network_visualizations.py` - Obsolete
- Unused CLI modules corresponding to removed commands

## Workflow Updates
1. Update `run_end_to_end_workflow.sh` to use simplified pipeline
2. Use `run_analysis_only.sh` for analysis updates
3. Remove Neo4j-dependent steps

## Testing After Cleanup
1. Run `run_analysis_only.sh` to verify analysis works
2. Check dashboard displays correctly
3. Verify all wordclouds and stats are generated
4. Run tests to ensure nothing critical was removed