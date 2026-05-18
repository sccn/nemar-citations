#!/bin/bash
set -e

echo "=== Testing Citation Update (Should Find Missing Citations) ==="
echo "Dataset: ds003555"
echo "Current citations in test: 8"
echo "Expected to find: 10 (2 missing citations)"
echo ""

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$REPO_ROOT/tests/test_data/workflow_test"

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
if [ -f "$REPO_ROOT/.secrets" ]; then
    source "$REPO_ROOT/.secrets"
    export SCRAPERAPI_KEY
    export GITHUB_TOKEN
    echo "Environment variables loaded and exported"
    echo "SCRAPERAPI_KEY is set: ${SCRAPERAPI_KEY:+YES}"
fi

# Run the actual citation update
(cd "$REPO_ROOT" && uv run dataset-citations-update \
  --dataset-list-file tests/test_data/workflow_test/discovered_datasets.txt \
  --previous-citations-file tests/test_data/workflow_test/previous_citations.csv \
  --output-dir tests/test_data/workflow_test/citations/ \
  --workers 1 \
  --output-format json)

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
(cd "$REPO_ROOT" && uv run dataset-citations-regenerate \
  --json-dir tests/test_data/workflow_test/citations/json \
  --output-dir tests/test_data/workflow_test/citations \
  --date-suffix ${TODAY_DATE} \
  --update-previous)

echo ""
echo "Step 5: Final check"
echo "Updated CSV shows:"
cat citations/citations_${TODAY_DATE}.csv

echo ""
echo "=== TEST COMPLETE ==="
echo "SUCCESS if citations increased from 8 to 10"