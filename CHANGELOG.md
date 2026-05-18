# Changelog

All notable changes to this project. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Removed (breaking)
- The legacy `scholarly` + ScraperAPI citation discovery path. `dataset-citations-update`
  now runs the opencite pipeline unconditionally; the `--backend` flag is gone.
  Automation that hardcoded `--backend scholarly` or `--backend opencite` will
  fail loudly at argparse time. Output continues to live under
  `citations/json_opencite/`; the legacy `citations/json/` tree is no longer
  written by this package.
- Source files deleted:
  - `src/dataset_citations/core/getCitations.py`
  - `src/dataset_citations/test_end_to_end.py`
  - `tests/test_getCitations.py`
- Dependencies dropped from `pyproject.toml`: `scholarly`, `free-proxy`,
  `selenium`. The `httpx<=0.27.0` upper bound (which existed for scholarly
  compatibility) is now `httpx>=0.27.0`.
- Removed CLI flags from `dataset-citations-update`: `--backend`,
  `--previous-citations-file`, `--workers`, `--output-format`,
  `--no-update-num-cites`, `--no-update-cite-list`. The surface is now
  `--dataset-list-file` and `--output-dir`.
- `__version__` bumped to `2.0.0`.

### Action required (operator)
- Delete the `SCRAPERAPI_KEY` secret from the GitHub Actions repo settings
  (Settings -> Secrets and variables -> Actions). It is no longer referenced.
- Optionally add `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_API_KEY`,
  `PUBMED_API_KEY` as repo secrets to raise opencite's rate limits.
- Local `.env` / `.secrets` files: drop `SCRAPERAPI_KEY`; the optional
  opencite keys above are honored if present.

### Added
- Weekly schedule on `.github/workflows/update_citations.yml` (Sunday 06:00 UTC)
  so the opencite pipeline runs automatically against all nemarDatasets and
  legacy OpenNeuro datasets. Manual `workflow_dispatch` trigger preserved.
- `dataset-citations-update --backend opencite` selects the new DOI-anchored
  pipeline instead of the legacy scholarly path; the two backends are
  mutually exclusive per invocation. Output lands at
  `<output-dir>/json_opencite/<id>_citations.json`, so the legacy
  `citations/json/` tree is untouched and both outputs can coexist on disk
  for side-by-side parity comparison before Phase 4 retires scholarly.
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
