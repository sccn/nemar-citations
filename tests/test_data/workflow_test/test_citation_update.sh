#!/bin/bash
# Smoke test for the opencite-backed dataset-citations-update CLI.
# Runs against the ds003555 fixture in this directory; expects citations
# discovered via DOIs in OpenNeuroDatasets/ds003555/dataset_description.json.
set -e

echo "=== Testing Citation Update (opencite backend) ==="
echo "Dataset: ds003555"
echo ""

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$REPO_ROOT/tests/test_data/workflow_test"

echo "Step 1: Current state"
if [ -f previous_citations.csv ]; then
    echo "Previous citations CSV shows:"
    cat previous_citations.csv
    echo ""
fi
if [ -f citations/json_opencite/ds003555_citations.json ]; then
    echo "Current opencite JSON has:"
    jq '.num_citations' citations/json_opencite/ds003555_citations.json
    echo ""
fi

echo "Step 2: Running citation update via opencite"
# Optional opencite keys for higher rate limits. Missing keys degrade
# gracefully to unauthenticated access.
if [ -f "$REPO_ROOT/.secrets" ]; then
    set -a
    source "$REPO_ROOT/.secrets"
    set +a
    echo "Loaded secrets from .secrets"
fi

(cd "$REPO_ROOT" && uv run dataset-citations-update \
  --dataset-list-file tests/test_data/workflow_test/discovered_datasets.txt \
  --output-dir tests/test_data/workflow_test/citations/)

echo ""
echo "Step 3: Check results"
echo "New opencite JSON citation count:"
jq '.num_citations' citations/json_opencite/ds003555_citations.json

echo ""
echo "New citation details (first 3):"
jq '.citation_details[:3] | .[].title' citations/json_opencite/ds003555_citations.json

echo ""
echo "Step 4: Regenerate CSV from updated JSON"
TODAY_DATE=$(date +%d%m%Y)
(cd "$REPO_ROOT" && uv run dataset-citations-regenerate \
  --json-dir tests/test_data/workflow_test/citations/json_opencite \
  --output-dir tests/test_data/workflow_test/citations \
  --date-suffix ${TODAY_DATE} \
  --update-previous)

echo ""
echo "Step 5: Final check"
echo "Updated CSV shows:"
cat citations/citations_${TODAY_DATE}.csv

echo ""
echo "=== TEST COMPLETE ==="
