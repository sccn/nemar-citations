#!/usr/bin/env bash
# Nightly hallu pipeline: pull main, run full opencite pipeline with GPU
# scoring, push results to an auto-update branch, open a PR. Designed to
# run from cron at 03:00 PDT (see crontab installed alongside this script).
#
# Locking: flock prevents concurrent runs. Logs land in $REPO_DIR/.logs/.
# Safety: a `git reset --hard origin/main` runs before any pipeline step,
# so this script assumes the working tree is disposable between runs.
set -uo pipefail

REPO_DIR="$HOME/dataset_citations"
LOG_DIR="$REPO_DIR/.logs"
LOCK_FILE="$REPO_DIR/.cron.lock"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
LOG="$LOG_DIR/cron-$TS.log"

mkdir -p "$LOG_DIR"

# Single-writer lock; concurrent invocations short-circuit instead of clobbering each other.
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "[hallu-cron $TS] another run in progress, skipping" | tee -a "$LOG_DIR/cron-skips.log"
  exit 0
fi

# Tee all subsequent output to the timestamped log file.
exec > >(tee -a "$LOG") 2>&1

trap 'rc=$?; if [ $rc -ne 0 ]; then echo "FAILED rc=$rc at line $LINENO"; fi' EXIT

echo "=== hallu-cron $TS start (host=$(hostname), pid=$$) ==="
cd "$REPO_DIR"

# Pull the GitHub token from gh CLI. cron jobs run with a minimal env;
# without this, dataset-citations-retrieve-metadata falls back to the
# unauthenticated public API (60 req/hr) and stalls after a handful of
# repos. gh stores the token in ~/.config/gh/hosts.yml from a prior
# `gh auth login`; we never have to write it to disk.
export GITHUB_TOKEN="$(gh auth token 2>/dev/null)"
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: gh auth token returned empty; aborting" >&2
  exit 2
fi

# Reset working tree to fresh main so each cron run starts from a known good state.
git fetch --quiet origin main
git checkout --quiet main
git reset --quiet --hard origin/main
git clean --quiet -fd citations/.checkpoints/ 2>/dev/null || true
echo "main at $(git rev-parse --short HEAD)"

DATASETS_LIST="/tmp/hallu_cron_discovered.txt"

# 1. Discover via catalog (api.nemar.org/datasets, no GitHub for this step).
echo "--- discover ---"
uv run dataset-citations-discover \
  --source catalog \
  --output-file "$DATASETS_LIST" \
  --no-catalog-cache

# 2. Retrieve dataset metadata from GitHub (hallu's own IP = own rate-limit budget).
# Moved ahead of `update` in phase 4 (#88) so anchor adjudication has dataset
# descriptions available, and the subsequent `update` step can consume the
# anchor-judgment sidecars produced below.
# `--skip-existing` keeps steady-state runs cheap and (more importantly) ducks
# the GitHub secondary rate limit that bit us during the post-#76 backfill:
# refetching ~3000 unchanged dataset_description.json + README files every
# weekly run is wasted quota. Trade-off: a dataset's GitHub-side description
# / README will only refresh when the cached file is deleted; #82 (follow-up)
# adds a `--max-age-days` flag mirroring `update.py` so the freshness window
# is configurable without an explicit wipe.
echo "--- retrieve-metadata ---"
uv run dataset-citations-retrieve-metadata \
  --citations-dir citations/json_opencite \
  --output-dir datasets \
  --skip-existing

# 3. Preflight: Ollama must be reachable for anchor adjudication. If the
# daemon is down, abort cleanly instead of producing a citation update
# with stale judgments. Exit 2 mirrors the contract documented for
# `dataset-citations-judge-anchors` (phase 2, #86). Honors
# $OLLAMA_BASE_URL so a non-default daemon URL is probed at the same
# host the CLI ends up calling.
OLLAMA_PROBE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
curl -s --max-time 5 "${OLLAMA_PROBE_URL}/api/tags" >/dev/null || {
  echo "ERROR: Ollama daemon at ${OLLAMA_PROBE_URL} not reachable; aborting." >&2
  exit 2
}

