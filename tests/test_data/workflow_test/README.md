# Workflow Test Infrastructure

## Purpose
Minimal test setup to validate the GitHub Actions workflow pipeline without expensive API calls.

## Test Dataset
- **Dataset ID:** ds003555
- **Original citations:** 10
- **Modified for test:** 8 citations
- **Expected behavior:** Workflow should find 2 missing citations

## Files
- `discovered_datasets.txt` - Single dataset to process
- `previous_citations.csv` - Shows 8 citations (modified)
- `ds003555_citations.json` - Modified JSON with only 8 citations
- `test_workflow.sh` - Simulates workflow steps locally

## Key Finding
The workflow is missing dashboard generation after confidence scoring (Step 7).
This explains why dashboards are being created manually.

## How to Run Test
```bash
cd tests/test_data/workflow_test
./test_workflow.sh  # Dry run to see steps
# Uncomment commands in script to run actual test
```

## Next Steps
1. Add dashboard generation to workflow after CSV validation
2. Include analysis commands before dashboard generation
3. Test with this minimal dataset first