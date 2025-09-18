# Development Setup Guide

## Environment Setup

### Option 1: Update Existing Environment

If you have an existing conda environment, update it to Python 3.11:

```bash
conda activate dataset-citations
conda install python=3.11
pip install -e ".[dev,test]"
```

### Option 2: Create New Environment

Create a fresh environment with Python 3.11:

```bash
# Using conda
conda env create -f environment.yml

# Or manually
conda create -n dataset-citations python=3.11
conda activate dataset-citations
pip install -e ".[dev,test]"
```

### Option 3: Using venv

For those preferring venv:

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev,test]"
```

## Python Version Requirements

- **Minimum Python Version**: 3.11
- **Tested Versions**: 3.11, 3.12
- **Recommended Version**: 3.11 (most stable with all dependencies)

## Why Python 3.11+?

The project uses modern Python features including:
- Type union syntax with `|` operator
- Enhanced error messages
- Performance improvements
- Better async support

## Development Tools

After setting up your environment, ensure you have the development tools:

```bash
# Formatting and linting
pip install black ruff

# Testing
pip install pytest pytest-cov

# All dev dependencies
pip install -e ".[dev,test]"
```

## Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# The hook is already installed in .git/hooks/pre-commit
# It runs black and ruff on staged files

# To run manually
black src/ tests/
ruff check --fix src/ tests/
```

## Running Tests

```bash
# Quick tests (no API calls, < 5 seconds)
pytest tests/ -v

# With coverage
pytest --cov=dataset_citations --cov-report=term-missing tests/

# Specific test
pytest tests/test_integration_workflow.py -v

# End-to-end workflow tests
./run_end_to_end_workflow.sh test              # Test mode, no API calls
./run_end_to_end_workflow.sh full              # Full pipeline (recommended)
./run_end_to_end_workflow.sh local-ci-test     # Test CI/CD test workflow via Docker
./run_end_to_end_workflow.sh local-ci-update   # Test CI/CD update workflow via Docker
```

## Important Dependencies

### httpx Version Lock

**WARNING**: Do not upgrade httpx beyond version 0.27.0. There's a compatibility issue with the scholarly package that causes errors with newer versions.

```bash
# Correct version
pip install httpx==0.27.0

# DO NOT upgrade to latest
# pip install --upgrade httpx  # This will break scholarly!
```

If you accidentally upgrade httpx:
```bash
pip install httpx==0.27.0 --force-reinstall
```

## Workflow and CI/CD

### Workflow Modes

The `run_end_to_end_workflow.sh` script supports multiple modes:

- **test**: Quick validation with mock data (no API calls)
- **full**: Complete pipeline with real API calls (creates branch/PR)
- **local-ci-test**: Test GitHub Actions test workflow locally using `act`
- **local-ci-update**: Test GitHub Actions update workflow locally using `act`

### API Keys and Secrets

The workflow script now auto-loads credentials from `.secrets` file:

```bash
# Create .secrets file (auto-loaded by workflow)
cat > .secrets << EOF
SCRAPERAPI_KEY=your_key_here
GITHUB_TOKEN=your_token_here
EOF

# Or use environment variables
export SCRAPERAPI_KEY=your_key_here
export GITHUB_TOKEN=your_token_here
```

### Branch Protection

Both `full` and `local-ci-update` modes automatically:
1. Create a feature branch before making changes
2. Run the complete pipeline
3. Create a pull request for review

### PyTorch Installation

The project uses CPU-only PyTorch to avoid CUDA dependencies:

```bash
# Install CPU-only PyTorch (done automatically in CI/CD)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Troubleshooting

### ImportError with type unions

If you see errors like:
```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

This means you're using Python < 3.10. Update to Python 3.11+.

### Conda environment issues

To completely recreate the environment:

```bash
conda deactivate
conda env remove -n dataset-citations
conda create -n dataset-citations python=3.11
conda activate dataset-citations
pip install -e ".[dev,test]"
```