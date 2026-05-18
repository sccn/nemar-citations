# Changelog

All notable changes to this project. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `dataset-citations-update --backend opencite` runs the new DOI-anchored
  pipeline alongside the legacy scholarly path. Output lands at
  `<output-dir>/json_opencite/<id>_citations.json` (side-by-side; the
  legacy `citations/json/` tree is untouched).
- `src/dataset_citations/core/opencite_pipeline.py` orchestrates source
  extraction (nm or ds prefix), opencite lookup, dedup across anchors,
  and emits the schema-v2 citation JSON.
- `core.citation_utils.add_discovery_provenance` augments a citation JSON
  with `metadata.schema_version` (`"2.0"`), `metadata.discovery_backend`,
  and per-citation `discovery_backend` markers. Opencite-path citations
  additionally carry `source_doi` and `source_relation`.
- `dashboard.data.aggregator.DataAggregator.summary_by_backend()` returns
  `{dataset_id: {"scholarly": N, "opencite": M}}` for side-by-side parity
  reporting before scholarly is retired.
- `src/dataset_citations/sources/` subpackage with `NemarMetadataSource` and
  `BidsMetadataSource` for DOI-anchored citation discovery. Reads
  `.nemar/metadata.json` from `nemarDatasets` (DataCite-style
  `related_identifiers`) and `dataset_description.json` from
  `OpenNeuroDatasets` (`DatasetDOI` / `HowToAcknowledge` /
  `ReferencesAndLinks`).
- `src/dataset_citations/backends/opencite_backend.py`, a sync facade over
  `opencite.citations.CitationExplorer` for looking up papers that cite a
  given DOI / PMID / arXiv ID.
- `FetchSuccess` / `FetchError` result wrappers so callers can distinguish
  empty results from rate limits / network failures.
- `opencite` declared as a git-ref dependency pinned to `v0.4.0` (PyPI lags;
  switch tracked in #43 + neuromechanist/opencite#31).

### Changed
- `pyproject.toml`: added `opencite` to `dependencies` and regenerated
  `uv.lock`.
