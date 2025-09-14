#!/bin/bash
set -e

echo "=== Testing Citation Update (Should Find Missing Citations) ==="
echo "Dataset: ds003555"
echo "Current citations in test: 8"
echo "Expected to find: 10 (2 missing citations)"
echo ""

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-citations

cd /Users/yahya/Documents/git/dataset_citations/tests/test_data/workflow_test

echo "Step 1: Current state"
echo "Previous citations CSV shows:"
cat previous_citations.csv
echo ""
echo "Current JSON has:"
jq '.num_citations' citations/json/ds003555_citations.json
echo ""

echo "Step 2: Running citation update (THIS IS THE KEY TEST)"
echo "This should find the 2 missing citations..."
echo ""

# Load and EXPORT environment variables from .secrets
if [ -f "/Users/yahya/Documents/git/dataset_citations/.secrets" ]; then
    source /Users/yahya/Documents/git/dataset_citations/.secrets
    export SCRAPERAPI_KEY
    export GITHUB_TOKEN
    echo "Environment variables loaded and exported"
    echo "SCRAPERAPI_KEY is set: ${SCRAPERAPI_KEY:+YES}"
fi

# Run the actual citation update
dataset-citations-update \
  --dataset-list-file discovered_datasets.txt \
  --previous-citations-file previous_citations.csv \
  --output-dir citations/ \
  --workers 1 \
  --output-format json

echo ""
echo "Step 3: Check results"
echo "New JSON citation count:"
jq '.num_citations' citations/json/ds003555_citations.json

echo ""
echo "New citation details (first 3):"
jq '.citation_details[:3] | .[].title' citations/json/ds003555_citations.json

echo ""
echo "Step 4: Regenerate CSV from updated JSON"
TODAY_DATE=$(date +%d%m%Y)
dataset-citations-regenerate \
  --json-dir citations/json \
  --output-dir citations \
  --date-suffix ${TODAY_DATE} \
  --update-previous

echo ""
echo "Step 5: Final check"
echo "Updated CSV shows:"
cat citations/citations_${TODAY_DATE}.csv

echo ""
echo "=== TEST COMPLETE ==="
echo "SUCCESS if citations increased from 8 to 10"