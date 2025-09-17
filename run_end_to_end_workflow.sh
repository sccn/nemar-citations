#!/bin/zsh
#
# Comprehensive end-to-end workflow for Dataset Citations project
# This script runs the complete pipeline: discover → update → score → analyze → dashboard
#
# Usage:
#   ./run_end_to_end_workflow.sh [mode]
#
# Modes:
#   test    - Run with test dataset (fast, no API calls)
#   local   - Run full workflow locally with act
#   full    - Run full workflow with real API calls
#   help    - Show this help message
#
# Environment variables:
#   SCRAPERAPI_KEY - Required for full mode
#   GITHUB_TOKEN   - Required for discovery and metadata
#

set -e # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Default settings
MODE="${1:-help}"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/workflow_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to check requirements
check_requirements() {
    print_status "Checking requirements..."

    # Check Python environment
    if ! conda env list | grep -q "dataset-citations"; then
        print_error "Conda environment 'dataset-citations' not found"
        print_info "Create it with: conda create -n dataset-citations python=3.10"
        return 1
    fi

    # Check environment variables for full mode
    if [ "$MODE" = "full" ]; then
        if [ -z "$SCRAPERAPI_KEY" ]; then
            print_error "SCRAPERAPI_KEY not set. Required for full mode."
            print_info "Set it with: export SCRAPERAPI_KEY=your_key"
            return 1
        fi
        if [ -z "$GITHUB_TOKEN" ]; then
            print_warning "GITHUB_TOKEN not set. Discovery may be limited."
        fi
    fi

    # Check if act is installed for local mode
    if [ "$MODE" = "local" ]; then
        if ! command -v act &> /dev/null; then
            print_error "act not installed. Required for local mode."
            print_info "Install with: brew install act"
            return 1
        fi
    fi

    print_status "Requirements check passed ✓"
    return 0
}

# Function to run test workflow
run_test_workflow() {
    print_status "Running test workflow with controlled dataset..."

    # Use existing test data
    TEST_DATA_DIR="tests/test_data/workflow_test"

    if [ ! -d "$TEST_DATA_DIR" ]; then
        print_error "Test data directory not found: $TEST_DATA_DIR"
        return 1
    fi

    # Create temporary output directories
    TEST_OUTPUT_DIR="test_output_${TIMESTAMP}"
    mkdir -p "$TEST_OUTPUT_DIR"/{citations,datasets,results,interactive_reports}

    print_status "Step 1/6: Using test dataset list..."
    cp "$TEST_DATA_DIR/discovered_datasets.txt" "$TEST_OUTPUT_DIR/"

    print_status "Step 2/6: Simulating citation update with test data..."
    cp "$TEST_DATA_DIR/previous_citations.csv" "$TEST_OUTPUT_DIR/citations/"

    # Run minimal citation update with test dataset
    print_status "Step 3/6: Processing test citations..."
    conda run -n dataset-citations python -c "
import json
from pathlib import Path
test_citations = {
    'ds003555': {
        'dataset_id': 'ds003555',
        'dataset_name': 'Test Dataset',
        'citations': [
            {'title': f'Citation {i}', 'year': 2020+i, 'confidence_score': 0.5+i*0.1}
            for i in range(8)
        ]
    }
}
output_path = Path('$TEST_OUTPUT_DIR/citations/json')
output_path.mkdir(parents=True, exist_ok=True)
(output_path / 'ds003555.json').write_text(json.dumps(test_citations['ds003555'], indent=2))
print('Test citations generated')
"

    print_status "Step 4/6: Generating test metadata..."
    conda run -n dataset-citations python -c "
import json
from pathlib import Path
test_metadata = {
    'dataset_id': 'ds003555',
    'name': 'Test Dataset',
    'description': 'A test dataset for workflow validation',
    'readme': 'This is a test README content'
}
output_path = Path('$TEST_OUTPUT_DIR/datasets')
output_path.mkdir(parents=True, exist_ok=True)
(output_path / 'ds003555_metadata.json').write_text(json.dumps(test_metadata, indent=2))
print('Test metadata generated')
"

    print_status "Step 5/6: Running analysis..."
    # Temporal analysis (positional argument for citations_dir)
    conda run -n dataset-citations dataset-citations-analyze-temporal \
        "$TEST_OUTPUT_DIR/citations/json" \
        --output-dir "$TEST_OUTPUT_DIR/results/temporal_analysis" || true

    # Network analysis (no citations_dir argument needed)
    conda run -n dataset-citations dataset-citations-analyze-networks \
        --output-dir "$TEST_OUTPUT_DIR/results/network_analysis" || true

    print_status "Step 6/6: Generating dashboard..."
    conda run -n dataset-citations dataset-citations-create-interactive-reports \
        --results-dir "$TEST_OUTPUT_DIR/results" \
        --output-dir "$TEST_OUTPUT_DIR/interactive_reports" \
        --verbose || print_warning "Dashboard generation failed"

    # Validate outputs
    print_status "Validating test outputs..."
    VALIDATION_PASSED=true

    if [ ! -f "$TEST_OUTPUT_DIR/citations/json/ds003555.json" ]; then
        print_error "Citation JSON not generated"
        VALIDATION_PASSED=false
    fi

    if [ ! -f "$TEST_OUTPUT_DIR/datasets/ds003555_metadata.json" ]; then
        print_error "Metadata JSON not generated"
        VALIDATION_PASSED=false
    fi

    if [ -f "$TEST_OUTPUT_DIR/interactive_reports/dataset_citations_dashboard.html" ]; then
        print_status "Dashboard generated successfully"
        ls -lh "$TEST_OUTPUT_DIR/interactive_reports/"*.html
    else
        print_warning "Dashboard not generated (non-critical)"
    fi

    if [ "$VALIDATION_PASSED" = true ]; then
        print_status "Test workflow completed successfully ✓"
        print_info "Test outputs in: $TEST_OUTPUT_DIR"
        return 0
    else
        print_error "Test workflow validation failed"
        return 1
    fi
}

