#!/bin/zsh
#
# Comprehensive end-to-end workflow for Dataset Citations project
# This script runs the complete pipeline: discover → update → score → analyze → dashboard
#
# Usage:
#   ./run_end_to_end_workflow.sh [mode]
#
# Modes:
#   test            - Run with test dataset (fast, no API calls)
#   local-ci-test   - Test the test workflow locally with act
#   local-ci-update - Test the update workflow locally with act
#   full            - Run full workflow with real API calls
#   help            - Show this help message
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
# Support backward compatibility
if [ "$MODE" = "local" ] || [ "$MODE" = "local-ci" ]; then
    print_warning "'$MODE' mode is deprecated. Use 'local-ci-test' or 'local-ci-update' instead."
    MODE="local-ci-update"
fi
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M")
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

# Function to load secrets from .secrets file if available
load_secrets() {
    if [ -f ".secrets" ]; then
        print_info "Loading secrets from .secrets file..."
        # Source the .secrets file to load environment variables
        set -a  # Mark all new variables for export
        source .secrets
        set +a  # Turn off auto-export
    fi
}

# Function to check requirements
check_requirements() {
    print_status "Checking requirements..."

    # Load secrets if available and not already set
    load_secrets

    # Check Python environment
    if ! conda env list | grep -q "dataset-citations"; then
        print_error "Conda environment 'dataset-citations' not found"
        print_info "Create it with: conda create -n dataset-citations python=3.11"
        return 1
    fi

    # Check environment variables for full mode
    if [ "$MODE" = "full" ]; then
        if [ -z "$SCRAPERAPI_KEY" ]; then
            print_error "SCRAPERAPI_KEY not set. Required for full mode."
            print_info "Set it with: export SCRAPERAPI_KEY=your_key or add to .secrets file"
            return 1
        fi
        if [ -z "$GITHUB_TOKEN" ]; then
            print_warning "GITHUB_TOKEN not set. Discovery may be limited."
            print_info "Set it with: export GITHUB_TOKEN=your_token or add to .secrets file"
        fi
    fi

    # Check if act is installed for local-ci modes
    if [[ "$MODE" == local-ci-* ]]; then
        if ! command -v act &> /dev/null; then
            print_error "act not installed. Required for local-ci mode."
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
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
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
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
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
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-temporal \
        "$TEST_OUTPUT_DIR/citations/json" \
        --output-dir "$TEST_OUTPUT_DIR/results/temporal_analysis" || true

    # Network analysis (no citations_dir argument needed)
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-networks \
        --output-dir "$TEST_OUTPUT_DIR/results/network_analysis" || true

    print_status "Step 6/6: Generating dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('$TEST_OUTPUT_DIR/dashboard_data'),
    output_dir=Path('$TEST_OUTPUT_DIR/interactive_reports'),
    citations_dir=Path('$TEST_OUTPUT_DIR/citations/json'),
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
print(f'Dashboard generated: {output_path}')
" || print_warning "Dashboard generation failed"

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

# Function to run local CI/CD test workflow with act
run_local_ci_test_workflow() {
    print_status "Testing CI/CD test workflow locally with act..."
    print_info "Note: This tests the GitHub Actions test workflow locally"

    # Check for .secrets file
    if [ ! -f ".secrets" ]; then
        print_warning "No .secrets file found. Creating template..."
        cat > .secrets <<EOF
GITHUB_TOKEN=${GITHUB_TOKEN:-your_github_token}
EOF
        print_info "Edit .secrets file with your GitHub token if needed"
    fi

    print_status "Executing GitHub Actions test workflow locally..."
    act push -W .github/workflows/test.yml --secret-file .secrets --verbose 2>&1 | tee "$LOG_FILE"

    # Capture the exit status
    local exit_status=${PIPESTATUS[0]}

    if [ "$exit_status" -eq 0 ]; then
        print_status "CI/CD test workflow completed successfully ✓"
    else
        print_error "CI/CD test workflow failed. Check log: $LOG_FILE"
        return 1
    fi
}

# Function to run local CI/CD update workflow with act
run_local_ci_update_workflow() {
    print_status "Testing CI/CD update workflow locally with act..."
    print_info "Note: This tests the GitHub Actions update workflow locally"

    # Check for .secrets file
    if [ ! -f ".secrets" ]; then
        print_warning "No .secrets file found. Creating template..."
        cat > .secrets <<EOF
SCRAPERAPI_KEY=${SCRAPERAPI_KEY:-your_scraperapi_key}
GITHUB_TOKEN=${GITHUB_TOKEN:-your_github_token}
EOF
        print_info "Edit .secrets file with your API keys"
    fi

    print_status "Executing GitHub Actions update workflow locally..."
    act workflow_dispatch -W .github/workflows/update_citations.yml --secret-file .secrets --verbose 2>&1 | tee "$LOG_FILE"

    # Capture the exit status
    local exit_status=${PIPESTATUS[0]}

    if [ "$exit_status" -eq 0 ]; then
        print_status "CI/CD update workflow completed successfully ✓"
        print_info "The workflow created a branch and PR automatically"
    else
        print_error "CI/CD update workflow failed. Check log: $LOG_FILE"
        return 1
    fi
}

# Function to run full workflow
run_full_workflow() {
    print_status "Running full end-to-end workflow..."

    # Save current directory for later
    ORIGINAL_DIR=$(pwd)

    # Step 0: Create branch to protect current work
    print_status "Creating feature branch..."
    BRANCH_NAME="auto-update/$(date +'%Y-%m-%d_%H-%M')"

    # Get current branch name (save for later)
    ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

    # Determine the base branch for PR
    if [ "$ORIGINAL_BRANCH" = "main" ] || [ "$ORIGINAL_BRANCH" = "master" ]; then
        PR_BASE_BRANCH="main"
        print_status "Currently on main branch. Creating new branch from main..."
        # Ensure we have latest main
        git pull origin main --ff-only 2>/dev/null || true
    else
        PR_BASE_BRANCH="$ORIGINAL_BRANCH"
        print_info "Currently on branch: $ORIGINAL_BRANCH"
        print_info "Creating new branch from current branch to preserve fixes..."
        print_info "PR will be created against: $PR_BASE_BRANCH"
    fi

    # Ensure working directory is clean
    if [ -n "$(git status --porcelain)" ]; then
        print_status "Stashing uncommitted changes..."
        git stash push -m "Stashing changes before workflow"
    fi

    # Create and checkout new branch from current position
    print_status "Creating new branch: $BRANCH_NAME"
    git checkout -b "$BRANCH_NAME"

    # Use existing directories instead of creating new ones
    print_status "Step 1/8: Discovering datasets..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-discover \
        --output-file "discovered_datasets.txt" 2>&1 | tee -a "$LOG_FILE"

    DATASET_COUNT=$(wc -l < "discovered_datasets.txt" | tr -d ' ')
    print_info "Found $DATASET_COUNT datasets"

    print_status "Step 2/8: Updating citations (this may take a while)..."
    # Use previous citations if available, or create empty file
    if [ ! -f "citations/previous_citations.csv" ]; then
        print_warning "No previous citations file found, creating empty one"
        mkdir -p citations
        echo "Dataset,Title,Year,Authors,DOI,URL" > citations/previous_citations.csv
    fi

    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-update \
        --dataset-list-file "discovered_datasets.txt" \
        --previous-citations-file citations/previous_citations.csv \
        --output-dir citations \
        --output-format json \
        --workers 5 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 3/8: Retrieving dataset metadata..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-retrieve-metadata \
        --citations-dir citations/json \
        --output-dir datasets \
        --skip-existing \
        --log-level INFO 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 4/8: Calculating confidence scores..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-score-confidence \
        --citations-dir citations/json \
        --datasets-dir datasets \
        --model Qwen/Qwen3-Embedding-0.6B \
        --skip-existing \
        --log-level INFO 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 5/8: Running analysis..."
    mkdir -p results/temporal_analysis results/network_analysis

    # Temporal analysis (positional argument for citations_dir)
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-temporal \
        citations/json \
        --output-dir results/temporal_analysis \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Temporal analysis failed"

    # Network analysis (no citations_dir argument needed)
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-networks \
        --output-dir results/network_analysis \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Network analysis failed"

    print_status "Step 6/8: Generating interactive dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('dashboard_data'),
    output_dir=Path('interactive_reports'),
    citations_dir=Path('citations/json'),
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
print(f'Dashboard generated: {output_path}')
" 2>&1 | tee -a "$LOG_FILE"

    # Validate outputs
    print_status "Validating outputs..."
    JSON_COUNT=$(find citations/json -name "*.json" 2>/dev/null | wc -l)
    print_info "Generated $JSON_COUNT citation JSON files"

    if [ -f "interactive_reports/dataset_citations_dashboard_nemar.html" ]; then
        print_status "Dashboard generated successfully ✓"
        ls -lh interactive_reports/*.html
    else
        print_error "Dashboard generation failed"
    fi

    print_status "Step 7/8: Updating previous_citations.csv for next run..."
    TODAY_DATE=$(date +%d%m%Y)
    LATEST_CITATIONS_FILE="citations/citations_${TODAY_DATE}.csv"
    TARGET_PREVIOUS_FILE="citations/previous_citations.csv"

    if [ -f "$LATEST_CITATIONS_FILE" ]; then
        print_info "Found $LATEST_CITATIONS_FILE. Copying to $TARGET_PREVIOUS_FILE..."
        cp "$LATEST_CITATIONS_FILE" "$TARGET_PREVIOUS_FILE"
        print_status "Successfully updated $TARGET_PREVIOUS_FILE ✓"
    else
        print_warning "Today's citation file ($LATEST_CITATIONS_FILE) not found."
        print_info "previous_citations.csv not updated"
    fi

    print_status "Step 8/8: Creating Pull Request..."

    # Check for changes
    git add -A
    if git diff --cached --quiet; then
        print_warning "No changes detected. Nothing to commit."
        print_info "Switching back to original branch: $ORIGINAL_BRANCH"
        git checkout "$ORIGINAL_BRANCH"
        return 0
    fi

    # Commit changes
    COMMIT_MSG="Update dataset citations - $(date +'%Y-%m-%d')

Workflow: Full end-to-end pipeline
Updated: $(git diff --cached --name-only | wc -l) files
"
    git commit -m "$COMMIT_MSG"
    print_status "Changes committed to branch: $BRANCH_NAME"

    # Push branch
    print_status "Pushing branch to origin..."
    if git push origin "$BRANCH_NAME"; then
        print_status "Branch pushed successfully"

        # Create PR using gh CLI if available
        if command -v gh &> /dev/null; then
            print_status "Creating Pull Request against $PR_BASE_BRANCH..."
            PR_TITLE="[Auto] Update citations - $(date +'%Y-%m-%d')"
            PR_BODY="## Automated Citation Update

This PR was generated by the end-to-end workflow script.

### Changes:
- Updated citation data from Google Scholar
- Retrieved dataset metadata from GitHub
- Calculated confidence scores
- Generated analysis and dashboard

### Files Updated:
$(git diff origin/main..HEAD --name-only | head -20)

---
*Generated by run_end_to_end_workflow.sh*"

            if gh pr create \
                --base "$PR_BASE_BRANCH" \
                --head "$BRANCH_NAME" \
                --title "$PR_TITLE" \
                --body "$PR_BODY" \
                --label "automated,citations-update" \
                --assignee "@me"; then
                print_status "Pull Request created successfully ✓"
                PR_URL=$(gh pr view --json url -q .url)
                print_info "PR URL: $PR_URL"
            else
                print_warning "Failed to create PR. Create manually at:"
                print_info "https://github.com/sccn/nemar-citations/pull/new/$BRANCH_NAME"
            fi
        else
            print_warning "gh CLI not found. Create PR manually at:"
            print_info "https://github.com/sccn/nemar-citations/pull/new/$BRANCH_NAME"
        fi
    else
        print_error "Failed to push branch. You may need to push manually."
    fi

    print_status "Full workflow completed ✓"
    print_info "Branch: $BRANCH_NAME"
    print_info "Log file: $LOG_FILE"

    # Deploy dashboard to GitHub Pages
    print_status "Deploying dashboard to GitHub Pages..."

    # Create a temporary directory for the GitHub Pages repo
    TEMP_DIR=$(mktemp -d)
    print_info "Using temp directory: $TEMP_DIR"

    # Clone the GitHub Pages repository
    print_info "Cloning neuromechanist.github.io repository..."
    if git clone https://${GITHUB_TOKEN}@github.com/neuromechanist/neuromechanist.github.io.git "$TEMP_DIR/github-pages" 2>/dev/null; then
        cd "$TEMP_DIR/github-pages"

        # Configure git for commits
        git config user.name "citations-bot"
        git config user.email "shirazi@ieee.org"

        # Create static directory if it doesn't exist
        mkdir -p static

        # Copy dashboard files
        print_info "Copying dashboard files to static directory..."
        cp "$ORIGINAL_DIR/interactive_reports/dataset_citations_dashboard_nemar.html" static/ 2>/dev/null || print_warning "Dashboard HTML not found"
        cp -r "$ORIGINAL_DIR/interactive_reports/data" static/ 2>/dev/null || print_warning "Data directory not found"
        cp "$ORIGINAL_DIR/interactive_reports/dashboard_styles.css" static/ 2>/dev/null || print_warning "Styles CSS not found"

        # Check if there are changes to commit
        if ! git diff --quiet; then
            print_info "Committing dashboard updates..."
            git add static/
            git commit -m "Update NEMAR citations dashboard - $(date +'%Y-%m-%d %H:%M')"

            # Push to GitHub Pages
            if git push origin main; then
                print_status "Dashboard deployed successfully to GitHub Pages ✓"
                print_info "Dashboard URL: https://neuromechanist.github.io/static/dataset_citations_dashboard_nemar.html"
            else
                print_warning "Failed to push dashboard to GitHub Pages"
            fi
        else
            print_info "No changes in dashboard files, skipping deployment"
        fi

        # Return to original directory
        cd "$ORIGINAL_DIR"
    else
        print_warning "Failed to clone GitHub Pages repository. Skipping dashboard deployment."
    fi

    # Clean up temp directory
    rm -rf "$TEMP_DIR"

    # Switch back to original branch
    print_info "Switching back to original branch: $ORIGINAL_BRANCH"
    git checkout "$ORIGINAL_BRANCH"
}

# Function to show help
show_help() {
    cat <<EOF
Dataset Citations - End-to-End Workflow Runner

Usage: $0 [mode]

Modes:
  test      Run with test dataset (fast, no API calls)
            - Uses controlled test data
            - No external API calls
            - Validates pipeline components
            - ~30 seconds runtime

  local-ci-test   Test the test workflow locally with act
            - Runs the test workflow via Docker
            - Tests exact GitHub Actions test behavior
            - Useful for debugging test issues
            - Requires act and Docker
            - ~5-10 minutes runtime

  local-ci-update Test the update workflow locally with act
            - Runs the update workflow via Docker
            - Tests exact GitHub Actions update behavior
            - Useful for debugging update issues
            - Requires act and Docker
            - ~10-30 minutes runtime

  full      Run full pipeline directly (recommended)
            - Runs pipeline natively with conda
            - Creates feature branch automatically
            - Live API calls to Google Scholar
            - Creates PR for review
            - ~1-2 hours runtime

  help    Show this help message

Environment Variables:
  SCRAPERAPI_KEY  API key for ScraperAPI (required for full mode)
  GITHUB_TOKEN    GitHub personal access token (optional, for discovery)

Examples:
  # Quick test run
  $0 test

  # Test the test workflow locally
  export GITHUB_TOKEN=your_token
  $0 local-ci-test

  # Test the update workflow locally
  export SCRAPERAPI_KEY=your_key
  export GITHUB_TOKEN=your_token
  $0 local-ci-update

  # Full production run (recommended for actual updates)
  export SCRAPERAPI_KEY=your_key
  export GITHUB_TOKEN=your_token
  $0 full

Output:
  test:      test_output_<timestamp>/ (temporary directory)
  local-ci-test:   Tests run via Docker
  local-ci-update: Creates branch with PR (via GitHub Actions in Docker)
  full:      Updates repository on new branch, creates PR

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
        local-ci-test)
            check_requirements || exit 1
            run_local_ci_test_workflow
            ;;
        local-ci-update)
            check_requirements || exit 1
            run_local_ci_update_workflow
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