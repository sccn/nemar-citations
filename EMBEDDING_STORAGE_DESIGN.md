# Embedding Storage System Design

## Overview
Design for persistent embedding storage with uniqueness tracking, version control, and obsolescence detection for the BIDS dataset citation system.

## Directory Structure

```
embeddings/
├── dataset_embeddings/          # Dataset metadata embeddings
│   ├── ds000117_v1_20250801.pkl    # versioned embedding files
│   ├── ds000117_v2_20250815.pkl    # updated version after metadata change
│   └── ds000246_v1_20250801.pkl
├── citation_embeddings/         # Citation text embeddings  
│   ├── citation_12345_v1_20250801.pkl
│   └── citation_67890_v1_20250801.pkl
├── composite_embeddings/        # Combined dataset+citation embeddings
│   └── confidence_pairs/
│       ├── ds000117_cite12345_v1.pkl
│       └── ds000246_cite67890_v1.pkl
├── metadata/                    # Embedding metadata tracking
│   ├── embedding_registry.json     # master registry of all embeddings
│   ├── dataset_metadata_hashes.json # track dataset metadata changes
│   └── citation_content_hashes.json # track citation content changes
└── analysis/                    # Analysis-specific embeddings
    ├── umap_projections/
    │   ├── citation_umap_2d_v1.pkl
    │   └── dataset_umap_2d_v1.pkl
    └── clustering/
        ├── citation_clusters_v1.pkl
        └── theme_labels_v1.json
```

## Unique ID System

### Dataset Embedding IDs
Format: `{dataset_id}_v{version}_{date}`
- `dataset_id`: BIDS dataset identifier (e.g., ds000117)
- `version`: Incremental version number starting from 1
- `date`: Creation date in YYYYMMDD format

Example: `ds000117_v1_20250801.pkl`

### Citation Embedding IDs  
Format: `citation_{hash}_v{version}_{date}`
- `hash`: SHA256 hash of citation title + abstract (first 8 characters)
- `version`: Version number for same citation content
- `date`: Creation date

Example: `citation_a1b2c3d4_v1_20250801.pkl`

### Composite Embedding IDs
Format: `{dataset_id}_cite{citation_hash}_v{version}`
- Links dataset and citation embeddings for confidence scoring
- Tracks the pairing relationship and confidence calculation version

Example: `ds000117_citea1b2c3d4_v1.pkl`

## Embedding Registry System

### Master Registry (`embedding_registry.json`)
```json
{
  "datasets": {
    "ds000117": {
      "current_version": 2,
      "embeddings": [
        {
          "version": 1,
          "file": "ds000117_v1_20250801.pkl",
          "created": "2025-08-01T10:30:00Z",
          "content_hash": "abc123...",
          "metadata_sources": ["dataset_description.json", "README.md"],
          "model": "Qwen/Qwen3-Embedding-0.6B",
          "status": "obsolete",
          "obsoleted_by": "ds000117_v2_20250815.pkl",
          "obsoleted_reason": "dataset metadata updated"
        },
        {
          "version": 2,
          "file": "ds000117_v2_20250815.pkl", 
          "created": "2025-08-15T14:20:00Z",
          "content_hash": "def456...",
          "metadata_sources": ["dataset_description.json", "README.md"],
          "model": "Qwen/Qwen3-Embedding-0.6B",
          "status": "current"
        }
      ]
    }
  },
  "citations": {
    "a1b2c3d4": {
      "current_version": 1,
      "title": "Neural correlates of face processing...",
      "embeddings": [
        {
          "version": 1,
          "file": "citation_a1b2c3d4_v1_20250801.pkl",
          "created": "2025-08-01T10:30:00Z",
          "content_hash": "xyz789...",
          "text_sources": ["title", "abstract"],
          "model": "Qwen/Qwen3-Embedding-0.6B",
          "status": "current"
        }
      ]
    }
  },
  "analysis": {
    "umap_projections": [
      {
        "file": "citation_umap_2d_v1.pkl",
        "created": "2025-08-01T15:00:00Z",
        "input_embeddings": ["citation_a1b2c3d4_v1", "citation_e5f6g7h8_v1"],
        "umap_params": {"n_components": 2, "n_neighbors": 15, "min_dist": 0.1},
        "status": "current"
      }
    ]
  }
}
```

