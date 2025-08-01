"""
Embedding storage and management system for dataset citations.

This module provides functionality for:
- Persistent embedding storage with versioning
- Content change detection and obsolescence tracking
- UMAP dimensionality reduction and clustering
- Integration with citation confidence scoring system
"""

from .embedding_registry import EmbeddingRegistry
from .storage_manager import EmbeddingStorageManager
from .umap_analyzer import UMAPAnalyzer

__all__ = ["EmbeddingRegistry", "EmbeddingStorageManager", "UMAPAnalyzer"]
