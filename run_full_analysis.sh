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
    if [ ! -d "citations/json" ]; then
        print_error "No citation data found. Run discovery and scraping first."
        return 1
    fi

    JSON_COUNT=$(find citations/json -name "*.json" 2>/dev/null | wc -l)
    print_info "Found $JSON_COUNT citation JSON files"

    # Clean up and prepare directories
    print_status "Step 1/8: Preparing directories..."
    rm -rf dashboard_data/network/*
    rm -rf dashboard_data/themes/*
    rm -rf dashboard_data/temporal/*
    rm -rf dashboard_data/visualizations/*
    rm -rf interactive_reports/data/*

    mkdir -p dashboard_data/{network,themes,temporal,visualizations}
    mkdir -p interactive_reports/data/themes

    # Generate embeddings (required for UMAP and theme analysis)
    print_status "Step 2/8: Generating embeddings..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-generate-embeddings \
        --citations citations/json \
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

    # Generate temporal themes with wordclouds
    print_status "Step 4/8: Generating theme analysis with wordclouds..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-analyze-temporal-themes \
        --embeddings-dir embeddings \
        --citations-dir citations/json \
        --output-dir dashboard_data/themes \
        --create-visualizations \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Theme analysis had issues"

    # Generate network analysis data (without Neo4j)
    print_status "Step 5/8: Generating network analysis data..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
import json
import csv
from pathlib import Path
from collections import defaultdict, Counter

# Prepare output directory
network_dir = Path('dashboard_data/network')
network_dir.mkdir(parents=True, exist_ok=True)

# Initialize data structures
author_datasets = defaultdict(set)
dataset_citations = defaultdict(int)
dataset_co_citations = defaultdict(int)
bridge_papers = []
multi_dataset_citations = []

# Process all citation files
citations_dir = Path('citations/json')
for json_file in citations_dir.glob('*.json'):
    dataset_id = json_file.stem.replace('_citations', '')

    with open(json_file) as f:
        data = json.load(f)
        citations = data.get('citation_details', [])
        dataset_citations[dataset_id] = len(citations)

        # Process each citation
        for citation in citations:
            if citation.get('confidence_score', 0) >= 0.4:
                # Track authors
                authors = citation.get('authors', '')
                if authors:
                    author_datasets[authors].add(dataset_id)

                # Check for multi-dataset citations (simplified)
                title = citation.get('title', '').lower()
                if any(term in title for term in ['multiple', 'comparison', 'benchmark', 'survey']):
                    multi_dataset_citations.append({
                        'title': citation.get('title'),
                        'datasets': dataset_id,
                        'confidence': citation.get('confidence_score')
                    })

# Identify bridge papers (papers citing multiple datasets)
for author, datasets in author_datasets.items():
    if len(datasets) > 1:
        bridge_papers.append({
            'author': author,
            'datasets_bridged': list(datasets),
            'num_datasets': len(datasets)
        })

# Save author influence data
with open(network_dir / 'author_influence.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['author', 'datasets_cited', 'num_datasets'])
    writer.writeheader()
    for author, datasets in author_datasets.items():
        writer.writerow({
            'author': author,
            'datasets_cited': ','.join(list(datasets)),
            'num_datasets': len(datasets)
        })

# Save bridge papers data
with open(network_dir / 'bridge_papers.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['author', 'datasets_bridged', 'num_datasets'])
    writer.writeheader()
    writer.writerows(bridge_papers[:80])  # Top 80 bridge papers

# Save dataset popularity
with open(network_dir / 'dataset_popularity.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['dataset_id', 'citation_count'])
    writer.writeheader()
    for dataset_id, count in sorted(dataset_citations.items(), key=lambda x: x[1], reverse=True):
        writer.writerow({'dataset_id': dataset_id, 'citation_count': count})

# Save multi-dataset citations
with open(network_dir / 'multi_dataset_citations.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['title', 'datasets', 'confidence'])
    writer.writeheader()
    writer.writerows(multi_dataset_citations[:100])

print(f'Generated network analysis data: {len(bridge_papers)} bridge papers identified')
" 2>&1 | tee -a "$LOG_FILE"

    # Generate temporal analysis
    print_status "Step 6/8: Generating temporal analysis..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
import json
import csv
from pathlib import Path
from collections import defaultdict

# Prepare output directory
temporal_dir = Path('dashboard_data/temporal')
temporal_dir.mkdir(parents=True, exist_ok=True)

# Initialize data structures
yearly_citations = defaultdict(int)
yearly_datasets = defaultdict(set)

# Process all citation files
citations_dir = Path('citations/json')
for json_file in citations_dir.glob('*.json'):
    dataset_id = json_file.stem.replace('_citations', '')

    with open(json_file) as f:
        data = json.load(f)
        citations = data.get('citation_details', [])

        for citation in citations:
            year = citation.get('year', 0)
            if year and year > 2000 and year < 2025:
                yearly_citations[year] += 1
                yearly_datasets[year].add(dataset_id)

# Save temporal summary
with open(temporal_dir / 'temporal_summary.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['year', 'total_citations', 'unique_datasets'])
    writer.writeheader()
    for year in sorted(yearly_citations.keys()):
        writer.writerow({
            'year': year,
            'total_citations': yearly_citations[year],
            'unique_datasets': len(yearly_datasets[year])
        })

# Save as JSON too
temporal_data = {
    'yearly_citations': dict(yearly_citations),
    'yearly_datasets': {str(k): len(v) for k, v in yearly_datasets.items()}
}

with open(temporal_dir / 'temporal_analysis.json', 'w') as f:
    json.dump(temporal_data, f, indent=2)

print(f'Generated temporal analysis data: {len(yearly_citations)} years of data')
" 2>&1 | tee -a "$LOG_FILE"

    # Aggregate all data
    print_status "Step 7/8: Aggregating data for dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.data.aggregator import DataAggregator
from pathlib import Path
import json

# Create aggregator
aggregator = DataAggregator(
    results_dir=Path('.'),
    citations_dir=Path('citations/json')
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
    results_dir=Path('.'),
    output_dir=Path('interactive_reports'),
    citations_dir=Path('citations/json')
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