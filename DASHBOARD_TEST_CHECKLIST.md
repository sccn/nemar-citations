# Dashboard Testing Checklist

## Pre-Cleanup Reference State
Date: 2025-09-17
Branch: fix/issue-23-cleanup-consolidate-outputs

### Current Dashboard Components

#### 1. Header Section
- [x] Title: "NEMAR Dataset Citation Analysis"
- [x] Description text present
- [x] 318 datasets mentioned in description

#### 2. Statistics Cards (Top Row)
- [x] Datasets Analyzed: 318
- [x] High-Confidence Citations: 1062
- [x] Research Bridge Papers: 80
- [x] Confidence Threshold: ≥0.4

#### 3. Main Tabs
- [x] Overview (default selected)
- [x] Network Analysis
- [x] Research Themes

#### 4. Overview Tab Content
##### Left Panel - Citation Quality
- [x] Bar chart showing High-Confidence (1062, 84%) vs Low-Confidence (198, 16%)
- [x] Red and gray colors

##### Middle Panel - Growth Timeline
- [x] Line chart showing cumulative citations from 2018 to 2024
- [x] Blue line with data points

##### Right Panel - Data Modalities
- [x] Donut chart showing EEG (63.2%), MEG (23.7%), EG (2%), iEEG (11.2%)
- [x] Blue, purple, red colors

#### 5. Network Analysis Tab
- [x] Interactive network visualization loads
- [x] Nodes and edges visible
- [x] Zoom/pan controls work
- [x] Node hover shows dataset info

#### 6. Research Themes Tab
- [x] Theme 0 wordcloud visible
- [x] Theme 1 wordcloud visible
- [x] Theme 2 wordcloud visible
- [x] Theme 3 wordcloud visible
- [x] Wordclouds have proper colors and layouts

#### 7. Modal Dialogs (Click on cards)
##### Datasets Modal
- [x] Shows 302 total datasets (note: inconsistency with main card)
- [x] Shows 290 with high-conf citations
- [x] Shows 96% coverage
- [x] Lists top 20 datasets with citations

##### Citations Modal
- [x] Shows citation quality breakdown
- [x] Shows temporal distribution
- [x] Shows confidence score distribution

##### Bridge Papers Modal
- [x] Lists bridge papers
- [x] Shows datasets bridged
- [x] Shows citation impact

##### Threshold Modal
- [x] Explains confidence scoring
- [x] Shows threshold value

### File Dependencies Check
```bash
# Files that must exist for dashboard to work
interactive_reports/dataset_citations_dashboard_nemar.html  # Main dashboard
interactive_reports/dashboard_styles.css                     # Styles
dashboard_data/aggregated_data.json                         # Data source
interactive_reports/data/themes/theme_*_wordcloud.png       # Wordclouds
interactive_reports/data/themes/comprehensive_theme_analysis.json  # Theme data
```

### Console Errors Check
- [ ] No JavaScript errors in browser console
- [ ] All resources load successfully (no 404s)
- [ ] Network visualization initializes without errors

## Testing Procedure After Each Cleanup Step

### Quick Test (after minor changes)
1. Open dashboard HTML in browser
2. Check all 4 statistics cards show numbers
3. Click through all 3 tabs
4. Verify wordclouds visible in Research Themes tab

### Full Test (after major changes)
1. Run `./run_analysis_only.sh`
2. Check output for errors
3. Open new dashboard in browser
4. Go through entire checklist above
5. Compare with reference dashboard (saved copy)

### Critical Failures (stop if any occur)
- Dashboard doesn't open
- Statistics cards show 0 or NaN
- Wordclouds missing
- Network visualization broken
- JavaScript errors in console

## Comparison Method
```bash
# Save reference dashboard before cleanup
cp interactive_reports/dataset_citations_dashboard_nemar.html reference_dashboard.html

# After cleanup, compare key metrics
grep -o "318\|1062\|80\|0.4" reference_dashboard.html | sort | uniq -c > reference_metrics.txt
grep -o "318\|1062\|80\|0.4" interactive_reports/dataset_citations_dashboard_nemar.html | sort | uniq -c > new_metrics.txt
diff reference_metrics.txt new_metrics.txt
```

## Rollback Plan
If critical failure occurs:
1. `git stash` current changes
2. `git checkout main`
3. Analyze what went wrong
4. Try more conservative cleanup approach