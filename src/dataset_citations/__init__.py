#!/usr/bin/env python3
"""Dataset Citations Package.

Automated BIDS dataset citation tracking and JSON generation. The legacy
scholarly + ScraperAPI discovery path was retired in epic #37 phase 4, and
the legacy pre-opencite write/migrate helpers in epic #180 phase 5; the
package now exposes the opencite citation_utils helpers, the opencite-backed
pipeline orchestrator, and the source/backend modules.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

__version__ = "2.0.0"
__author__ = "Seyed Yahya Shirazi"
__email__ = "shirazi@ieee.org"
__license__ = "Copyright Reserved"

from .core import citation_utils
from .core.citation_utils import (
    add_discovery_provenance,
    get_citation_summary_from_json,
    load_citation_json,
)
from .core.opencite_pipeline import fetch_dataset_citations_via_opencite

__all__ = [
    "add_discovery_provenance",
    "citation_utils",
    "fetch_dataset_citations_via_opencite",
    "get_citation_summary_from_json",
    "load_citation_json",
]
