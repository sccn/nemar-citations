# JSON Citation Format Documentation

## Overview

This document describes the new JSON-based citation format implemented to replace pickle files for easier downstream processing and web integration. The JSON format provides structured, human-readable citation data that can be easily consumed by web applications, APIs, and other downstream systems.

## Motivation

The previous pickle-based format had several limitations:
- **Binary format**: Requires Python to read, not accessible to web applications
- **Manual processing**: Difficult to extract information for website updates
- **Limited interoperability**: Cannot be easily consumed by non-Python systems
- **Maintenance overhead**: Requires specialized tools to inspect or modify data

The new JSON format addresses these issues by providing:
- **Universal accessibility**: Can be read by any programming language or web browser
- **Human-readable**: Easy to inspect, debug, and manually modify if needed
- **Web-friendly**: Direct integration with JavaScript applications and APIs
- **Structured**: Well-defined schema with consistent field types

## JSON Schema

### File Naming Convention
Citation JSON files follow the naming pattern: `<dataset_id>_citations.json`

Examples:
- `ds000117_citations.json`
- `ds003374_citations.json`

### JSON Structure

```json
{
  "dataset_id": "string",
  "num_citations": "integer",
  "date_last_updated": "ISO 8601 timestamp",
  "metadata": {
    "total_cumulative_citations": "integer",
    "fetch_date": "ISO 8601 timestamp", 
    "processing_version": "string"
  },
  "citation_details": [
    {
      "title": "string",
      "author": "string",
      "venue": "string", 
      "year": "integer",
      "url": "string",
      "cited_by": "integer",
      "bib": {
        "title": "string",
        "author": "string",
        "venue": "string",
        "pub_year": "integer",
        // ... additional bibliographic fields
      }
    }
  ]
}
```

### Field Descriptions

#### Root Level Fields

- **`dataset_id`** (string): The BIDS dataset identifier (e.g., "ds000117")
- **`num_citations`** (integer): Total number of citations found for this dataset
- **`date_last_updated`** (string): ISO 8601 timestamp when the data was last updated
- **`metadata`** (object): Additional processing information
- **`citation_details`** (array): List of individual citation objects

#### Metadata Object

- **`total_cumulative_citations`** (integer): Sum of all `cited_by` values from citation details
- **`fetch_date`** (string): ISO 8601 timestamp when the data was originally fetched
- **`processing_version`** (string): Version of the processing pipeline used

#### Citation Detail Object

- **`title`** (string): Title of the citing paper
- **`author`** (string): Comma-separated list of authors
- **`venue`** (string): Publication venue (journal, conference, etc.)
- **`year`** (integer): Publication year
- **`url`** (string): URL to the paper (if available)
- **`cited_by`** (integer): Number of times this paper has been cited
- **`bib`** (object): Raw bibliographic data with additional fields

## Example JSON File

```json
{
  "dataset_id": "ds000117",
  "num_citations": 25,
  "date_last_updated": "2025-01-09T15:30:45Z",
  "metadata": {
    "total_cumulative_citations": 1250,
    "fetch_date": "2025-01-09T15:30:45Z",
    "processing_version": "1.0"
  },
  "citation_details": [
    {
      "title": "A multimodal dataset for various neuroimaging techniques",
      "author": "Wakeman, D.G., Henson, R.N.",
      "venue": "Scientific Data",
      "year": 2015,
      "url": "https://www.nature.com/articles/sdata201515",
      "cited_by": 89,
      "bib": {
        "title": "A multimodal dataset for various neuroimaging techniques",
        "author": "Wakeman, D.G., Henson, R.N.",
        "venue": "Scientific Data",
        "pub_year": 2015,
        "journal": "Scientific Data",
        "volume": "2",
        "pages": "150001"
      }
    },
    {
      "title": "Analysis of face processing using MEG and EEG",
      "author": "Smith, J., Johnson, A., Brown, K.",
      "venue": "NeuroImage", 
      "year": 2018,
      "url": "https://example.com/paper2",
      "cited_by": 42,
      "bib": {
        "title": "Analysis of face processing using MEG and EEG",
        "author": "Smith, J., Johnson, A., Brown, K.",
        "venue": "NeuroImage",
        "pub_year": 2018,
        "journal": "NeuroImage"
      }
    }
  ]
}
```

## Usage Examples

### Reading Citation Data (JavaScript)