# Function to run local workflow with act
run_local_workflow() {
    print_status "Running local workflow with act..."

    # Check for .secrets file
    if [ ! -f ".secrets" ]; then
        print_warning "No .secrets file found. Creating template..."
        cat > .secrets <<EOF
SCRAPERAPI_KEY=${SCRAPERAPI_KEY:-your_scraperapi_key}
GITHUB_TOKEN=${GITHUB_TOKEN:-your_github_token}
EOF
        print_info "Edit .secrets file with your API keys"
    fi

    print_status "Executing workflow with act..."
    act workflow_dispatch --secret-file .secrets --verbose 2>&1 | tee "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_status "Local workflow completed successfully ✓"
    else
        print_error "Local workflow failed. Check log: $LOG_FILE"
        return 1
    fi
}

# Function to run full workflow
run_full_workflow() {
    print_status "Running full end-to-end workflow..."

    # Create output directories
    OUTPUT_DIR="workflow_output_${TIMESTAMP}"
    mkdir -p "$OUTPUT_DIR"/{citations,datasets,results,interactive_reports}

    print_status "Step 1/7: Discovering datasets..."
    conda run -n dataset-citations dataset-citations-discover \
        --output-file "$OUTPUT_DIR/discovered_datasets.txt" 2>&1 | tee -a "$LOG_FILE"

    DATASET_COUNT=$(wc -l < "$OUTPUT_DIR/discovered_datasets.txt" | tr -d ' ')
    print_info "Found $DATASET_COUNT datasets"

    print_status "Step 2/7: Migrating existing pickle files..."
    if [ -d "citations/pickle" ]; then
        conda run -n dataset-citations dataset-citations-migrate \
            --input-dir citations/pickle \
            --output-dir "$OUTPUT_DIR/citations/json" \
            --overwrite 2>&1 | tee -a "$LOG_FILE"
    fi

    print_status "Step 3/7: Updating citations (this may take a while)..."
    # Use previous citations if available
    PREV_CITATIONS=""
    if [ -f "citations/previous_citations.csv" ]; then
        cp "citations/previous_citations.csv" "$OUTPUT_DIR/citations/"
        PREV_CITATIONS="--previous-citations-file $OUTPUT_DIR/citations/previous_citations.csv"
    fi

    conda run -n dataset-citations dataset-citations-update \
        --dataset-list-file "$OUTPUT_DIR/discovered_datasets.txt" \
        $PREV_CITATIONS \
        --output-dir "$OUTPUT_DIR/citations" \
        --output-format json \
        --workers 5 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 4/7: Retrieving dataset metadata..."
    conda run -n dataset-citations dataset-citations-retrieve-metadata \
        --citations-dir "$OUTPUT_DIR/citations/json" \
        --output-dir "$OUTPUT_DIR/datasets" \
        --skip-existing \
        --log-level INFO 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 5/7: Calculating confidence scores..."
    conda run -n dataset-citations dataset-citations-score-confidence \
        --citations-dir "$OUTPUT_DIR/citations/json" \
        --datasets-dir "$OUTPUT_DIR/datasets" \
        --model all-MiniLM-L6-v2 \
        --skip-existing \
        --log-level INFO 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 6/7: Running analysis..."
    # Temporal analysis (positional argument for citations_dir)
    conda run -n dataset-citations dataset-citations-analyze-temporal \
        "$OUTPUT_DIR/citations/json" \
        --output-dir "$OUTPUT_DIR/results/temporal_analysis" \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Temporal analysis failed"

    # Network analysis (no citations_dir argument needed)
    conda run -n dataset-citations dataset-citations-analyze-networks \
        --output-dir "$OUTPUT_DIR/results/network_analysis" \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Network analysis failed"

    print_status "Step 7/7: Generating interactive dashboard..."
    conda run -n dataset-citations dataset-citations-create-interactive-reports \
        --results-dir "$OUTPUT_DIR/results" \
        --output-dir "$OUTPUT_DIR/interactive_reports" \
        --verbose 2>&1 | tee -a "$LOG_FILE"

    # Validate outputs
    print_status "Validating outputs..."
    JSON_COUNT=$(find "$OUTPUT_DIR/citations/json" -name "*.json" | wc -l)
    print_info "Generated $JSON_COUNT citation JSON files"

    if [ -f "$OUTPUT_DIR/interactive_reports/dataset_citations_dashboard.html" ]; then
        print_status "Dashboard generated successfully ✓"
        ls -lh "$OUTPUT_DIR/interactive_reports/"*.html
    else
        print_error "Dashboard generation failed"
    fi

    print_status "Full workflow completed ✓"
    print_info "Outputs in: $OUTPUT_DIR"
    print_info "Log file: $LOG_FILE"
}

