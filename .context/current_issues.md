# Current Open Issues (priority order)

_Last refreshed: 2026-05-18. Authoritative state comes from `gh issue list --state open`; the entries below add context that doesn't fit in an issue title._

## CRITICAL: Backfill the opencite citation tree
**Status:** OPEN (no single issue; tracked across #43, #48 and operational state).
**Problem:** `citations/json_opencite/` is empty. The May 18 `workflow_dispatch` run (`26030534541`) was cancelled at the 6h GitHub Actions limit during the fetch step. The public dashboard at `dashboard.nemar.org/citations/` therefore still serves January 2026 scholarly-format data.
**Solution path:**
1. Shard discovery + fetch so each job finishes inside the 6h limit, OR run locally once with checkpointing and commit the seeded JSON tree.
2. Address #48 (dataset citation vs methodology-paper citation) before the backfill; otherwise we re-fetch.
3. Pin opencite version per #43.

## #48: Distinguish "cites the dataset" vs "cites the methodology paper"
**Opened:** 2026-05-18. **Priority:** HIGH — blocks meaningful backfill.
A citation that came from an `IsDerivedFrom` anchor (methodology paper, mirror DOI) should not be counted as "this paper uses the dataset". Schema v2 stores `source_relation` per citation; downstream rendering and scoring need to honor it.

## #43: Pin opencite version for Phase 2
**Opened:** 2026-05-18. **Priority:** HIGH — blocks deterministic backfill.
Settle on a release tag or commit SHA before running a full reindex, so future runs are reproducible.

## CRITICAL: Decide Semantic Scholar (S2) retirement
**Status:** OPEN (no issue yet — open one).
S2 throttling under opencite contributed to the May 18 timeout. Before retiring it, verify that OpenAlex covers the citations S2 currently surfaces uniquely (sample ~20 datasets). Document the diff in `.context/research.md`; retire via opencite config rather than a code fork. See `.rules/cross_repo.md` § Fetch Strategy.

## CRITICAL: Migrate discovery to api.nemar.org
**Status:** OPEN (no issue yet — open one; relates to #29 / #30).
`cli/discover.py` paginates GitHub for both `nemarDatasets/` and `OpenNeuroDatasets/` and now hits rate limits on full reindex. `api.nemar.org/datasets` returns the full catalog (~40KB, no auth) including DOI, modalities, source. Switch the primary discovery path; keep GitHub only as ds-* fallback. See `.rules/cross_repo.md`.

## HIGH: Render per-dataset uses/related panel in dashboard
**Status:** OPEN (no issue yet — open one).
`dashboard/components/modals.py:105-140` splits citations only by confidence. Schema v2 already carries `source_relation` ∈ {`References`, `IsDerivedFrom`, `IsIdenticalTo`, `IsVersionOf`}. Add a per-dataset panel grouped by relation type once the backfill lands. Small, isolated change.

## #30: Expand citation search methodology beyond dataset IDs
**Opened:** 2026-01-15. **Priority:** MEDIUM.
Captured in part by the opencite pivot (anchors expanded to PMID, arXiv, related DOIs). Revisit after backfill to confirm coverage gains.

## #29: Research alternative citation APIs (OpenAlex, S2, PubMed)
**Opened:** 2026-01-15. **Priority:** MEDIUM.
Largely answered by the opencite pivot (PR #47). Remaining work: document the OpenAlex-vs-S2 coverage comparison required to retire S2.

## #27: Style suggestions for next dashboard iteration
**Opened:** 2025-11-24. **Priority:** LOW.
Visual polish; revisit after the uses/related panel ships.

## #5: Explore richer graph network visualization libraries
**Opened:** 2025-08-26. **Priority:** LOW.
D3.js / Sigma.js / vis.js as alternatives to Cytoscape. Not blocking.

## Historical references
- **#10 (closed earlier):** "Revisit automation" — the workflow is now correctly wired to opencite (PR #47 + #50) but the timeout from the actual run is the live blocker. Don't conflate with the original code-integration problem.
- **#12 (closed earlier):** "Break down the dashboard-making function" — modularization shipped; `create_interactive_reports.py` is no longer the active entry point.
- **#11 (closed earlier):** "Simple test + CodeCov" — covered by the current `tests/` directory and `test.yml` workflow.
