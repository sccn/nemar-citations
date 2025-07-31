# Dataset Citations CLI Reference

This document provides comprehensive documentation for all CLI commands available in the dataset-citations package.

## Installation

After installing the package with `pip install -e .`, all CLI commands are available as entry points:

```bash
dataset-citations-discover --help
dataset-citations-update --help
dataset-citations-migrate --help
dataset-citations-retrieve-metadata --help
dataset-citations-score-confidence --help
dataset-citations-regenerate --help
```

## Command Reference

### `dataset-citations-discover`

**Purpose**: Automatically discover BIDS datasets from OpenNeuro GitHub organization that contain EEG, iEEG, or MEG data.

**Usage**:
```bash
dataset-citations-discover [OPTIONS]
```

**Options**:
- `--output-file TEXT`: Output file for discovered dataset IDs (default: `discovered_datasets.txt`)
- `--search-terms TEXT`: Comma-separated BIDS modalities to search for (default: `eeg,ieeg,meg`)
- `--limit INTEGER`: Maximum number of datasets to discover
- `--github-token TEXT`: GitHub API token for higher rate limits
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Basic usage - discover EEG, iEEG, MEG datasets
dataset-citations-discover

# Custom output file and modalities
dataset-citations-discover --output-file my_datasets.txt --search-terms "eeg,meg"

# Limit discovery to 50 datasets with GitHub token
dataset-citations-discover --limit 50 --github-token $GITHUB_TOKEN
```

---

### `dataset-citations-update`

**Purpose**: Update citation counts and detailed citation information for specified datasets using Google Scholar.

**Usage**:
```bash
dataset-citations-update [OPTIONS]
```

**Options**:
- `--dataset-list-file TEXT`: File containing dataset IDs to process
- `--previous-citations-file TEXT`: CSV file with previous citation counts
- `--output-dir TEXT`: Directory to save citation files (default: `citations/`)
- `--output-format [pickle|json|both]`: Output format (default: `both`)
- `--workers INTEGER`: Number of parallel workers (default: 5)
- `--no-update-num-cites`: Skip citation count updates
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Basic usage with JSON output only
dataset-citations-update \
    --dataset-list-file discovered_datasets.txt \
    --previous-citations-file citations/previous_citations.csv \
    --output-format json

# Parallel processing with 3 workers
dataset-citations-update \
    --dataset-list-file datasets.txt \
    --workers 3 \
    --verbose

# Skip citation count updates (only get detailed citations)
dataset-citations-update \
    --dataset-list-file datasets.txt \
    --no-update-num-cites
```

---

### `dataset-citations-migrate`

**Purpose**: Convert legacy pickle citation files to modern JSON format.

**Usage**:
```bash
dataset-citations-migrate [OPTIONS]
```

**Options**:
- `--input-dir TEXT`: Directory containing pickle files (default: `citations/pickle/`)
- `--output-dir TEXT`: Directory to save JSON files (default: `citations/json/`)
- `--overwrite`: Overwrite existing JSON files
- `--dataset-id TEXT`: Process specific dataset only
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Migrate all pickle files to JSON
dataset-citations-migrate

# Migrate with custom directories and overwrite
dataset-citations-migrate \
    --input-dir /path/to/pickle \
    --output-dir /path/to/json \
    --overwrite

# Migrate specific dataset only
dataset-citations-migrate --dataset-id ds002718
```

---

### `dataset-citations-retrieve-metadata`

**Purpose**: Retrieve dataset descriptions and README files from GitHub for use in confidence scoring.

**Usage**:
```bash
dataset-citations-retrieve-metadata [OPTIONS]
```

**Options**:
- `--citations-dir TEXT`: Directory containing citation JSON files
- `--output-dir TEXT`: Directory to save metadata files (default: `datasets/`)
- `--dataset-ids TEXT [TEXT ...]`: Specific dataset IDs to process (space-separated)
- `--github-token TEXT`: GitHub API token for authentication
- `--force-update`: Update metadata even if files exist
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Retrieve metadata for all datasets with citations
dataset-citations-retrieve-metadata \
    --citations-dir citations/json \
    --output-dir datasets

# Retrieve metadata for specific datasets
dataset-citations-retrieve-metadata \
    --citations-dir citations/json \
    --dataset-ids ds002718 ds000117 ds000246

# Force update existing metadata files
dataset-citations-retrieve-metadata \
    --citations-dir citations/json \
    --force-update \
    --github-token $GITHUB_TOKEN
```

---

### `dataset-citations-score-confidence`

**Purpose**: Calculate AI-powered confidence scores for citations using semantic similarity between dataset metadata and citation content.

**Usage**:
```bash
dataset-citations-score-confidence [OPTIONS]
```

