"""DOI source extractors for the opencite-backed citation pipeline.

`nemar_metadata` reads `.nemar/metadata.json` from nm-prefixed nemarDatasets
repos. `bids_metadata` reads `dataset_description.json` from legacy
OpenNeuroDatasets ds-prefixed repos. Both return `FetchResult[list[DoiReference]]`
so callers distinguish errors from "no DOIs found".
"""

from dataset_citations.sources.bids_metadata import (
    BidsMetadataSource,
    parse_bids_description,
)
from dataset_citations.sources.doi import (
    extract_identifiers,
    is_openneuro_dataset_doi,
    normalize_doi,
    validate_identifier,
)
from dataset_citations.sources.models import (
    Author,
    CitingWork,
    DoiReference,
    FetchError,
    FetchResult,
    FetchSuccess,
    RelationType,
)
from dataset_citations.sources.nemar_metadata import (
    EMPTY_NEMAR_DATASET_METADATA,
    NemarDatasetMetadata,
    NemarMetadataSource,
    parse_nemar_dataset_metadata,
    parse_nemar_metadata,
)

__all__ = [
    "EMPTY_NEMAR_DATASET_METADATA",
    "Author",
    "BidsMetadataSource",
    "CitingWork",
    "DoiReference",
    "FetchError",
    "FetchResult",
    "FetchSuccess",
    "NemarDatasetMetadata",
    "NemarMetadataSource",
    "RelationType",
    "extract_identifiers",
    "is_openneuro_dataset_doi",
    "normalize_doi",
    "parse_bids_description",
    "parse_nemar_dataset_metadata",
    "parse_nemar_metadata",
    "validate_identifier",
]