```javascript
// Fetch citation data
fetch('citations/ds000117_citations.json')
  .then(response => response.json())
  .then(data => {
    console.log(`Dataset: ${data.dataset_id}`);
    console.log(`Citations: ${data.num_citations}`);
    console.log(`Last updated: ${data.date_last_updated}`);
    
    // Process citations
    data.citation_details.forEach(citation => {
      console.log(`${citation.title} (${citation.year}) - ${citation.cited_by} citations`);
    });
  });
```

### Reading Citation Data (Python)

```python
import json

# Load citation data
with open('citations/ds000117_citations.json', 'r') as f:
    citation_data = json.load(f)

print(f"Dataset: {citation_data['dataset_id']}")
print(f"Citations: {citation_data['num_citations']}")
print(f"Total cumulative citations: {citation_data['metadata']['total_cumulative_citations']}")

# Process citations
for citation in citation_data['citation_details']:
    print(f"{citation['title']} ({citation['year']}) - {citation['cited_by']} citations")
```

### Creating Summary Statistics

```python
import json
import glob

# Process all citation JSON files
total_datasets = 0
total_citations = 0
total_cumulative_citations = 0

for json_file in glob.glob('citations/*_citations.json'):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    total_datasets += 1
    total_citations += data['num_citations']
    total_cumulative_citations += data['metadata']['total_cumulative_citations']

print(f"Total datasets: {total_datasets}")
print(f"Total citations: {total_citations}")
print(f"Total cumulative citations: {total_cumulative_citations}")
```

## Tools and Scripts

### Migration from Pickle Files

Use the provided migration script to convert existing pickle files:

```bash
# Migrate all pickle files to JSON
python migrate_pickle_to_json.py

# Migrate with custom directories
python migrate_pickle_to_json.py --input-dir old_citations --output-dir new_citations

# Overwrite existing JSON files
python migrate_pickle_to_json.py --overwrite

# Dry run to see what would be migrated
python migrate_pickle_to_json.py --dry-run
```

### Citation Update with JSON Output

The main citation update script now supports JSON output:

```bash
# Generate only JSON files
dataset-citations-update \
  --dataset-list-file datasets.txt \
  --previous-citations-file previous.csv \
  --output-format json

# Generate both pickle and JSON files
dataset-citations-update \
  --dataset-list-file datasets.txt \
  --previous-citations-file previous.csv \
  --output-format both

# Generate only pickle files (legacy mode)
dataset-citations-update \
  --dataset-list-file datasets.txt \
  --previous-citations-file previous.csv \
  --output-format pickle
```

### Testing the JSON Format

Validate the JSON implementation:

```bash
python test_json_citations.py
```

This script tests:
- JSON structure creation
- File save/load operations
- Empty DataFrame handling
- JSON serialization
- Pickle to JSON migration

## Implementation Details

### Citation Utilities Module

The `citation_utils.py` module provides the following functions:

- **`create_citation_json_structure()`**: Convert DataFrame to JSON structure
- **`save_citation_json()`**: Save citation data as JSON file
- **`load_citation_json()`**: Load citation data from JSON file
- **`migrate_pickle_to_json()`**: Convert pickle file to JSON format
- **`get_citation_summary_from_json()`**: Extract summary from JSON file

### Data Type Handling

The JSON format handles various data types and edge cases:

- **Missing values**: Converted to "n/a" for strings, 0 for integers
- **NaN values**: Properly handled and converted to appropriate defaults
- **Complex bib data**: Cleaned and converted to JSON-serializable format
- **Date timestamps**: ISO 8601 format with timezone information

### Backward Compatibility

The new JSON format is designed to coexist with the existing pickle format:

- Both formats can be generated simultaneously
- Existing scripts that use pickle files continue to work
- Migration tools allow gradual transition
- No breaking changes to existing APIs

## Web Integration Examples

### REST API Endpoint

```python
from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

@app.route('/api/citations/<dataset_id>')
def get_citations(dataset_id):
    json_file = f'citations/{dataset_id}_citations.json'
    
    if not os.path.exists(json_file):
        return jsonify({'error': 'Dataset not found'}), 404
    
    with open(json_file, 'r') as f:
        citation_data = json.load(f)
    
    return jsonify(citation_data)

@app.route('/api/citations/<dataset_id>/summary')
def get_citation_summary(dataset_id):
    json_file = f'citations/{dataset_id}_citations.json'
    
    if not os.path.exists(json_file):
        return jsonify({'error': 'Dataset not found'}), 404
    
    with open(json_file, 'r') as f:
        citation_data = json.load(f)
    
    summary = {
        'dataset_id': citation_data['dataset_id'],
        'num_citations': citation_data['num_citations'],
        'total_cumulative_citations': citation_data['metadata']['total_cumulative_citations'],
        'last_updated': citation_data['date_last_updated']
    }
    
    return jsonify(summary)
```

