#!/usr/bin/env python3
"""
Dataset Citations Package

Automated BIDS dataset citation tracking and JSON generation system.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

__version__ = "1.0.0"
__author__ = "Seyed Yahya Shirazi"
__email__ = "shirazi@ieee.org"
__license__ = "Copyright Reserved"

# Core functionality exports
from .core import citation_utils, getCitations

# Main functions from citation_utils
from .core.citation_utils import (
    create_citation_json_structure,
    get_citation_summary_from_json,
    load_citation_json,
    migrate_pickle_to_json,
    save_citation_json,
)

# Main functions from getCitations
from .core.getCitations import (
    get_citation_numbers,
    get_citations,
    get_working_proxy,
)

__all__ = [
    "citation_utils",
    "create_citation_json_structure",
    "getCitations",
    "get_citation_numbers",
    "get_citation_summary_from_json",
    "get_citations",
    "get_working_proxy",
    "load_citation_json",
    "migrate_pickle_to_json",
    "save_citation_json",
]
