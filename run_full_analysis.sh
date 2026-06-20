#!/bin/zsh
#
# Full analysis workflow for Dataset Citations Dashboard
# This script generates all analysis components needed for the complete dashboard
#
# Usage:
#   ./run_full_analysis.sh
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

TIMESTAMP=$(date +"%Y%m%d_%H%M")
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/full_analysis_${TIMESTAMP}.log"

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

# Main analysis workflow
run_full_analysis() {
    print_status "Starting full analysis workflow..."

    # Check if we have citation data
    if [ ! -d "citations/json_opencite" ]; then
        print_error "No citation data found. Run discovery and scraping first."
        return 1
    fi

    JSON_COUNT=$(find citations/json_opencite -name "*.json" 2>/dev/null | wc -l)
    print_info "Found $JSON_COUNT citation JSON files"

    # Clean up and prepare directories
    print_status "Step 1/8: Preparing directories..."
    rm -rf dashboard_data/network 2>/dev/null || true
    rm -rf dashboard_data/themes 2>/dev/null || true
    rm -rf dashboard_data/temporal 2>/dev/null || true
    rm -rf dashboard_data/visualizations 2>/dev/null || true
    rm -rf interactive_reports/data 2>/dev/null || true

    mkdir -p dashboard_data/{network,themes,temporal,visualizations}
    mkdir -p interactive_reports/data/themes

    # Generate embeddings (required for UMAP and theme analysis)
    print_status "Step 2/8: Generating embeddings..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-generate-embeddings \
        --citations citations/json_opencite \
        --datasets datasets \
        --embeddings-dir embeddings \
        --embedding-type both \
        --batch-size 32 \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Some embeddings may have failed"

    # Run UMAP analysis for theme identification
    print_status "Step 3/8: Running UMAP analysis and clustering..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-umap \
        --embeddings-dir embeddings \
        --output-dir dashboard_data \
        --embedding-type both \
        --n-components 2 \
        --clustering \
        --clustering-method kmeans \
        --n-clusters 4 \
        --create-visualizations \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "UMAP analysis had issues"

    # Generate theme analysis with wordclouds
    print_status "Step 4/8: Generating theme analysis with wordclouds..."
    ~/miniconda3/bin/conda run -n dataset-citations python -m dataset_citations.analysis.generate_themes \
        --citations-dir citations/json_opencite \
        --output-dir dashboard_data/themes 2>&1 | tee -a "$LOG_FILE" || print_warning "Theme generation had issues"

    # Generate network analysis data
    print_status "Step 5/8: Generating network analysis data..."
    ~/miniconda3/bin/conda run -n dataset-citations python -m dataset_citations.analysis.generate_network \
        --citations-dir citations/json_opencite \
        --output-dir dashboard_data/network 2>&1 | tee -a "$LOG_FILE"

    # Generate temporal analysis
    print_status "Step 6/8: Generating temporal analysis..."
    ~/miniconda3/bin/conda run -n dataset-citations python -m dataset_citations.analysis.generate_temporal \
        --citations-dir citations/json_opencite \
        --output-dir dashboard_data/temporal 2>&1 | tee -a "$LOG_FILE"

    # Aggregate all data
    print_status "Step 7/8: Aggregating data for dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.data.aggregator import DataAggregator
from pathlib import Path
import json

# Create aggregator
aggregator = DataAggregator(
    results_dir=Path('dashboard_data'),
    citations_dir=Path('citations/json_opencite')
)

# Aggregate all data
data = aggregator.aggregate_all_data()

# Save to dashboard_data
output_file = Path('dashboard_data/aggregated_data.json')
with open(output_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f'Aggregated data saved: {data[\"summary_stats\"][\"total_datasets\"]} datasets')
print(f'Bridge papers found: {data[\"summary_stats\"][\"bridge_papers\"]}')
" 2>&1 | tee -a "$LOG_FILE"

    # Generate dashboard
    print_status "Step 8/8: Generating dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('dashboard_data'),
    output_dir=Path('interactive_reports'),
    citations_dir=Path('citations/json_opencite')
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
print(f'Dashboard generated: {output_path}')
" 2>&1 | tee -a "$LOG_FILE"

    # Copy theme files to interactive_reports
    if [ -d "dashboard_data/themes" ]; then
        print_info "Copying theme visualizations to dashboard..."
        cp dashboard_data/themes/*.png interactive_reports/data/themes/ 2>/dev/null || true
        cp dashboard_data/themes/*.json interactive_reports/data/themes/ 2>/dev/null || true
    fi

    # Copy UMAP visualizations if they exist
    if [ -f "dashboard_data/research_themes_umap.png" ]; then
        print_info "Copying UMAP visualizations..."
        cp dashboard_data/*umap*.png dashboard_data/visualizations/ 2>/dev/null || true
    fi

    # Validate output
    if [ -f "interactive_reports/dataset_citations_dashboard_nemar.html" ]; then
        print_status "Analysis completed successfully ✓"
        print_info "Dashboard: interactive_reports/dataset_citations_dashboard_nemar.html"
        print_info "Log file: $LOG_FILE"

        # Show dashboard stats
        ~/miniconda3/bin/conda run -n dataset-citations python -c "
import json
with open('dashboard_data/aggregated_data.json') as f:
    data = json.load(f)
    stats = data['summary_stats']
    print(f'')
    print(f'Dashboard Statistics:')
    print(f'  - Datasets analyzed: {stats[\"total_datasets\"]}')
    print(f'  - Total citations: {stats[\"total_citations\"]}')
    print(f'  - High-confidence citations: {stats[\"high_confidence_citations\"]}')
    print(f'  - Bridge papers: {stats[\"bridge_papers\"]}')
    print(f'  - Confidence threshold: {stats[\"confidence_threshold\"]}')

    # Check what analysis data was generated
    network = data.get('network_analysis', {})
    themes = data.get('theme_analysis', {})
    temporal = data.get('temporal_analysis', {})

    print(f'')
    print(f'Analysis Components:')
    print(f'  - Network analysis: {len(network)} components')
    print(f'  - Theme analysis: {len(themes)} components')
    print(f'  - Temporal analysis: {len(temporal)} components')
" 2>/dev/null || true
    else
        print_error "Dashboard generation failed"
        return 1
    fi
}

# Main execution
main() {
    print_status "Full Analysis Workflow"
    print_info "Generates all analysis components for complete dashboard"

    # Check conda environment
    if ! conda env list | grep -q "dataset-citations"; then
        print_error "Conda environment 'dataset-citations' not found"
        return 1
    fi

    run_full_analysis
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        print_status "Workflow completed successfully ✓"
    else
        print_error "Workflow failed with exit code: $EXIT_CODE"
    fi

    return $EXIT_CODE
}

# Run main function
main
exit $?