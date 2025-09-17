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
# Quick tests
pytest tests/ -v

# With coverage
pytest --cov=dataset_citations tests/

# Specific test
pytest tests/test_integration_workflow.py -v
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