**Options**:
- `--citations-dir TEXT`: Directory containing citation JSON files
- `--datasets-dir TEXT`: Directory containing dataset metadata files
- `--output-dir TEXT`: Directory to save confidence scores (default: `confidence_scores/`)
- `--model-name TEXT`: Sentence transformer model (default: `Qwen/Qwen3-Embedding-0.6B`)
- `--device [mps|auto|cpu|cuda]`: Computing device to use (default: `mps`)
- `--dataset-ids TEXT [TEXT ...]`: Specific dataset IDs to process
- `--threshold FLOAT`: Confidence threshold for reporting (default: 0.0)
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Basic confidence scoring with default settings
dataset-citations-score-confidence \
    --citations-dir citations/json \
    --datasets-dir datasets

# Use CPU device and specific datasets
dataset-citations-score-confidence \
    --citations-dir citations/json \
    --datasets-dir datasets \
    --device cpu \
    --dataset-ids ds002718 ds000117

# Custom model and threshold
dataset-citations-score-confidence \
    --citations-dir citations/json \
    --datasets-dir datasets \
    --model-name "all-MiniLM-L6-v2" \
    --threshold 0.5 \
    --verbose
```

---

### `dataset-citations-regenerate`

**Purpose**: Generate CSV summary files from JSON citation data for analysis and reporting.

**Usage**:
```bash
dataset-citations-regenerate [OPTIONS]
```

**Options**:
- `--json-dir TEXT`: Directory containing JSON citation files (default: `citations/json/`)
- `--output-file TEXT`: Output CSV file path (default: `citations/regenerated_citations.csv`)
- `--include-confidence`: Include confidence scores in CSV output
- `--verbose`: Enable verbose logging
- `--help`: Show help message

**Examples**:
```bash
# Basic CSV regeneration
dataset-citations-regenerate

# Custom paths with confidence scores
dataset-citations-regenerate \
    --json-dir citations/json \
    --output-file reports/current_citations.csv \
    --include-confidence

# Verbose output for debugging
dataset-citations-regenerate --verbose
```

## Common Workflows

### Full Pipeline (New Project)

```bash
# 1. Discover datasets
dataset-citations-discover --output-file datasets.txt

# 2. Update citations
dataset-citations-update \
    --dataset-list-file datasets.txt \
    --output-format json

# 3. Retrieve metadata for confidence scoring
dataset-citations-retrieve-metadata \
    --citations-dir citations/json \
    --output-dir datasets

# 4. Calculate confidence scores
dataset-citations-score-confidence \
    --citations-dir citations/json \
    --datasets-dir datasets

# 5. Generate summary report
dataset-citations-regenerate \
    --include-confidence \
    --output-file reports/analysis.csv
```

### Legacy Data Migration

```bash
# 1. Migrate existing pickle files
dataset-citations-migrate \
    --input-dir citations/pickle \
    --output-dir citations/json \
    --overwrite

# 2. Regenerate CSV from migrated JSON
dataset-citations-regenerate \
    --json-dir citations/json \
    --output-file citations/migrated_citations.csv
```

### Confidence Scoring Update

```bash
# 1. Update metadata for existing datasets
dataset-citations-retrieve-metadata \
    --citations-dir citations/json \
    --force-update

# 2. Recalculate confidence scores
dataset-citations-score-confidence \
    --citations-dir citations/json \
    --datasets-dir datasets \
    --threshold 0.3
```

## Environment Variables

Set these in your `.env` file:

```bash
# Required for citation updates
SCRAPERAPI_KEY=your_scraperapi_key_here

# Required for metadata retrieval and better GitHub API limits
GITHUB_TOKEN=your_github_token_here
```

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Install with `pip install -e .`
2. **API rate limits**: Add GitHub token to `.env` file
3. **Memory issues**: Use `--device cpu` for confidence scoring
4. **Permission errors**: Check write permissions on output directories

### Debug Mode

Add `--verbose` to any command for detailed logging:

```bash
dataset-citations-update --verbose --workers 1
dataset-citations-score-confidence --verbose --device cpu
```

## Performance Tips

1. **Parallel Processing**: Adjust `--workers` based on your system (default: 5)
2. **Device Selection**: Use `--device mps` on Apple Silicon, `--device cuda` on NVIDIA GPUs
3. **Batch Processing**: Process datasets in smaller batches if memory is limited
4. **API Limits**: Use GitHub token to avoid rate limiting during metadata retrieval

## Output Files

- **Discovery**: Text file with dataset IDs (one per line)
- **Citations**: JSON files with citation data and metadata
- **Metadata**: JSON files with dataset descriptions and README content
- **Confidence**: JSON files with similarity scores for each citation
- **CSV Reports**: Tabular summary data for analysis

For more information, see the main [README.md](README.md) or use `--help` with any command.