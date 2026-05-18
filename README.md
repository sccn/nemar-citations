# NEMAR Citations

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Tests](https://github.com/nemarOrg/nemar-citations/actions/workflows/test.yml/badge.svg)](https://github.com/nemarOrg/nemar-citations/actions)

Automated BIDS dataset citation tracking system with AI-powered confidence scoring for 300+ neuroscience datasets.

## Overview

Track and analyze citations for OpenNeuro datasets with a complete pipeline from discovery to interactive dashboards. Features Google Scholar integration, semantic similarity scoring, network analysis, and automated monthly updates via GitHub Actions.

**Key Features**: Dataset discovery • Citation tracking • AI confidence scoring • Network analysis • Interactive dashboards • JSON/CSV export • GitHub Actions automation

## Installation

```bash
git clone https://github.com/nemarOrg/nemar-citations.git
cd nemar-citations
pip install -e ".[dev,test]"
```

**Requirements**: Python 3.13+ • ScraperAPI key • GitHub token (optional)

## Quick Start

```bash
# 1. Setup environment (choose .env or .secrets)
# Option A: Using .env file
echo "SCRAPERAPI_KEY=your_key_here" > .env
echo "GITHUB_TOKEN=your_token_here" >> .env

# Option B: Using .secrets file (auto-loaded by workflow script)
echo "SCRAPERAPI_KEY=your_key_here" > .secrets
echo "GITHUB_TOKEN=your_token_here" >> .secrets

# 2. Run complete pipeline
chmod +x run_end_to_end_workflow.sh
./run_end_to_end_workflow.sh test              # Test mode (no API calls)
./run_end_to_end_workflow.sh full              # Full pipeline (recommended)
./run_end_to_end_workflow.sh local-ci-test     # Test CI/CD test workflow locally
./run_end_to_end_workflow.sh local-ci-update   # Test CI/CD update workflow locally
```

## Shell Scripts

The repository includes several shell scripts for different workflows:

| Script | Purpose | Runtime | When to Use |
|--------|---------|---------|-------------|
| `run_end_to_end_workflow.sh` | Complete pipeline from discovery to dashboard | 1-3 hours | Production updates, full analysis |
| `run_full_analysis.sh` | Analysis and dashboard generation only | 10-30 min | When citations already exist |
| `migrate_to_json.sh` | Convert pickle files to JSON format | 1-2 min | One-time migration |

## Pipeline Workflow

### Running the Complete Pipeline

The `run_end_to_end_workflow.sh` script automates the entire workflow:

| Mode | Description | Runtime | API Calls | Steps Executed | Branch/PR |
|------|-------------|---------|-----------|----------------|-----------|
| `test` | Controlled test data (3-8 citations) | ~1 min | None | 4-5 only (Analyze, Generate) | No |
| `full` | **Recommended**: Direct pipeline execution | 1-3 hours | Google Scholar, GitHub | 1-5 (All steps) | Yes (auto) |
| `local-ci-test` | Test GitHub Actions test workflow via Docker | ~5-10 min | None | Runs test suite | No |
| `local-ci-update` | Test GitHub Actions update workflow via Docker | ~10-30 min | Real API calls | 1-5 (All steps) | Yes (auto) |

**Workflow Steps**:
1. **Discover** → Find BIDS datasets (EEG/MEG/iEEG)
2. **Collect** → Fetch citations from Google Scholar
3. **Enhance** → Add metadata & AI confidence scores
4. **Analyze** → Network, temporal, theme analysis
5. **Generate** → Interactive HTML dashboard

**Mode Selection Guide**:
- Use `test` for quick validation during development
- Use `full` for actual citation updates (runs natively, faster)
- Use `local-ci-test` to test/debug GitHub Actions test workflow issues
- Use `local-ci-update` to test/debug GitHub Actions update workflow issues

**Branch Protection**: Both `full` and `local-ci-update` modes automatically create a feature branch and pull request to protect the main branch from direct commits.

### Automated Updates (Cron)

```bash
# 1. Create update script
cat > ~/update_citations.sh << 'EOF'
#!/bin/bash
cd /path/to/dataset_citations
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-citations
./run_end_to_end_workflow.sh full
EOF
chmod +x ~/update_citations.sh

# 2. Add to crontab (choose one)
crontab -e
0 2 1 * * ~/update_citations.sh >> ~/citations.log 2>&1  # Monthly
0 3 * * 0 ~/update_citations.sh >> ~/citations.log 2>&1  # Weekly
0 4 * * * ~/update_citations.sh >> ~/citations.log 2>&1  # Daily

# 3. Monitor
tail -f ~/citations.log
```

## Python API

```python
from dataset_citations.core import citation_utils
from dataset_citations.quality.confidence_scoring import CitationConfidenceScorer
from dataset_citations.quality.dataset_metadata import DatasetMetadataRetriever

# Convert pickle to JSON
json_path = citation_utils.migrate_pickle_to_json(
    'citations/pickle/ds002718.pkl', 
    'citations/json', 
    'ds002718'
)

# Load citation data
citations = citation_utils.load_citation_json(json_path)
print(f"Dataset {citations['dataset_id']} has {citations['num_citations']} citations")

# Calculate confidence scores
scorer = CitationConfidenceScorer()
confidence_scores = scorer.score_citations_for_dataset('ds002718', citations, dataset_metadata)

# Retrieve dataset metadata
retriever = DatasetMetadataRetriever()
metadata = retriever.get_dataset_metadata('ds002718')
```


## Key Commands

```bash
# Discovery & Updates
dataset-citations-discover                    # Find datasets
dataset-citations-update                      # Fetch citations
dataset-citations-migrate                     # Pickle→JSON

# Quality & Analysis
dataset-citations-retrieve-metadata           # Get GitHub data
dataset-citations-score-confidence            # AI scoring
dataset-citations-analyze-temporal            # Trends
dataset-citations-analyze-networks            # Networks

# Dashboards
dataset-citations-create-interactive-reports  # Generate HTML

# All commands support --help for detailed usage
```

## Data Formats

### JSON Output
```json
{
  "dataset_id": "ds002718",
  "num_citations": 13,
  "citation_details": [{
    "title": "Paper title",
    "author": "Authors",
    "year": 2021,
    "confidence_score": 0.82  // AI similarity score
  }]
}
```

### Confidence Scoring
AI-powered relevance scoring (0.0-1.0) using sentence transformers to compare dataset metadata with citation abstracts. Helps filter high-confidence citations and identify misattributions.

## Development

```bash
# Setup
git clone https://github.com/nemarOrg/nemar-citations.git
cd nemar-citations
conda create -n dataset-citations python=3.13
conda activate dataset-citations
pip install -e ".[dev,test]"

# Testing
pytest tests/ -v                    # Fast tests
pytest --cov=dataset_citations      # With coverage

# Code quality
ruff format src/ tests/             # Format
ruff check --fix src/ tests/        # Lint
```

## Architecture

**Core Components**:
- **Discovery**: Find BIDS datasets via GitHub API
- **Collection**: Google Scholar citation fetching with proxy rotation
- **Processing**: Parallel processing, format conversion, validation
- **Analysis**: Network graphs, temporal trends, theme clustering
- **Dashboard**: Interactive HTML with D3.js visualizations

**Data Flow**: Discovery → Fetching → Processing → Analysis → Dashboard


## Troubleshooting

| Issue | Solution |
|-------|----------|
| ScraperAPI key not found | Add `SCRAPERAPI_KEY` to `.env` |
| Google Scholar rate limit | Wait for proxy rotation |
| GitHub API rate limit | Add `GITHUB_TOKEN` to `.env` |
| MPS memory error (macOS) | Use `--device cpu` |
| Import errors | Reinstall: `pip install -e ".[dev,test]"` |

**Debug**: Add `--verbose` flag to any command

**Support**: [GitHub Issues](https://github.com/nemarOrg/nemar-citations/issues)

## Contributing

1. Fork & create feature branch
2. Make changes with tests
3. Run `pytest` and `ruff format`
4. Submit PR with issue reference

**Guidelines**: Type hints • Docstrings • Tests • No mocks

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) - Attribution, NonCommercial, ShareAlike

## Citation

If you use this software in your research, please cite:

```bibtex
@software{shirazi2025nemarcitations,
  title={NEMAR Citations: Automated BIDS Dataset Citation Tracking System},
  author={Shirazi, Seyed Yahya},
  year={2025},
  url={https://github.com/nemarOrg/nemar-citations},
  organization={Swartz Center for Computational Neuroscience (SCCN)}
}
```

## Acknowledgments

- **Author**: [Seyed Yahya Shirazi](https://github.com/neuromechanist)
- **Organization**: [Swartz Center for Computational Neuroscience (SCCN)](https://sccn.ucsd.edu/)
- **Project**: [NEMAR - NeuroElectroMagnetic Archive](https://nemar.org/)
- **GitHub**: [@neuromechanist](https://github.com/neuromechanist)

Built with ❤️ for NEMAR and the neuroscience open science community.

---

*Last updated: September 19, 2025*
