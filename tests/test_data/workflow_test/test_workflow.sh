#!/bin/bash
set -e

echo "=== Test Workflow for Single Dataset ==="
echo "Testing with ds003555 (8 citations in test, should find 10)"
echo ""

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-citations

# Set working directory
cd /Users/yahya/Documents/git/dataset_citations/tests/test_data/workflow_test

echo "Step 1: Skip discovery (using pre-made discovered_datasets.txt)"
echo "  - Dataset: ds003555"
echo ""

echo "Step 2: Skip migration (no pickle files in test)"
echo ""

echo "Step 3: Update citations"
echo "  - Input: discovered_datasets.txt (1 dataset)"
echo "  - Previous: 8 citations"
echo "  - Expected: Should find 10 citations"

# This will actually call the API - comment out for dry run
# dataset-citations-update \
#   --dataset-list-file discovered_datasets.txt \
#   --previous-citations-file previous_citations.csv \
#   --output-dir citations/ \
#   --workers 1 \
#   --output-format json

echo ""
echo "Step 4: Retrieve metadata (would need GitHub token)"
# dataset-citations-retrieve-metadata \
#   --citations-dir citations/json \
#   --output-dir datasets \
#   --skip-existing

echo ""
echo "Step 5: Calculate confidence scores"
# dataset-citations-score-confidence \
#   --citations-dir citations/json \
#   --datasets-dir datasets \
#   --model all-MiniLM-L6-v2 \
#   --skip-existing

echo ""
echo "Step 6: Generate CSV from JSON"
TODAY_DATE=$(date +%d%m%Y)
# dataset-citations-regenerate \
#   --json-dir citations/json \
#   --output-dir citations \
#   --date-suffix ${TODAY_DATE} \
#   --update-previous

echo ""
echo "Step 7: Dashboard generation (MISSING FROM WORKFLOW!)"
echo "  This is where the workflow breaks - no dashboard generation step"

echo ""
echo "=== Test Complete ==="
echo "Uncomment commands to run actual test"