### Content Hash Tracking
Track changes in source content to detect when embeddings need updates:

**Dataset Metadata Hashes (`dataset_metadata_hashes.json`):**
```json
{
  "ds000117": {
    "current_hash": "abc123...",
    "last_checked": "2025-08-15T14:20:00Z",
    "content_sources": {
      "dataset_description.json": "def456...",
      "README.md": "ghi789..."
    },
    "history": [
      {
        "hash": "old123...",
        "date": "2025-08-01T10:30:00Z",
        "change_reason": "initial creation"
      }
    ]
  }
}
```

## Obsolescence Detection System

### Automated Change Detection
1. **Regular content monitoring**: Check for changes in dataset metadata and citation content
2. **Hash comparison**: Compare current content hashes with stored hashes
3. **Dependency tracking**: Identify which embeddings depend on changed content
4. **Cascade updates**: Mark dependent embeddings as obsolete when source content changes

### Update Triggers
- **Dataset metadata changes**: New commits to dataset repositories
- **Citation updates**: New citation data or corrections to existing citations
- **Model updates**: Migration to newer embedding models
- **Analysis parameter changes**: Different UMAP parameters, clustering settings

### Cleanup Policy
- **Immediate obsolescence**: Mark as obsolete when source content changes
- **Grace period**: Keep obsolete embeddings for 30 days for rollback
- **Archive policy**: Move old embeddings to archive after 90 days
- **Selective cleanup**: Keep embeddings referenced in published analyses

## Integration with Existing System

### Citation JSON Linking
Add embedding references to existing citation JSON files:

```json
{
  "dataset_id": "ds000117",
  "embeddings": {
    "dataset_embedding": {
      "file": "embeddings/dataset_embeddings/ds000117_v2_20250815.pkl",
      "version": 2,
      "content_hash": "def456...",
      "created": "2025-08-15T14:20:00Z"
    }
  },
  "citation_details": [
    {
      "title": "Neural correlates...",
      "confidence_score": 0.85,
      "embeddings": {
        "citation_embedding": {
          "file": "embeddings/citation_embeddings/citation_a1b2c3d4_v1_20250801.pkl",
          "content_hash": "xyz789...",
          "created": "2025-08-01T10:30:00Z"
        },
        "confidence_embedding": {
          "file": "embeddings/composite_embeddings/confidence_pairs/ds000117_citea1b2c3d4_v1.pkl",
          "confidence_score": 0.85,
          "created": "2025-08-01T10:30:00Z"
        }
      }
    }
  ]
}
```

### CLI Integration
New CLI commands for embedding management:

```bash
# Generate embeddings for all datasets/citations
dataset-citations-generate-embeddings

# Check for obsolete embeddings
dataset-citations-check-embedding-health

# Update embeddings for changed content  
dataset-citations-update-embeddings --dataset ds000117

# Clean up obsolete embeddings
dataset-citations-cleanup-embeddings --older-than 90d

# UMAP analysis using stored embeddings
dataset-citations-umap-analysis --output results/umap_analysis/
```

## Performance Considerations

### Lazy Loading
- Load embeddings only when needed for analysis
- Cache frequently accessed embeddings in memory
- Use memory mapping for large embedding files

### Parallel Processing
- Generate embeddings in parallel for multiple items
- Use batch processing for efficiency
- Queue-based system for background embedding updates

### Storage Optimization
- Compress embedding files (pickle with compression)
- Deduplicate identical embeddings (rare but possible)
- Archive old embeddings to reduce active storage

## Future Extensions

### Advanced Versioning
- Git-like branching for experimental embedding approaches
- Tagging system for stable embedding versions
- Diff capabilities for comparing embedding versions

### Multi-Model Support
- Support for multiple embedding models simultaneously
- A/B testing framework for comparing embedding approaches
- Migration utilities for switching between models

### Distributed Storage
- Cloud storage integration for large embedding collections
- Distributed caching for multi-user access
- Remote computation for embedding generation

## Implementation Priority

1. **Phase 1**: Basic embedding storage and registry system
2. **Phase 2**: Obsolescence detection and automatic updates
3. **Phase 3**: UMAP integration and analysis pipeline
4. **Phase 4**: Performance optimization and cleanup automation
5. **Phase 5**: Advanced versioning and multi-model support