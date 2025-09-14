#!/bin/bash
# Test script for modular dashboard generation

set -e  # Exit on error

echo "Testing modular dashboard generation..."
echo "======================================="

# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-citations

# Test with minimal dashboard first
echo "1. Testing minimal dashboard generation..."
python -m dataset_citations.cli.create_interactive_reports_modular \
    --results-dir tests/test_data/workflow_test \
    --dashboard-type minimal \
    --output-dir test_output \
    --verbose

# Check if file was created
if [ -f "test_output/dataset_citations_dashboard_minimal.html" ]; then
    echo "✓ Minimal dashboard created successfully"
    echo "  Size: $(ls -lh test_output/dataset_citations_dashboard_minimal.html | awk '{print $5}')"
else
    echo "✗ Failed to create minimal dashboard"
    exit 1
fi

echo ""
echo "2. Testing standard dashboard generation with test data..."
python -m dataset_citations.cli.create_interactive_reports_modular \
    --results-dir tests/test_data/workflow_test \
    --citations-dir tests/test_data/workflow_test \
    --dashboard-type standard \
    --output-dir test_output \
    --verbose

# Check if file was created
if [ -f "test_output/dataset_citations_dashboard_standard.html" ]; then
    echo "✓ Standard dashboard created successfully"
    echo "  Size: $(ls -lh test_output/dataset_citations_dashboard_standard.html | awk '{print $5}')"
else
    echo "✗ Failed to create standard dashboard"
    exit 1
fi

echo ""
echo "======================================="
echo "All tests passed successfully!"
echo "Dashboard files created in test_output/"
ls -la test_output/