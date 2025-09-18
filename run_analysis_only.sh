#!/bin/zsh
#
# Streamlined analysis-only workflow for Dataset Citations
# This script runs only the analysis and dashboard generation
# (skips discovery and citation scraping which are time-consuming)
#
# Usage:
#   ./run_analysis_only.sh
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
LOG_FILE="${LOG_DIR}/analysis_${TIMESTAMP}.log"

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
run_analysis() {
    print_status "Starting streamlined analysis workflow..."

    # Check if we have citation data
    if [ ! -d "citations/json" ]; then
        print_error "No citation data found. Run full workflow first."
        return 1
    fi

    JSON_COUNT=$(find citations/json -name "*.json" 2>/dev/null | wc -l)
    print_info "Found $JSON_COUNT citation JSON files"

    # Clean up old analysis directories
    print_status "Step 1/5: Cleaning up old analysis outputs..."
    rm -rf dashboard_data/network/*
    rm -rf dashboard_data/themes/*
    rm -rf dashboard_data/temporal/*
    rm -rf dashboard_data/visualizations/*
    rm -rf interactive_reports/data/*

    # Ensure directories exist
    mkdir -p dashboard_data/{network,themes,temporal,visualizations}
    mkdir -p interactive_reports/data

    print_status "Step 2/5: Generating embeddings..."
    ~/miniconda3/bin/conda run -n dataset-citations dataset-citations-generate-embeddings \
        --citations citations/json \
        --datasets datasets \
        --embeddings-dir embeddings \
        --embedding-type both \
        --batch-size 32 \
        --verbose 2>&1 | tee -a "$LOG_FILE" || print_warning "Some embeddings may have failed"

    print_status "Step 3/5: Analyzing themes and generating wordclouds..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from pathlib import Path
import json
import numpy as np
from sklearn.cluster import KMeans
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
import pickle

# Load embeddings
embeddings_dir = Path('embeddings')
citation_embeddings = []
citation_texts = []

# Collect all citation texts and embeddings
for json_file in Path('citations/json').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
        citations = data.get('citation_details', [])
        for citation in citations:
            if citation.get('confidence_score', 0) >= 0.4:
                title = citation.get('title', '')
                if title:
                    citation_texts.append(title)

print(f'Collected {len(citation_texts)} high-confidence citations')

if len(citation_texts) > 0:
    # Generate embeddings if needed
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(citation_texts)

    # Cluster into themes
    n_clusters = min(4, len(citation_texts) // 10)  # 4 themes or fewer
    if n_clusters > 1:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(embeddings)

        # Generate wordclouds for each theme
        themes_dir = Path('dashboard_data/themes')
        themes_dir.mkdir(parents=True, exist_ok=True)

        theme_data = {'themes': []}

        for i in range(n_clusters):
            theme_texts = [citation_texts[j] for j in range(len(citation_texts)) if labels[j] == i]
            if theme_texts:
                # Combine texts for wordcloud
                combined_text = ' '.join(theme_texts)

                # Generate wordcloud
                wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_text)

                # Save wordcloud
                plt.figure(figsize=(10, 5))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                plt.tight_layout()
                plt.savefig(themes_dir / f'theme_{i}_wordcloud.png', dpi=100, bbox_inches='tight')
                plt.close()

                # Add to theme data
                theme_data['themes'].append({
                    'id': i,
                    'size': len(theme_texts),
                    'top_words': list(wordcloud.words_.keys())[:10]
                })

                print(f'Generated wordcloud for theme {i} ({len(theme_texts)} citations)')

        # Save theme analysis
        with open(themes_dir / 'comprehensive_theme_analysis.json', 'w') as f:
            json.dump(theme_data, f, indent=2)
    else:
        print('Not enough data for clustering')
else:
    print('No high-confidence citations found for theme analysis')
" 2>&1 | tee -a "$LOG_FILE" || print_warning "Theme analysis had issues"

    print_status "Step 4/5: Aggregating data for dashboard..."
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
" 2>&1 | tee -a "$LOG_FILE"

    print_status "Step 5/5: Generating dashboard..."
    ~/miniconda3/bin/conda run -n dataset-citations python -c "
from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path('.'),
    output_dir=Path('interactive_reports')
)

output_path = gen.generate_dashboard(dashboard_type='nemar', lazy_load=True)
print(f'Dashboard generated: {output_path}')
" 2>&1 | tee -a "$LOG_FILE"

    # Copy theme files to interactive_reports
    if [ -d "dashboard_data/themes" ]; then
        print_info "Copying theme visualizations to dashboard..."
        mkdir -p interactive_reports/data/themes
        cp dashboard_data/themes/* interactive_reports/data/themes/ 2>/dev/null || true
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
    print(f'  - Confidence threshold: {stats[\"confidence_threshold\"]}')
" 2>/dev/null || true
    else
        print_error "Dashboard generation failed"
        return 1
    fi
}

# Main execution
main() {
    print_status "Streamlined Analysis Workflow"
    print_info "This skips discovery and scraping, only runs analysis"

    # Check conda environment
    if ! conda env list | grep -q "dataset-citations"; then
        print_error "Conda environment 'dataset-citations' not found"
        return 1
    fi

    run_analysis
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