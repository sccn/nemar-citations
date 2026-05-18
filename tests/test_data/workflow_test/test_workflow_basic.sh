#!/bin/bash
set -e

echo "=== Testing Basic Workflow (No Dashboard) ==="
echo "Working directory: $(pwd)"
echo ""

# Run via uv from the repo root, then cd into the test data dir
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$REPO_ROOT/tests/test_data/workflow_test"

echo "Step 1: Check discovered datasets"
cat discovered_datasets.txt
echo ""

echo "Step 2: Check previous citations"
cat previous_citations.csv
echo ""

echo "Step 3: Check current citation file"
echo "Current citations in test JSON:"
jq '.num_citations' citations/json/ds003555_citations.json
echo ""

echo "Step 4: Test CSV regeneration (should work)"
TODAY_DATE=$(date +%d%m%Y)
(cd "$REPO_ROOT" && uv run dataset-citations-regenerate \
  --json-dir tests/test_data/workflow_test/citations/json \
  --output-dir tests/test_data/workflow_test/citations \
  --date-suffix ${TODAY_DATE} \
  --update-previous)

echo ""
echo "Step 5: Check generated CSV"
if [ -f "citations/citations_${TODAY_DATE}.csv" ]; then
  echo "CSV generated successfully:"
  cat "citations/citations_${TODAY_DATE}.csv"
else
  echo "ERROR: CSV was not generated"
fi

echo ""
echo "=== Basic Workflow Test Complete ==="
echo "This is what currently WORKS in the automation"