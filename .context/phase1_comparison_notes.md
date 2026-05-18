# Phase 1: comparison spot-checks and qualitative notes

Companion to `.context/phase1_comparison.csv`. Spot-checks done by reading
`.context/phase1_opencite_raw.json` and the historical
`citations/json/<id>_citations.json` snapshots.

## Notable findings

### 1. Three datasets returned 0 opencite results — root cause confirmed
`ds000117`, `ds001787`, `ds002001` all returned 0 papers from opencite. In every
case the only resolvable identifier the extraction script passed in was the
OpenNeuro `DatasetDOI` (e.g. `10.18112/openneuro.ds000117.v1.1.0`), which is
**not indexed as a paper in OpenAlex / Semantic Scholar**.

`ds000117` and `ds001787` also expose PMIDs via `HowToAcknowledge` /
`ReferencesAndLinks`, but the comparison script intentionally filtered out
`pmid:` records. Manually re-running `uvx opencite cite pmid:25977808
--direction citing -f json --max 100` for ds000117's PubMed reference
returned a populated paper list, confirming opencite supports PMID lookup
directly.

**Implication for Phase 2**: the DOI extractor must keep PMIDs and pass them to
opencite (which accepts `pmid:N` syntax). It should *not* attempt to look up
OpenNeuro DatasetDOIs against OpenAlex; treat them as identifiers for record
linkage only.

### 2. opencite returns substantially broader citing-works than the scholarly snapshot
For datasets where opencite found anything, the title sets are 10-50x larger
than the scholarly snapshot (e.g. `ds001810`: scholarly 6 vs opencite 152;
`ds000247`: scholarly 5 vs opencite 100). This is consistent with how the two
methods differ at the source — scholarly searches Google Scholar for text
mentions of the dataset ID and applied confidence scoring downstream, while
opencite enumerates papers in OpenAlex / Semantic Scholar that *cite* the
source paper DOI.

These are different populations, not competing recall numbers:
- Scholarly path → "papers mentioning `ds000117` in body text"
- opencite path → "papers citing the canonical paper that produced ds000117"

A paper that text-mentions the dataset but doesn't cite its paper is
scholarly-only. A paper that cites the canonical paper but never names the
dataset is opencite-only.

### 3. Title intersection is near-zero across the 12 ds-datasets
Intersection ranges from 0-2 titles per dataset (most are 0 or 1). This
quantifies finding 2 — the two methods surface largely non-overlapping
populations. **Phase 2 should not present opencite as a "drop-in replacement"
producing the same papers; it should be framed as a complementary, more
defensible-by-construction signal.**

### 4. nm-datasets show clean opencite discovery
With no scholarly history available for nm-datasets, opencite produced
174 / 267 / 233 citing works for nm000103 / nm000115 / nm000121 respectively,
across 3-4 source DOIs per dataset. These numbers will need confidence
filtering before they reach the dashboard (Phase 3), but the raw recall is
healthy.

## Manual spot-checks (3 datasets)

### ds000247 — scholarly 5 titles, opencite 100 titles, intersection 2 by title
Manually inspected the 2 intersecting titles in `phase1_opencite_raw.json`:
both are MEG methodology papers (Tadel et al., Gramfort et al.) that both
cite the dataset's canonical paper AND text-mention the dataset id.

Sampled 10 opencite-only titles: 7 are clearly relevant MEG-analysis papers
citing the canonical methodology paper; 3 are tangential (general
neuroscience reviews). False-positive rate ~30% on the unfiltered opencite
output — consistent with the expectation that confidence scoring (Phase 3) is
still needed.

### ds001810 — scholarly 6 titles, opencite 152 titles
Sampled 10 opencite-only titles: 8 are EEG / ERP studies referencing the
methodology paper; 2 are unrelated. The scholarly set looks heavily
preprint-skewed; only one of the 6 scholarly titles appears in the opencite
output — likely because the preprints aren't indexed in OpenAlex yet.

### nm000115 — opencite 267 titles
Sampled 10: all 10 are EEG/MEG/imaging studies citing one of the three source
DOIs. No obvious false positives in the sample — likely because nm000115's
source DOIs are well-cited canonical papers, so the citing population is
domain-relevant by construction.

## Takeaways for Phase 2/3

1. **Keep PMIDs.** Extract them in the DOI-source step and pass them through
   to opencite verbatim (`pmid:N`).
2. **Drop OpenNeuro-style DatasetDOIs from opencite lookups.** They will
   always return 0 from OpenAlex. Keep them for record linkage.
3. **Treat scholarly snapshots and opencite results as complementary inputs**,
   not as competing implementations of the same method. The Phase 3 schema
   should tag each citation with its discovery source.
4. **Confidence scoring still matters.** Spot-checks show ~30% irrelevant
   papers in the unfiltered opencite output for typical methodology DOIs.
   Phase 3 must keep the sentence-transformer confidence pipeline (or an
   equivalent) on the new path.
