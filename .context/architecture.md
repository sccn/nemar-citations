# System Architecture

## Core Components

### 1. Citation Fetching Pipeline
- **Entry Point:** `dataset-citations-update` CLI command
- **Core Module:** `src/dataset_citations/core/opencite_pipeline.py`, with DOI extractors in `src/dataset_citations/sources/` and the opencite adapter in `src/dataset_citations/backends/opencite_backend.py`
- **Data Sources:** `.nemar/metadata.json` (nm datasets) and `dataset_description.json` (legacy ds datasets) provide DOI/PMID anchors; opencite then queries OpenAlex / Semantic Scholar / PubMed for papers citing each anchor.
- **Output:** JSON files in `citations/json_opencite/` (schema v2) with citation details, source_doi/source_relation provenance, and discovery metadata.

### 2. Confidence Scoring System
- **Module:** `src/dataset_citations/quality/`
- **Model:** Sentence-transformers with Qwen3-Embedding-0.6B
- **Process:** Compares dataset metadata (from GitHub) with citation abstracts
- **Threshold:** Confidence score ≥ 0.4 for inclusion in analysis

### 3. Dashboard Generation
- **Current:** Monolithic `create_interactive_reports.py` (3113 lines)
- **Target:** Modular system with components:
  - `dashboard/components/` - UI components
  - `dashboard/data/` - Data aggregation
  - `dashboard/templates/` - HTML templates
  - `dashboard/core.py` - Orchestration

### 4. Automation Workflow
- **File:** `.github/workflows/update_citations.yml`
- **Trigger:** Manual via workflow_dispatch
- **Steps:**
  1. Discover datasets
  2. Fetch citations
  3. Calculate confidence scores
  4. Generate dashboards (BROKEN - needs fix)
  5. Create PR with updates

## Data Flow

```
GitHub API (OpenNeuroDatasets, nemarDatasets)
        ↓
Dataset Discovery
        ↓
DOI extraction (.nemar/metadata.json | dataset_description.json)
        ↓
opencite (OpenAlex / Semantic Scholar / PubMed)
        ↓
Citation JSON files (citations/json_opencite/, schema v2)
        ↓
Confidence Scoring
        ↓
Dashboard Generation
        ↓
Interactive HTML Reports
```

## Key Directories

- `citations/json_opencite/` - Citation data files (schema v2)
- `datasets/` - Dataset metadata from GitHub
- `interactive_reports/` - Generated dashboards
- `embeddings/` - Semantic vectors for similarity
- `tests/` - Test suite (needs expansion)

## Current Problems

1. **Automation Broken:** Dashboard generation not integrated in workflow
2. **Manual Process:** Dashboards created manually outside pipeline
3. **Monolithic Code:** Dashboard module too large to maintain
4. **No Test Data:** Need controlled test dataset for CI/CD