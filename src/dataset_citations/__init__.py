#!/usr/bin/env python3
"""Dataset Citations Package.

Automated BIDS dataset citation tracking and JSON generation. Phase 4 of
epic #37 retired the legacy scholarly + ScraperAPI discovery path; the
package now exposes the citation_utils helpers, the opencite-backed
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
    create_citation_json_structure,
    get_citation_summary_from_json,
    load_citation_json,
    migrate_pickle_to_json,
    save_citation_json,
)
from .core.opencite_pipeline import fetch_dataset_citations_via_opencite

__all__ = [
    "add_discovery_provenance",
    "citation_utils",
    "create_citation_json_structure",
    "fetch_dataset_citations_via_opencite",
    "get_citation_summary_from_json",
    "load_citation_json",
    "migrate_pickle_to_json",
    "save_citation_json",
]