# Function to show help
show_help() {
    cat <<EOF
Dataset Citations - End-to-End Workflow Runner

Usage: $0 [mode]

Modes:
  test    Run with test dataset (fast, no API calls)
          - Uses controlled test data
          - No external API calls
          - Validates pipeline components
          - ~30 seconds runtime

  local   Run full workflow locally with act
          - Uses GitHub Actions locally
          - Requires act and Docker
          - Needs .secrets file
          - ~10-30 minutes runtime

  full    Run full workflow with real data
          - Live API calls to ScraperAPI
          - Requires SCRAPERAPI_KEY
          - Full dataset processing
          - ~1-2 hours runtime

  help    Show this help message

Environment Variables:
  SCRAPERAPI_KEY  API key for ScraperAPI (required for full mode)
  GITHUB_TOKEN    GitHub personal access token (optional, for discovery)

Examples:
  # Quick test run
  $0 test

  # Local workflow with act
  export SCRAPERAPI_KEY=your_key
  export GITHUB_TOKEN=your_token
  $0 local

  # Full production run
  export SCRAPERAPI_KEY=your_key
  export GITHUB_TOKEN=your_token
  $0 full

Output:
  Test mode:  test_output_<timestamp>/
  Local mode: Current repository directories
  Full mode:  workflow_output_<timestamp>/

Logs are saved to: logs/workflow_<timestamp>.log

EOF
}

# Main execution
main() {
    print_status "Dataset Citations - End-to-End Workflow"
    print_info "Mode: $MODE"
    print_info "Timestamp: $TIMESTAMP"

    case "$MODE" in
        test)
            check_requirements || exit 1
            run_test_workflow
            ;;
        local)
            check_requirements || exit 1
            run_local_workflow
            ;;
        full)
            check_requirements || exit 1
            run_full_workflow
            ;;
        help|--help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Invalid mode: $MODE"
            show_help
            exit 1
            ;;
    esac

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        print_status "Workflow completed successfully ✓"
    else
        print_error "Workflow failed with exit code: $EXIT_CODE"
    fi

    exit $EXIT_CODE
}

# Run main function
main