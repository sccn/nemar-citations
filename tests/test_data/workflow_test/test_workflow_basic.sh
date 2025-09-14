#!/bin/bash
set -e

echo "=== Testing Basic Workflow (No Dashboard) ==="
echo "Working directory: $(pwd)"
echo ""

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-citations

# Set working directory
cd /Users/yahya/Documents/git/dataset_citations/tests/test_data/workflow_test

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
dataset-citations-regenerate \
  --json-dir citations/json \
  --output-dir citations \
  --date-suffix ${TODAY_DATE} \
  --update-previous

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