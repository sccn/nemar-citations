# System Architecture

## Core Components

### 1. Citation Fetching Pipeline
- **Entry Point:** `dataset-citations-update` CLI command
- **Core Module:** `src/dataset_citations/core/getCitations.py`
- **Data Source:** Google Scholar via ScraperAPI
- **Output:** JSON files in `citations/json/` with citation details and metadata

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
OpenNeuro GitHub API
        ↓
Dataset Discovery
        ↓
Google Scholar (via ScraperAPI)
        ↓
Citation JSON Files
        ↓
Confidence Scoring
        ↓
Dashboard Generation
        ↓
Interactive HTML Reports
```

## Key Directories

- `citations/json/` - Citation data files
- `datasets/` - Dataset metadata from GitHub
- `interactive_reports/` - Generated dashboards
- `embeddings/` - Semantic vectors for similarity
- `tests/` - Test suite (needs expansion)

## Current Problems

1. **Automation Broken:** Dashboard generation not integrated in workflow
2. **Manual Process:** Dashboards created manually outside pipeline
3. **Monolithic Code:** Dashboard module too large to maintain
4. **No Test Data:** Need controlled test dataset for CI/CD