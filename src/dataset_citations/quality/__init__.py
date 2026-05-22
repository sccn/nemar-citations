"""
Citation quality and confidence scoring functionality.

This module contains Phase 3 features including:
- Citation-to-dataset relevance scoring
- Confidence score calculation
- Sentence-transformers integration
- Metadata retrieval and comparison

Epic #76 (anchor adjudication) adds the LLM client + prompt builder here so
phases 2, 3, and 4 import the prompt from one place.
"""

# Import only dataset_metadata to avoid sentence-transformers import issues during CLI help
from .dataset_metadata import (
    DatasetMetadataRetriever,
    extract_dataset_text,
    load_dataset_metadata,
    save_dataset_metadata,
)
from .llm_client import (
    ALLOWED_CLASSIFICATIONS,
    LlmJudgmentError,
    OllamaJudgmentClient,
    build_anchor_prompt,
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
    "ALLOWED_CLASSIFICATIONS",
    "DatasetMetadataRetriever",
    "LlmJudgmentError",
    "OllamaJudgmentClient",
    "batch_score_citations",
    "build_anchor_prompt",
    "extract_dataset_text",
    "get_confidence_scorer",
    "load_dataset_metadata",
    "save_dataset_metadata",
    "score_dataset_citations",
]
