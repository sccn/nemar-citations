"""
Citation quality and confidence scoring functionality.

This module contains Phase 3 features including:
- Citation-to-dataset relevance scoring
- Confidence score calculation
- Sentence-transformers integration
- Metadata retrieval and comparison
"""

from .dataset_metadata import (
    DatasetMetadataRetriever,
    save_dataset_metadata,
    load_dataset_metadata,
    extract_dataset_text,
)
from .confidence_scoring import (
    CitationConfidenceScorer,
    score_dataset_citations,
    batch_score_citations,
)

__all__ = [
    "DatasetMetadataRetriever",
    "save_dataset_metadata",
    "load_dataset_metadata",
    "extract_dataset_text",
    "CitationConfidenceScorer",
    "score_dataset_citations",
    "batch_score_citations",
]