### Frontend Widget

```html
<!DOCTYPE html>
<html>
<head>
    <title>Dataset Citations</title>
</head>
<body>
    <div id="citation-widget">
        <h3>Dataset Citations</h3>
        <div id="citation-info"></div>
        <ul id="citation-list"></ul>
    </div>

    <script>
    async function loadCitations(datasetId) {
        const response = await fetch(`citations/${datasetId}_citations.json`);
        const data = await response.json();
        
        // Update summary info
        document.getElementById('citation-info').innerHTML = `
            <p><strong>Dataset:</strong> ${data.dataset_id}</p>
            <p><strong>Citations:</strong> ${data.num_citations}</p>
            <p><strong>Last Updated:</strong> ${new Date(data.date_last_updated).toLocaleDateString()}</p>
        `;
        
        // Update citation list
        const citationList = document.getElementById('citation-list');
        citationList.innerHTML = data.citation_details.map(citation => `
            <li>
                <strong>${citation.title}</strong><br>
                ${citation.author} (${citation.year})<br>
                <em>${citation.venue}</em> - ${citation.cited_by} citations
                ${citation.url !== 'n/a' ? `<br><a href="${citation.url}">Read paper</a>` : ''}
            </li>
        `).join('');
    }
    
    // Load citations for ds000117
    loadCitations('ds000117');
    </script>
</body>
</html>
```

## Performance Considerations

### File Size Comparison

JSON files are typically:
- **Larger than pickle files** (20-40% increase due to text format)
- **More compressible** (JSON compresses well with gzip)
- **Faster to parse** for web applications
- **More cacheable** by web browsers and CDNs

### Optimization Tips

1. **Compression**: Enable gzip compression for JSON files when served over HTTP
2. **Caching**: JSON files can be cached more effectively than pickle files
3. **Partial Loading**: Large JSON files can be streamed or partially loaded
4. **CDN Friendly**: JSON files work well with Content Delivery Networks

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `citation_utils.py` is in the Python path
2. **Permission errors**: Check file permissions for output directories
3. **JSON validation errors**: Use JSON validators to check file format
4. **Character encoding**: JSON files use UTF-8 encoding

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Validation

Validate JSON files:

```bash
# Check JSON syntax
python -m json.tool citations/ds000117_citations.json

# Run tests
python test_json_citations.py
```

## Migration Guide

### Step 1: Test the New Format

```bash
# Run tests to ensure everything works
python test_json_citations.py

# Migrate a few files for testing
python migrate_pickle_to_json.py --dry-run
```

### Step 2: Update Scripts

Modify your scripts to use the new JSON format:

```python
# Old way (pickle)
import pandas as pd
citations_df = pd.read_pickle('citations/ds000117.pkl')

# New way (JSON)
import citation_utils
citation_data = citation_utils.load_citation_json('citations/ds000117_citations.json')
```

### Step 3: Full Migration

```bash
# Migrate all pickle files
python migrate_pickle_to_json.py --overwrite

# Update the workflow to use JSON
# (This is already done in the workflow file)
```

### Step 4: Update Downstream Systems

Update your web applications, APIs, and other systems to consume the JSON format instead of pickle files.

## Future Considerations

### Schema Evolution

The JSON schema is versioned (currently v1.0) to allow for future enhancements:

- Additional metadata fields
- Extended citation information
- Better bibliographic data structure
- Enhanced web-specific optimizations

### Potential Enhancements

1. **Schema validation**: Add JSON Schema validation
2. **Compressed formats**: Support for compressed JSON variants
3. **Streaming support**: For very large citation datasets
4. **API integration**: Direct API endpoints for citation data
5. **Real-time updates**: WebSocket support for live citation updates

## Support

For questions or issues with the JSON citation format:

1. Run the test script: `python test_json_citations.py`
2. Check the migration report: Look for `migration_report.txt` in the output directory
3. Enable debug logging for detailed error information
4. Validate JSON files using standard JSON tools

---

*This documentation covers the JSON citation format implementation for the BIDS dataset citation tracking system. For general usage of the citation system, see the main README.md file.* 