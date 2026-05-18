# NEMAR Citations Instructions

## Project Context
**Purpose:** Automated Brain Imaging Data Structure (BIDS) dataset citation tracking system for the NEMAR.org project. Discovers and tracks citations for 300+ neuroscience datasets from OpenNeuro, scores them with AI confidence, and renders an interactive dashboard hosted at `dashboard.nemar.org/citations/`.
**Tech Stack:** Python 3.13+, UV, Ruff, Ty, pytest, sentence-transformers, scholarly, Cloudflare Pages.
**Architecture:** CLI-first package (`dataset_citations.*`) with discovery → fetching → processing → scoring → analysis → dashboard pipeline. Automated monthly via GitHub Actions.

## Architecture Map
```
src/dataset_citations/
├── core/        # Citation fetching, JSON utilities (citation_utils.py, getCitations.py)
├── quality/     # AI confidence scoring, dataset metadata retrieval
├── cli/         # 20+ command-line entry points (see pyproject [project.scripts])
├── graph/       # Network analysis, Neo4j integration
├── embeddings/  # Semantic vector storage, UMAP, registry
├── dashboard/   # Interactive HTML/JS dashboard generation
├── analysis/    # Theme / network / temporal generators
└── utils/       # Shared helpers
tests/           # Real-data tests (NO MOCKS)
.github/workflows/
├── test.yml             # Lint, ruff format check, ty, pytest, integration
├── update_citations.yml # Monthly citation fetch + dashboard deploy
└── deploy-dashboard.yml # Manual dashboard rebuild + Cloudflare Pages deploy
```

## Environment Setup
```bash
# Bootstrap (one time)
uv sync --all-extras       # Install deps + dev tools from pyproject.toml
uv run pre-commit install  # Enable ruff hook

# Secrets
echo "SCRAPERAPI_KEY=..."  > .env
echo "GITHUB_TOKEN=..."   >> .env
# Optional: .secrets for integration tests
```

## Development Workflow
1. **Check context:** `.context/plan.md` (current tasks), `.context/current_issues.md` (priorities)
2. **Understand deeply:** `.context/architecture.md`, `.context/ideas.md`
3. **Branch:** `gh issue develop <issue-number>` (creates branch off `main` for each issue)
4. **Code:** Follow patterns in `.rules/`
5. **Test:** Real data only (`.rules/testing.md`)
6. **Document failures:** Log in `.context/scratch_history.md`
7. **Commit:** Atomic, conventional prefix (`feat:`, `fix:`, `chore:`, ...), <50 chars, no emojis, no AI attribution
8. **PR:** Reference the issue; ALL CI must be green before merge
9. **Code review:** Run `/review-pr` after creating PR (`.rules/code_review.md`)

## [CRITICAL] Core Principles - Never Compromise

### [FUNDAMENTAL] NO MOCKS - Test Reality Only
- Use real OpenNeuro datasets (subsets are fine — keep small controlled fixtures)
- No mocked Google Scholar / ScraperAPI / GitHub responses
- If real testing is impossible, no test is better than a fake passing test
**Details:** `.rules/testing.md`

### UV Exclusively
- `uv sync`, `uv run`, `uv add` — never pip, conda, or virtualenv
- pyproject.toml is the single source of truth (no requirements.txt)
**Details:** `.rules/python.md`

### Ruff + Ty
- Format and lint: `uv run ruff format` / `uv run ruff check --fix`
- Type check: `uv run ty check` (replaces mypy)
**Details:** `.rules/python.md`

### Commits & Git
- Atomic commits, focused changes
- Conventional prefix, <50 chars, no emojis, no AI attribution
**Details:** `.rules/git.md`

### No Technical Debt Carried Forward
- Address ALL PR review findings
- Skip only genuine false positives or intentional design choices, with rationale in the PR
**Details:** `.rules/code_review.md`

## [NEVER DO THIS]
- Never use mocks, stubs, or fake data in tests
- Never use `pip`, `conda`, or `virtualenv`; use UV
- Never use `mypy`; use `ty`
- Never use `black` or `isort`; ruff handles both
- Never commit secrets, .env files, or credentials
- Never leave empty catch blocks or silent failures
- Never add backward-compatibility shims; replace directly
- Never add TODO without a linked issue
- Never use emojis in commits, PRs, or code
- Never merge a PR without all CI green