# 3a. Anchor adjudication: classify each anchor DOI as data_paper / umbrella /
# methodology / related_work / irrelevant and write sidecars under
# citations/anchor_judgments/. `--skip-existing` keeps steady-state runs cheap;
# the full ~3000-anchor backfill happens on first run after the epic merges.
# The cron uses `set -uo pipefail` (no -e), so a non-zero exit from the CLI
# does NOT halt the script by default; the explicit `|| { exit; }` guard
# below ensures a partial judgment run does not feed downstream `update`
# with a half-written sidecar tree.
echo "--- judge-anchors (gpu, ollama) ---"
uv run dataset-citations-judge-anchors \
  --datasets-list-file "$DATASETS_LIST" \
  --output-dir citations/anchor_judgments \
  --skip-existing || {
  echo "ERROR: dataset-citations-judge-anchors failed; aborting before update." >&2
  exit 2
}

# 3b. Fetch citations via opencite. Phase 3 (#87) made this CLI consume the
# sidecars from step 3a transparently; the invocation is unchanged from the
# pre-phase-4 script. Skip-existing (7d) keeps the run cheap.
#
# OPERATIONAL NOTE: on the first run after a fresh anchor-judgment backfill,
# `--max-age-days 7` (the `update` CLI default) will keep existing citation
# JSONs "fresh" and skip them, so the new bucketing does not take effect on
# already-cached datasets until the freshness window expires. To apply the
# new judgments immediately, manually re-run `dataset-citations-update`
# with `--max-age-days 0` once, then resume the normal weekly cron.
echo "--- update (skip-existing default 7d) ---"
OPENCITE_CONCURRENCY=4 \
  uv run dataset-citations-update \
    --dataset-list-file "$DATASETS_LIST" \
    --output-dir citations/

# 4. Semantic confidence scoring on RTX 4090. --skip-existing is a small speedup
#    for unchanged citation files.
echo "--- score-confidence (cuda) ---"
uv run dataset-citations-score-confidence \
  --citations-dir citations/json_opencite \
  --datasets-dir datasets \
  --device cuda \
  --skip-existing

# 5. Sentence-transformer embeddings on the RTX 4090. Phase 2 of epic #96
#    (#98) moved this step off CI because CPU torch in GitHub Actions took
#    ~10x longer than CUDA on hallu. `--skip-existing` is consistent with
#    the rest of the pipeline; the CLI also skips via the embedding
#    registry by default, so the flag is explicit-intent rather than a
#    behavior change. Outputs land under `embeddings/`, ready for the
#    UMAP step phase 3 (#99) will wire in right after this block.
#
#    Guard with `|| { exit 2; }` because the cron uses `set -uo pipefail`
#    (no -e); a non-zero exit otherwise would not halt the script and we
#    would publish a citation update without refreshed embeddings.
echo "--- generate-embeddings (cuda) ---"
uv run dataset-citations-generate-embeddings \
  --citations citations/json_opencite \
  --datasets datasets \
  --embeddings-dir embeddings \
  --embedding-type both \
  --device cuda \
  --skip-existing || {
  echo "ERROR: dataset-citations-generate-embeddings failed; aborting before commit." >&2
  exit 2
}

# Bail cleanly if no tracked data changed (typical when nothing is stale).
if git diff --quiet citations/ datasets/ embeddings/; then
  echo "no tracked data changes, nothing to commit"
  exit 0
fi

# Commit + push to a timestamped branch; open a PR (manual merge gates the deploy).
BRANCH="auto-update/$TS"
git checkout -b "$BRANCH"
git add citations/ datasets/ embeddings/
DIFFSTAT="$(git diff --cached --stat | tail -5)"
git commit -m "data: hallu nightly pipeline ($TS)

GPU semantic scoring + embeddings on RTX 4090. Pipeline:
  catalog discover -> metadata -> judge-anchors -> opencite fetch
  -> score-confidence -> generate-embeddings

$(echo "$DIFFSTAT")"

git push -u --quiet origin "$BRANCH"

PR_URL=$(gh pr create --base main --head "$BRANCH" \
  --title "Nightly pipeline: $TS" \
  --body "Auto-generated by hallu cron (03:00 PDT). GPU-scored on RTX 4090.

Diffstat:

\`\`\`
$DIFFSTAT
\`\`\`

Auto-merging on green CI. Cloudflare deploy fires via deploy-dashboard.yml's push trigger.")
echo "PR: $PR_URL"

# Auto-merge once CI is green. Data PRs have no human-reviewable
# content; CI is the only gate. --merge preserves commit history
# (no squash), --delete-branch keeps the remote tidy.
gh pr merge --auto --merge --delete-branch "$PR_URL"
echo "auto-merge enabled on $PR_URL"
echo "=== hallu-cron $TS done ==="
