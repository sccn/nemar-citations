"""Core citation tracking functionality.

This module contains the JSON-shape helpers and the opencite pipeline
orchestrator. (The legacy scholarly fetcher `getCitations` was removed in
epic #37 phase 4, and the legacy pre-opencite write/migrate helpers in
epic #180 phase 5.)
"""

from . import citation_utils

__all__ = ["citation_utils"]
