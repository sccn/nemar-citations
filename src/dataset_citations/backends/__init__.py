"""Citation discovery backends.

`OpenCiteBackend` is the sync-friendly entry point used by the Phase 3
pipeline. Additional backends (e.g., a future Scholar replacement) can be
added here; they all return `FetchResult[list[CitingWork]]` so callers stay
backend-agnostic.
"""

from dataset_citations.backends.opencite_backend import OpenCiteBackend

__all__ = ["OpenCiteBackend"]
