"""
Citation quality and confidence scoring functionality.

This module contains Phase 3 features including:
- Citation-to-dataset relevance scoring
- Confidence score calculation
- Sentence-transformers integration
- Metadata retrieval and comparison
"""

# Import only dataset_metadata to avoid sentence-transformers import issues during CLI help
from .dataset_metadata import (
    DatasetMetadataRetriever,
    save_dataset_metadata,
    load_dataset_metadata,
    extract_dataset_text,
)


# Lazy import functions for confidence scoring to avoid early sentence-transformers import
def get_confidence_scorer(*args, **kwargs):
    """Lazy import and create CitationConfidenceScorer."""
    from .confidence_scoring import CitationConfidenceScorer

    return CitationConfidenceScorer(*args, **kwargs)


def score_dataset_citations(*args, **kwargs):
    """Lazy import and call score_dataset_citations."""
    from .confidence_scoring import score_dataset_citations as _score_dataset_citations

    return _score_dataset_citations(*args, **kwargs)


def batch_score_citations(*args, **kwargs):
    """Lazy import and call batch_score_citations."""
    from .confidence_scoring import batch_score_citations as _batch_score_citations

    return _batch_score_citations(*args, **kwargs)


__all__ = [
    "DatasetMetadataRetriever",
    "save_dataset_metadata",
    "load_dataset_metadata",
    "extract_dataset_text",
    "get_confidence_scorer",
    "score_dataset_citations",
    "batch_score_citations",
]
