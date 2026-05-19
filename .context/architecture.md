# System Architecture

## Pipeline at a glance

```
api.nemar.org/datasets  ─┐
data.nemar.org/<id>/...  ─┤── Discovery + DOI extraction
GitHub (ds-* fallback)   ─┘             │
                                         ▼
                  sources/nemar_metadata.py + bids_metadata.py
                                         │  (DOI/PMID/arXiv with relation_type)
                                         ▼
                  backends/opencite_backend.py
                       (OpenAlex / PubMed / S2*)
                                         │
                                         ▼
                  core/opencite_pipeline.py
                       (dedupe across anchors, schema v2)
                                         │
                                         ▼
                  citations/json_opencite/*.json
                                         │
                                         ▼
                  quality/  ── confidence scoring (sentence-transformers)
                                         │
                                         ▼
                  analysis/  ── network / temporal / themes
                                         │
                                         ▼
                  dashboard/  ── core.py → templates/nemar_simple.py
                                         │
                                         ▼
                  dashboard.nemar.org/citations/  (Cloudflare Pages)
```

\* S2 is a retirement candidate — see `.rules/cross_repo.md` and `.context/research.md`.

## Core components

### 1. Discovery + DOI extraction
- **Primary source:** `https://api.nemar.org/datasets` (D1 catalog, no auth). Covers nm-* and on-* (NEMAR-imported OpenNeuro) IDs in one ~40KB response.
- **Per-dataset metadata:** `https://data.nemar.org/<id>/metadata.json` for nm-* IDs.
- **Legacy fallback:** GitHub REST against `OpenNeuroDatasets/` for ds-* IDs not yet in the D1 catalog (`cli/discover.py`).
- **DOI parsers:**
  - `src/dataset_citations/sources/nemar_metadata.py` — reads `.nemar/metadata.json` from each dataset repo's git tree; consumes `related_identifiers[]` with DataCite `relation_type` ∈ {`References`, `IsDerivedFrom`, `IsIdenticalTo`, `IsVersionOf`} and `identifier_type == "DOI"`.
  - `src/dataset_citations/sources/bids_metadata.py` — reads `dataset_description.json` for legacy ds-* datasets.

### 2. Citation fetching
- **Module:** `src/dataset_citations/backends/opencite_backend.py` (sync facade over opencite).
- **Backends:** OpenAlex (primary), PubMed, Semantic Scholar (retirement candidate).
- **Throttling:** `OPENCITE_MAX_CONCURRENCY` (CI sets to 1, see PR #50).
- **Orchestrator:** `src/dataset_citations/core/opencite_pipeline.py` deduplicates across DOI anchors and writes schema-v2 JSON.

### 3. Confidence scoring
- **Module:** `src/dataset_citations/quality/`.
- **Model:** sentence-transformers Qwen3-Embedding-0.6B (CPU-only in CI).
- **Process:** Cosine similarity between dataset metadata (`datasets/<id>.json`) and citation abstracts.
- **Threshold:** ≥ 0.4 surfaces in the dashboard's high-confidence view.

### 4. Dashboard generation
- **Entry point CLI:** `dataset-citations-create-reports` → `src/dataset_citations/cli/create_interactive_reports_modular.py`.
- **Generator:** `src/dataset_citations/dashboard/core.py` (modularized; the legacy 3113-line `create_interactive_reports.py` is no longer the active entry point).
- **Template:** `src/dataset_citations/dashboard/templates/nemar_simple.py` — overview / network / themes tabs.
- **Components:** `src/dataset_citations/dashboard/components/` (modals, charts, etc.).
- **Per-dataset uses/related panel:** **not yet implemented.** The modal at `dashboard/components/modals.py:105-140` currently splits citations only by confidence, not by `source_relation`. Adding a "uses vs related" view is a small, isolated change once `citations/json_opencite/` actually contains data.

### 5. Automation workflow
- **File:** `.github/workflows/update_citations.yml`.
- **Triggers:** weekly cron (Sunday 06:00 UTC) + `workflow_dispatch`.
- **Steps:** Discover → Update citations (opencite) → Score → Generate dashboard → Deploy to Cloudflare Pages → Open PR.
- **Status as of May 18, 2026:** Workflow is correctly wired to opencite (post PR #47 / #50), but the most recent run (`26030534541`) was cancelled at the 6h GitHub Actions ceiling during the fetch step. Downstream steps (scoring, dashboard, deploy) never ran. The public dashboard therefore still shows January 2026 scholarly-format JSON.

## Cross-repo data flow
See `.rules/cross_repo.md` for the contract details. The short version:

- `nemar-cli` (`api.nemar.org` + `data.nemar.org` + `.nemar/metadata.json` LLM enrichment) is **upstream of us** for dataset listing and DOI provenance.
- `website` (`nemar.org`, Astro 6 SSR) does **not consume citation data today**; the dashboard remains the canonical surface at `dashboard.nemar.org/citations/`.

## Key directories
- `citations/json_opencite/` — current schema-v2 citation data (currently empty; see workflow status above).
- `citations/json/` — legacy scholarly-format data from up to January 2026, read-only history.
- `datasets/` — per-dataset metadata snapshots used for confidence scoring.
- `embeddings/` — semantic vectors + registry.
- `interactive_reports/` — generated dashboard artifacts (gitignored target; produced fresh each workflow run).
- `tests/` — real-data tests (no mocks).

## Open structural problems
1. **Backfill timeout.** Full opencite fetch at `OPENCITE_MAX_CONCURRENCY=1` does not finish inside a 6h GitHub Actions job. Needs sharding (chunked discovery into multiple jobs) or a one-time local run that commits the seeded `citations/json_opencite/` tree.
2. **S2 retirement.** Semantic Scholar throttling broke the last full run; need to verify OpenAlex coverage on a sample before flipping S2 off in opencite config.
3. **GitHub rate-limit on discovery.** Migrate `cli/discover.py` to consume `api.nemar.org/datasets` as the primary catalog; keep GitHub only for legacy ds-* IDs.
4. **Per-dataset uses/related view missing in dashboard.** Schema v2 already carries `source_relation`; renderer needs to group by it.
5. **Citation endpoint on api.nemar.org.** Out of scope here, but a future integration with `nemar.org` per-dataset pages would require adding `GET /datasets/:id/citations.json` to `nemar-cli/backend/`.
