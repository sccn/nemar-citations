# Pivot to opencite: research findings + Phase 2 go/no-go

Status: draft (Phase 1, epic #37). Numbers below come from `scripts/phase1_*.py` runs in this PR.

## Recommendation

**GO for Phase 2.** Adopt opencite as the citation engine. Three findings drive the call:

1. nm-datasets already expose the structured anchor we need — `.nemar/metadata.json` v2.0 is present on 90% of the surveyed nm repos with rich `related_identifiers`.
2. Legacy ds-datasets are not blocked — `dataset_description.json` in `OpenNeuroDatasets/<id>` carries one or more DOIs/PMIDs in `DatasetDOI`/`HowToAcknowledge`/`ReferencesAndLinks` for ~94% of the 50-dataset sample.
3. opencite returns substantive citing-works lists for those DOIs against OpenAlex / Semantic Scholar with no API keys required for the spike (rate-limited but tractable). Comparison numbers below.

Preconditions surfaced during the spike:
- opencite's PyPI release lags the local `/Users/yahya/Documents/git/opencite` repo (PyPI 0.2.3 vs local 0.4.0). Phase 2 must either (a) pin a newer published version or (b) install opencite from a git ref / local path until 0.4.x is published.
- opencite pulls `markitdown`, `markit-mistral`, `pyalex` transitively. We do not need PDF conversion. **Action**: file an upstream issue in `neuromechanist/opencite` to expose a `core` extra that excludes the PDF tooling. Phase 2 can ship without this; we just absorb the extra closure size in the meantime.

## Schema we will consume

### nm-datasets (`nemarDatasets/<id>/.nemar/metadata.json` v2.0)

Top-level keys: `version, pipeline_stage, title, description, methods_description, license, dataset_type, authors, keywords, modalities, resource_type_general, resource_type_specific, source_hash, funding_references, related_identifiers`.

Anchor: `related_identifiers[]` — DataCite-style entries, each:
```
{ "identifier": "10.1038/sdata.2017.181", "identifier_type": "DOI", "relation_type": "References" }
```

`identifier_type` values observed: `DOI`, `URL`. `relation_type` values observed (descending frequency): `IsDescribedBy`, `References`, `IsDerivedFrom`, `IsIdenticalTo`, `IsVersionOf`, `IsSupplementedBy`.

### Legacy ds-datasets (`OpenNeuroDatasets/<id>/dataset_description.json`)

No structured relation types. We fall back to three fields:
- `DatasetDOI` — the dataset's own DOI (almost always present).
- `HowToAcknowledge` — free text often containing the canonical paper DOI or PubMed link.
- `ReferencesAndLinks` — array of URLs / DOIs / PubMed links.

We extract bare DOIs (regex `10\.\d{4,9}/...`) and PubMed IDs (`pubmed/\d+` or `pubmed.ncbi.nlm.nih.gov/\d+`) and tag each with the source field name. There is no DataCite-style `relation_type`; Phase 2/3 may infer relation labels heuristically (e.g., `DatasetDOI` -> `IsIdenticalTo`, `HowToAcknowledge` -> `IsDerivedFrom` when phrasing says "cite this paper").

## Relation types we treat as citation anchors

Phase 2 will look up citing-works for DOIs marked with the following `relation_type` values:

- `References` — direct upstream reference paper; almost always the canonical citation target. **Include.**
- `IsDerivedFrom` — dataset is derived from another work; that work's citations are strongly relevant. **Include.**
- `IsIdenticalTo` — points at a mirror / Zenodo deposit of the same dataset; useful for catching citations that DOI-match the alternate identifier. **Include.**
- `IsVersionOf` — points at a prior version; including its citations could over-count. **Include with deduplication** at the citation level (same citing paper across versions counted once).
- `IsSupplementedBy` — supplementary material; typically not the citation target. **Exclude** in Phase 2; revisit if signal is strong.
- `IsDescribedBy` — points at the dataset's own GitHub repo / NEMAR page / similar self-references. **Exclude** (no citation value).

For legacy ds-datasets without explicit relation_type, we treat `DatasetDOI` as `IsIdenticalTo`, `HowToAcknowledge`-extracted DOIs as `IsDerivedFrom` (since the field literally requests citation of those works), and `ReferencesAndLinks` DOIs as `References`.

## Coverage summary

From `scripts/phase1_nm_coverage.py --limit 30` (see `phase1_nm_coverage.md`):

| metric | value |
|--------|------:|
| nm repos sampled | 30 |
| with `.nemar/metadata.json` | 27 (90%) |
| total DOI identifiers across files | 70 |
| total URL identifiers across files | 54 |
| repos without metadata | nm000111, nm000116, nm000117 |

From `scripts/phase1_doi_extract.py --limit 50`:

| metric | value |
|--------|------:|
| ds-datasets processed | 50 |
| ds-datasets with at least one DOI | 47 (94%) |
| DOI + PMID records emitted | 86 |
| ds-datasets with `dataset_description.json` missing | 0 |

## Comparison summary

Numbers from `.context/phase1_comparison.csv` (12 ds + 3 nm datasets). Detailed spot-check notes live in `.context/phase1_comparison_notes.md`.

### Per-dataset highlights (ds, scholarly vs opencite by title)

| dataset | scholarly | opencite | title intersection |
|---------|----------:|---------:|-------------------:|
| ds000117 | 75 | 0 | 0 |
| ds000246 | 2 | 100 | 0 |
| ds000247 | 5 | 100 | 2 |
| ds000248 | 5 | 136 | 0 |
| ds001784 | 3 | 116 | 1 |
| ds001785 | 2 | 1 | 1 |
| ds001787 | 12 | 0 | 0 |
| ds001810 | 6 | 152 | 1 |
| ds001849 | 3 | 43 | 1 |
| ds001971 | 2 | 1 | 1 |
| ds002001 | 5 | 0 | 0 |
| ds002034 | 7 | 15 | 2 |

### nm-datasets (opencite-only; no scholarly history)

| dataset | source DOIs | citing papers via opencite |
|---------|----:|----:|
| nm000103 | 3 | 174 |
| nm000115 | 3 | 267 |
| nm000121 | 4 | 233 |

### Interpretation

1. The two methods discover **largely non-overlapping populations** (title intersection 0-2 per dataset). Scholarly finds papers that *mention the dataset id*; opencite finds papers that *cite the source paper DOI*. Phase 2/3 should treat them as complementary signals, not competing implementations.
2. Three ds-datasets (`ds000117`, `ds001787`, `ds002001`) returned 0 from opencite because their only DOI was the OpenNeuro `DatasetDOI` (e.g. `10.18112/openneuro.dsXXXXXX.vN.N.N`), which is **not indexed as a paper in OpenAlex / Semantic Scholar**. PMIDs were also present in two of these but the spike script skipped them. Verified that opencite supports `pmid:N` lookup natively. **Phase 2 must keep PMIDs**, and skip OpenNeuro DatasetDOIs from opencite lookups (use them only for record linkage).
3. For datasets where opencite returned results, the unfiltered output had a manually-spot-checked ~30% off-topic rate (general neuroscience reviews that cite the canonical paper without using the dataset). **Phase 3 must keep the sentence-transformer confidence pipeline** on the new path.
4. nm-datasets return useful citation counts immediately (174 / 267 / 233 papers across 3-4 source DOIs each). With confidence filtering and relation-type tagging, these are publishable signals.

## Operational notes

- The monthly `update_citations.yml` does not actually have a `schedule:` trigger (only `workflow_dispatch:`). Earlier docs claimed it was monthly-scheduled; the AGENTS.md fix is part of this PR.
- ScraperAPI credentials have lapsed. Running scholarly live is currently impossible. The "scholarly baseline" used in the comparison is the historical snapshot in `citations/json/`, not a live re-run.

## Phase 2 entry conditions

Phase 2 should start when:
- [x] This document records concrete comparison numbers (CSV present and summary section filled).
- [ ] An upstream issue is filed against `neuromechanist/opencite` requesting a `core` install extra (link from this doc).
- [ ] A decision is made on opencite version pinning (latest published 0.2.3 vs git ref of 0.4.0).

Phase 2 design adjustments derived from Phase 1 findings:
- **Keep PMIDs** in the DOI-source extractor; opencite supports `pmid:N` directly.
- **Skip OpenNeuro DatasetDOIs** from opencite lookups; treat them as record-linkage identifiers only.
- **Treat scholarly snapshots and opencite results as complementary inputs**, not as competing implementations. The citation JSON schema should tag each citation with its discovery source (`scholarly_text_match`, `opencite_doi:<relation_type>`).
- **Confidence scoring stays.** Phase 3 must keep the sentence-transformer pipeline on the new path; unfiltered opencite results carry ~30% off-topic noise.

---

# Per-source citation coverage (2026-06-19)

Epic #180, phase 2. Probe script: `scripts/probe_source_coverage.py`. Raw output: `.context/research/source_coverage_2026-06-19.json`. opencite v0.5.4.

## Why this re-probe
Phase 2 moves the backend to **delegate fetching to opencite** (one `CitationExplorer` per batch, source selection via `config.disabled_sources`, throughput via opencite's process-wide shared rate limiter) and removes our hand-rolled `S2_SKIP_PREFIXES` router. Before committing to "OpenAlex + S2, PubMed unwired," we measured what each cited-by source contributes on its own. opencite exposes three clients with a `citing_papers` method: OpenAlex, Semantic Scholar (S2), and PubMed (NCBI `elink`); `CitationExplorer` only fans out to OpenAlex + S2 today.

## Method
Same 30 unique DOIs as the 2026-05-19 probe (`scripts/probe_datasets.json`). For each DOI, **three independent single-source lookups**: OpenAlex (`lookup_doi` -> `citing_papers`), S2 (`citing_papers("DOI:<doi>")`), PubMed (`lookup_doi` -> `citing_papers(pmid)`). Each source's returned citing papers are projected to a normalized-DOI set; "unique" = a DOI present in exactly one source's set. `max_results=100` per call, keyless (OpenAlex no key; S2 shared pool; PubMed 3 req/s).

## Aggregate result (raw-DOI domain)

| Source | Citing DOIs | Unique to it | % of union | DOIs unresolved on source |
|---|---:|---:|---:|---:|
| OpenAlex | 1206 | 766 | 38.4% | 0 / 30 |
| Semantic Scholar | 914 | 454 | 22.8% | 17 / 30 |
| PubMed | 476 | 242 | 12.1% | 18 / 30 |

Union of all citing DOIs across the three sources: **1994**. S2 was unresolvable for 17 DOIs (the NEMAR / Zenodo / PhysioNet data-record families that 404 on S2); PubMed for 18 (anchors with no PMID). Transport errors were **0** for all three sources, so the counts above are not contaminated by failed lookups (a failed source would contribute an empty set and inflate the others' unique counts). Even across only ~12-13 resolvable anchors each, S2 and PubMed each surfaced hundreds of citing DOIs absent from OpenAlex's set.

## [CRITICAL] These per-source "unique" numbers are an UPPER BOUND
This probe does **naive DOI-only set arithmetic**, not the title+ID dedup that opencite's `CitationExplorer.deduplicate()` performs. Three effects inflate apparent uniqueness here, so the figures are **not** directly comparable to the 2026-05-19 figure of 9.71% S2-unique (which was measured *through* opencite's merge+dedup):
1. **DOI-less drops** — a paper a source returns without a DOI is dropped from that source's set, so the same paper found DOI-less by OpenAlex but with-DOI by S2 reads as "S2-unique."
2. **DOI-only cross-matching** — papers matched across sources by other IDs (PMID, OpenAlex ID, title) in opencite's dedup are treated as distinct here.
3. **Per-source top-100 truncation** — high-citation methodology anchors hit `max_results=100`; each source returns its own top-100, so disjointness is partly an artifact of which 100 each returned first.

The conservative, dedup-correct figure for S2's *marginal* contribution remains ~9.71% (2026-05-19). The robust, direction-only conclusions below do not depend on the inflated magnitudes.

## Decision
1. **Delegate to opencite; keep S2.** Both probes agree S2 is not redundant. Its only problem is throughput (1 req/s), now handled by opencite's shared `"s2"` rate limiter rather than our prefix skip. `S2_SKIP_PREFIXES` / `should_skip_s2` / the OpenAlex-only branch are removed; source on/off is `OPENCITE_DISABLED_SOURCES`.
2. **PubMed is worth wiring in.** Even as an upper bound, PubMed's contribution is clearly material and concentrated on biomedical anchors. Because measuring its *true* marginal value needs opencite's cross-source dedup, the right move is to **wire `PubMedClient.citing_papers` into `CitationExplorer` upstream in opencite** (DOI->PMID via `lookup_doi`, merge through the existing `deduplicate`), not to re-introduce a local multi-client merge here. Tracked upstream at neuromechanist/opencite#48; once it ships, the delegated backend picks PubMed up with zero downstream change.
3. **Follow-up rigorous measurement.** Once PubMed is in `CitationExplorer`, re-run with higher `max_results` and report the deduped marginal contribution (apples-to-apples with the 9.71% S2 figure).

---

# S2 vs OpenAlex coverage (2026-05-19)

Phase A of issue #53. Probe script: `scripts/probe_s2_vs_openalex.py` (removed in epic #180 phase 2; superseded by `scripts/probe_source_coverage.py`, see the 2026-06-19 section above). Raw output: `.context/research/s2_vs_openalex_2026-05-19.json`.

## Method
Twenty nm-* datasets from `api.nemar.org/datasets` (curated in `scripts/probe_datasets.json`), 44 DOI anchor entries collapsed to 30 unique DOIs. Each unique DOI run two ways:
- **OpenAlex-only**: `OpenAlexClient.lookup_doi` -> `OpenAlexClient.citing_papers` on the resolved OpenAlex ID.
- **Combined**: `CitationExplorer.citing_papers` — the production path, which fires OpenAlex and Semantic Scholar (S2) in parallel and merges.

Per-anchor diff is computed by normalized citing-paper DOI. `max_results=100` per call.

## Aggregate result

All counts below are in the DOI-set domain (papers identified by normalized DOI). Citing-paper records without a usable DOI are dropped by both sides because they cannot be cross-matched; raw paper counts including DOI-less records are reported separately at the bottom of the table.

| Metric | Value |
|---|---:|
| Unique DOIs probed | 30 |
| Unresolved in OpenAlex | 0 |
| DOIs at `max_results=100` truncation (either path) | 9 |
| Combined citing-paper DOIs | 1236 |
| OpenAlex-only citing-paper DOIs | 1192 |
| Overlap | 1116 |
| **S2-unique (in combined, not in OA-only)** | **120** |
| OpenAlex-unique (in OA-only, not in combined) | 76 |
| **S2-unique as % of combined** | **9.71%** |
| DOIs where S2 adds >=1 paper | 13 / 30 (43%) |
| DOIs where S2 adds >=5 papers | 8 / 30 (27%) |
| Raw citing papers, combined (DOI-less included) | 1278 |
| Raw citing papers, OpenAlex-only (DOI-less included) | 1199 |

The first three counts reconcile: `1236 = 1116 + 120` and `1192 = 1116 + 76`.

**Truncation caveat.** Nine DOIs hit the per-call `max_results=100` ceiling on at least one path. For those, part of the per-DOI diff reflects which 100 papers each backend returned first, not a real index gap. The 9.71% figure is therefore an upper bound on S2's unique contribution; the true coverage gain is likely lower. The DOIs most affected are high-citation methodology papers (e.g. `10.21105/joss.01896`, `10.3390/data4010014`).

## Where S2 helps and where it doesn't

**Top S2 contributors (descending S2-unique count):**
- `10.6084/m9.figshare.4244171.v2` -> 32 S2-unique (figshare data record)
- `10.1038/s41597-023-02650-w` -> 18 (Scientific Data)
- `10.1038/s41586-025-09255-w` -> 13 (Nature)
- `10.1371/journal.pone.0162657` -> 13 (PLOS ONE)
- `10.21105/joss.01896` -> 13 (JOSS)
- `10.3390/data4010014` -> 9 (MDPI Data)
- `10.1016/j.neucom.2016.01.007` -> 6 (Elsevier Neurocomputing)
- `10.1371/journal.pone.0178385` -> 5 (PLOS ONE)

**Zero S2 contribution (S2 returned 404 or empty):**
- All 5 NEMAR-minted DOIs in the sample (`10.82901/nemar.nm*`). S2 has not indexed them.
- All 6 Zenodo data records in the sample (`10.5281/zenodo.17287903`, ...). S2 does not index Zenodo data DOIs.
- Two of the figshare records (`10.6084/m9.figshare.2068677.v1` and similar).
- The PhysioNet `10.13026/*` family.

## Recommendation: keep S2, but route smarter

S2 is not negligible — it contributes a meaningful 9.39% of total coverage and helps on 43% of DOIs, concentrated in mainstream journals (Nature, Scientific Data, PLOS ONE, JOSS, Elsevier, MDPI). **Do not retire it.**

However, S2 produces zero value (just 404s and wasted rate-limit budget) for three identifiable DOI families:
- `10.82901/nemar.*` (NEMAR-minted DOIs — too new for S2)
- `10.5281/zenodo.*` (data records, not papers)
- `10.13026/*` (PhysioNet data records)
- Some `10.6084/m9.figshare.*` (data records, not papers)

These prefixes account for 11 of the 17 DOIs with zero S2 contribution in this sample.

**Action items (NOT in this PR, follow-ups):**
1. **Add a DOI-prefix pre-filter** in `backends/opencite_backend.py` that skips S2 entirely for known-zero-coverage prefixes. Keep OpenAlex as the only call for those. Saves rate budget without losing coverage.
2. **Lower opencite's global `max_retries`** from 3 to 1 in CI. Combined with #51/#52 + the prefix filter, this should fit the full 594-dataset backfill inside the 6h GitHub Actions window.
3. **Document the retention decision** in `.rules/cross_repo.md` (once PR #54 merges): replace "S2 retirement candidate" with "S2 retained; pre-filter known-404 prefixes; max_retries=1 in CI."
4. **Re-run the probe quarterly.** As S2 indexes newer DOIs (and adds the NEMAR DOIs once they propagate), the cost/benefit shifts.

## What this PR does

This PR ships only the probe script + the captured data + this report. The behavioral changes listed above are deliberately deferred to focused follow-up PRs so the data and the decision are reviewable independently of the code change. Issue #53 is closeable as "Phase A complete; Phase B = follow-up issues."

---

# 2026-05-22 — Epic #76 Phase 1 acceptance-gate probe

Status: PASS. Phase 1 (#85) ready for merge.

## Setup

- Model: `gemma4:31b` served by Ollama on hallu's RTX 4090.
- Network path: `ssh -fN -L 21434:localhost:11434 hallu`; `OLLAMA_BASE_URL=http://localhost:21434`. (Do NOT forward to port 11434 if a local `ollama serve` is also running — see the docstring in `scripts/probe_anchor_judgment.py` for why.)
- Probe: `scripts/probe_anchor_judgment.py` with the 5-class taxonomy + 3 in-prompt few-shot examples from `dataset_citations.quality.llm_client.build_anchor_prompt`.

## Results (10 anchors classified, 1 skip from a malformed-DOI extraction in `bids_metadata.py`)

| Dataset | Anchor DOI | Relation | Classification | Notes |
|---|---|---|---|---|
| ds005505 | 10.1101/2024.10.03.615261 | IsDerivedFrom | data_paper | HBN preprint, correct |
| ds005505 | 10.1101/2024.10.03.615261 | References | data_paper | same anchor, different relation |
| ds005505 | 10.1038/sdata.2017.181 | References | **umbrella** | HBN initiative paper, NOT this dataset's data paper — exactly the inflation case epic #76 exists to fix |
| ds005505 | 10.1038/sdata.2017.40 | References | **umbrella** | HBN imaging-resource paper, same pattern |
| ds000246 | 10.3389/fnins.2019.00076 | References | **methodology** | Brainstorm software paper, README explicitly cites it |
| nm000104 | 10.5281/zenodo.17287903 | IsVersionOf | data_paper | EMG2Qwerty Zenodo record |
| nm000104 | 10.5281/zenodo.17613953 | IsIdenticalTo | data_paper | EMG2Qwerty Zenodo mirror |
| nm000104 | 10.82901/nemar.nm000104 | IsVersionOf | data_paper | NEMAR-minted DOI for the same dataset |
| on001787 | 10.82901/nemar.on001787 | IsVersionOf | data_paper | EEG meditation study |
| ds002034 | 10.1007/s10548-019-00725-9 | References | data_paper | Single source paper, correct |

Distribution: 7 data_paper, 2 umbrella, 1 methodology — every classification matches the expected ground truth.

## Gate cases from issue #76, status

- ✅ HBN-derived dataset: classify HBN umbrella as `umbrella`, preprint as `data_paper`.
- ✅ Clean nm-* dataset: data paper classified correctly.
- ✅ Methodology-only anchor: classified as `methodology` (Brainstorm; equivalent to the spec'd MNE-Python case).

## Notes on iteration

- Earlier probe runs used `gemma4:26b`. 26B passed the HBN discrimination but **misclassified** the Brainstorm methodology anchor as `data_paper` and occasionally returned out-of-taxonomy labels (`"data_authors_paper"`). Default model updated to `gemma4:31b` in `OllamaJudgmentClient._DEFAULT_MODEL`.
- The malformed DOI `10.1038/sdata.2017.181)` with a literal trailing `)` is extracted by `sources/bids_metadata.py` from `HowToAcknowledge` text. File as a separate issue under the citation pipeline (out of scope for #76).
- A real Ollama daemon disconnect was observed during the probe run. The `_generate` wrapping now surfaces such errors as per-anchor SKIPs instead of aborting the batch.

Raw probe payload + full per-anchor JSON: see PR #89 artifacts (not committed to git to keep the repo lean).

