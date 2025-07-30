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
from dataset_citations.core import citation_utils
from dataset_citations.core import getCitations

# Main functions
from dataset_citations.core.citation_utils import (
    save_citation_json,
    load_citation_json,
    migrate_pickle_to_json,
    create_citation_json_structure,
    get_citation_summary_from_json,
)

from dataset_citations.core.getCitations import (
    get_working_proxy,
    get_citation_numbers,
    get_citations,
)

__all__ = [
    "citation_utils",
    "getCitations",
    "save_citation_json", 
    "load_citation_json",
    "migrate_pickle_to_json",
    "create_citation_json_structure",
    "get_citation_summary_from_json",
    "get_working_proxy",
    "get_citation_numbers",
    "get_citations",
] 