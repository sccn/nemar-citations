"""Core citation tracking functionality.

This module contains the JSON-shape helpers and the opencite pipeline
orchestrator. (The legacy scholarly fetcher `getCitations` was removed in
Phase 4 of epic #37.)
"""

from . import citation_utils

__all__ = ["citation_utils"]
