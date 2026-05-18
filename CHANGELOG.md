# Changelog

All notable changes to this project. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `src/dataset_citations/sources/` subpackage with `NemarMetadataSource` and
  `BidsMetadataSource` for DOI-anchored citation discovery. Reads
  `.nemar/metadata.json` from `nemarDatasets` (DataCite-style
  `related_identifiers`) and `dataset_description.json` from
  `OpenNeuroDatasets` (`DatasetDOI` / `HowToAcknowledge` /
  `ReferencesAndLinks`).
- `src/dataset_citations/backends/opencite_backend.py` — sync facade over
  `opencite.citations.CitationExplorer` for looking up papers that cite a
  given DOI / PMID / arXiv ID.
- `FetchSuccess` / `FetchError` result wrappers so callers can distinguish
  empty results from rate limits / network failures.
- `opencite` declared as a git-ref dependency pinned to `v0.4.0` (PyPI lags;
  switch tracked in #43 + neuromechanist/opencite#31).

Not yet wired to any CLI — Phase 3 of epic #37 will add the
`dataset-citations-update --backend opencite` path.

### Changed
- `pyproject.toml`: added `opencite` to `dependencies` and regenerated
  `uv.lock`.
