# Current Open Issues (Priority Order)

## Issue #10: Revisit automation
**Status:** OPEN
**Priority:** CRITICAL - DO FIRST
**Problem:** The pipeline was automated before but broke after adding JSON format and dashboard generation. Dashboard is currently generated manually.
**Solution:** Add dashboard generation to workflow after confidence scoring. This MUST be fixed before we can test anything.

## Issue #12: Breakdown the dashboard-making function
**Status:** OPEN
**Priority:** HIGH - DO SECOND
**Problem:** The dashboard-making function `src/dataset_citations/cli/create_interactive_reports.py` is too big (3113 lines), handling all dashboard aspects in one file.
**Solution:** After automation works, modularize into separate components. Test each module as extracted.

## Issue #11: Create a simple test and add CodeCov
**Status:** OPEN
**Priority:** MEDIUM - DO THIRD
**Problem:** No comprehensive test infrastructure. Need tests with real data.
**Solution:** After fixing automation and modularizing, create comprehensive test suite with controlled datasets. Target 75%+ coverage.

## Issue #5: Explore more robust Graph network visualizations
**Status:** OPEN
**Priority:** Low
**Problem:** Current network visualizations could be improved with better libraries.
**Solution:** Investigate D3.js, Sigma.js, or vis.js as alternatives to Cytoscape.

## Recently Closed Issues (Keep in Mind)
- Issue #14: Dashboard modal data (CLOSED - but ensure new code maintains 20+ items)
- Issue #9: Scrollable modal leaderboard (CLOSED)
- Issue #8: Data modality pie chart (CLOSED)
- Issue #6: Bar plot HTML rendering (CLOSED)
- Issue #4: Add hyperlinks to datasets/citations (CLOSED)
- Issue #3: Cumulative growth timeline (CLOSED)
- Issue #1: Dashboard performance (CLOSED - reduced from 18MB to 106KB)