## Key Development Commands
```bash
# Tests (fast)
uv run pytest tests/ -v
uv run pytest --cov=dataset_citations tests/

# Slow integration test (5-10 min, real Google Scholar)
RUN_SLOW_INTEGRATION_TESTS=1 uv run pytest \
  tests/test_getCitations.py::TestGetCitations::test_integration_full_api_workflow -v

# Lint, format, types
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
uv run ty check src/

# Pipeline CLIs (see pyproject [project.scripts] for the full set)
uv run dataset-citations-discover --output-file discovered_datasets.txt
uv run dataset-citations-update --dataset-list-file discovered_datasets.txt \
  --previous-citations-file citations/previous_citations.csv \
  --output-dir citations/ --output-format json
uv run dataset-citations-retrieve-metadata --citations-dir citations/json --output-dir datasets
uv run dataset-citations-score-confidence --citations-dir citations/json --datasets-dir datasets
```

## Data Flow
1. **Discovery** — Find BIDS datasets via GitHub API (`cli/discover.py`)
2. **Citation Fetching** — Google Scholar via ScraperAPI (`core/getCitations.py`)
3. **Processing** — Convert to JSON, attach metadata (`core/citation_utils.py`)
4. **Quality Scoring** — Sentence-transformer similarity between dataset metadata and citation abstract
5. **Analysis** — Network, temporal, and theme analyses with embeddings
6. **Dashboard** — Interactive HTML + D3 deployed to Cloudflare Pages

## Key Data Formats
- **Citation JSON** (`citations/json/`) — web-ready, includes confidence scores
- **Dataset metadata** (`datasets/`) — GitHub-sourced descriptions
- **Embeddings** (`embeddings/`) — semantic vectors + registry

## [REFERENCE] Rules Directory
### Core Standards
- `.rules/testing.md` — NO MOCKS policy
- `.rules/self_improve.md` — Learning from projects
- `.rules/documentation.md` — Docs standards
- `.rules/code_review.md` — PR review toolkit and checklist

### Language & Tools
- `.rules/python.md` — UV, ruff, ty
- `.rules/ci_cd.md` — GitHub Actions setup
- `.rules/git.md` — Branch + commit conventions

### MCP Tools
- `.rules/serena_mcp.md` — Code intelligence with Serena MCP

## Context Files
- `.context/plan.md` — Current tasks and phases (gitignored copy lives in plan.md at root for personal notes)
- `.context/research.md` — Technical explorations
- `.context/ideas.md` — Design concepts
- `.context/scratch_history.md` — Failed attempts and lessons
- `.context/current_issues.md` — Open GitHub issues and priorities
- `.context/architecture.md` — System architecture
- `.context/testing_strategy.md` — Test approach with controlled datasets
- `.context/development_plan.md` — Phased development roadmap

## CI/CD
- `.github/workflows/test.yml` — Lint (ruff format/check, ty), pytest 3.13, integration tests
- `.github/workflows/update_citations.yml` — `workflow_dispatch` only (no schedule): fetch citations, regenerate dashboard, deploy to Cloudflare Pages, open PR. ScraperAPI access has lapsed; this workflow does not run successfully today and is pending the epic #37 pivot to opencite.
- `.github/workflows/deploy-dashboard.yml` — Manual rebuild + deploy
- Secrets: `SCRAPERAPI_KEY`, `GITHUB_TOKEN`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`

## Project-Specific Guidelines
- **Domain:** NEMAR / OpenNeuro / BIDS / Hierarchical Event Descriptors (HED)
- **Writing style:** No em-dashes (use commas or semicolons); spell out acronyms on first use
- **Performance:** Dashboard payload was reduced from 18MB to 106KB — keep it optimized
- **External:** `dashboard.nemar.org/citations/` is the public-facing URL (Cloudflare Pages project `nemar-dashboard`)

---
Maintainable systems, not just code. Check `.rules/` for detailed guidance on any topic.
