# Anchor-classification model bake-off (2026-06-21)

Epic #180 / issue #131. Investigation into why citation attribution over-spreads
(an anchor's citers leak across many datasets), and whether a better judgment
model or a relation-type prior fixes it. Reproduce with
`scripts/bench_anchor_models.py` (raw output: `anchor_model_bakeoff_2026-06-21.json`).

## Setup
- Hand-labeled set of 9 `(dataset, anchor)` pairs: 6 over-attribution cases
  (a shared resource/method paper a *different* dataset reuses, must NOT be
  `data_paper`) + 3 genuine data-paper controls (`IsDescribedBy`-ish).
- Models served by Ollama on the hallu RTX 4090 (24 GB): `gemma4:e4b` (the cron
  model), `gemma4:26b`, `gemma4:31b`, `qwen3.6:27b`.
- Metric: exact 5-class accuracy and the decision-relevant `data_paper`-vs-not
  binary (that binary is what drives whether an anchor's citers get attributed),
  with and without a deterministic relation-type prior.

## Results

| model | exact | data_paper-binary | + relation prior | avg latency |
|---|---|---|---|---|
| gemma4:e4b (cron) | 0.22 | 0.22 | 0.78* | ~1.0 s |
| gemma4:26b | 0.17 | 0.17 | 0.67* | ~0.9 s (2 timeouts, 1 malformed) |
| gemma4:31b | 0.33 | 0.44 | 0.78* | ~5.2 s |
| qwen3.6:27b | — | — | — | emitted non-JSON (reasoning tokens); unusable without client changes |

## Findings
1. **No bare model reliably makes the call.** All models default the
   over-attribution cases (ERP CORE, HBN-EEG, c-VEP method papers) to
   `data_paper`. gemma4:31b was the only one to correctly call ERP CORE
   `methodology` for even one dataset, at 5x the latency. The distinction
   ("this resource has its own data, but the dataset in front of me is a
   *different* dataset that merely reuses it") is not reliably inferrable from
   title/abstract by a 4B-31B model.
2. **`*` The relation-type prior's gain is illusory.** It lifts binary accuracy
   to 0.78, but it does so by discarding a genuine data paper:
   - `on000117` <- `10.1038/sdata.2015.1` (Wakeman & Henson, the real ds000117
     data paper) is tagged **`References`** in our metadata, identical to ERP
     CORE. The prior downgrades it.
   - `on004100` <- `10.1038/s41597-019-0105-7` (iEEG-**BIDS** standard, NOT a
     data paper) is tagged **`IsDescribedBy`**.
   So `relation_type` is noise in **both** directions and cannot drive a clean
   count.

## Conclusion
The root cause is **upstream metadata quality** (`relation_type` assignment), not
the downstream judgment model. Neither a bigger model nor a deterministic prior
fixes the over-attribution cleanly. The fix belongs in `nemar-cli` enrichment
(haiku), which sees full dataset context: filed as **nemarOrg/nemar-cli#826**.

Consequences:
- **#131** (prompt/model fix) is effectively a dead end for over-attribution;
  PR #191's prompt change is kept only because it helps genuine method papers.
- **#192** (delete the dashboard `METHODS_SPREAD`/`DENYLIST` heuristic) is
  **blocked on nemar-cli#826** — the heuristic is compensating for the
  unreliable upstream signal, so the current dashboard count is the *correct*
  one. Deleting it before enrichment is fixed would regress counts.
