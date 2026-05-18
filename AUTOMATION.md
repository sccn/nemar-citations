# Automated Citation Updates

This document describes the automated weekly citation update system.

## Overview

The pipeline runs automatically via two paths:

1. **GitHub Actions weekly cron** (preferred for production): `.github/workflows/update_citations.yml` triggers every Sunday at 06:00 UTC. The job fetches citations via opencite, regenerates the dashboard, and deploys to Cloudflare Pages at `dashboard.nemar.org/citations/`. The same workflow can be triggered manually via `workflow_dispatch`.
2. **Local cron** (optional fallback): a host-side `setup_cron.sh` adds a crontab entry that calls `run_end_to_end_workflow.sh full`. Useful for environments that cannot run GitHub Actions.

## Setup Instructions

### GitHub Actions (recommended)
No setup required beyond having the workflow file in `.github/workflows/`. Optional repository secrets raise opencite's rate limits:

- `GITHUB_TOKEN` (provided automatically by Actions)
- `SEMANTIC_SCHOLAR_API_KEY`
- `OPENALEX_API_KEY`
- `PUBMED_API_KEY`
- `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (required for the dashboard deploy step)

### Local cron (optional)

1. Ensure `.secrets` file exists with your API keys:
   ```bash
   GITHUB_TOKEN=your_token_here
   # Optional, raise opencite rate limits:
   # SEMANTIC_SCHOLAR_API_KEY=your_key
   # OPENALEX_API_KEY=your_key
   # PUBMED_API_KEY=your_key
   ```

2. Run the setup script:
   ```bash
   ./setup_cron.sh
   ```

### Manual Trigger

To manually run a full update locally:
```bash
./run_monthly_update.sh
# or, equivalently:
./run_end_to_end_workflow.sh full
```

To manually trigger the GitHub Actions workflow:
```bash
gh workflow run "Update citations" --repo nemarOrg/nemar-citations
```

## What Happens During an Automated Run

1. **Updates main branch** -- Pulls latest changes.
2. **Runs full workflow**:
   - Discovers datasets from OpenNeuro and nemarDatasets.
   - Fetches citing works via opencite (OpenAlex / Semantic Scholar / PubMed) anchored on each dataset's reference DOIs (extracted from `.nemar/metadata.json` or `dataset_description.json`).
   - Retrieves dataset metadata.
   - Calculates confidence scores.
   - Generates analysis (network, temporal, themes).
   - Creates dashboard.
3. **Creates PR** -- Automatic PR for review.
4. **Deploys dashboard** -- Cloudflare Pages at `https://dashboard.nemar.org/citations/`.

## Logs

GitHub Actions runs are visible at https://github.com/nemarOrg/nemar-citations/actions.

Local runs log to:
```
logs/citation_update_YYYY-MM-DD_HH-MM.log
```

## Monitoring

Check for:
- New weekly PRs titled "Update dataset citations".
- Dashboard updates at https://dashboard.nemar.org/citations/.
- Log files in `logs/` directory (local cron only).
- GitHub Actions email notifications on failed runs.

## Troubleshooting

### Local cron job not running
1. Check crontab is installed:
   ```bash
   crontab -l
   ```
2. Check system logs:
   ```bash
   tail -f /var/log/system.log | grep cron
   ```
3. Verify script permissions:
   ```bash
   ls -la run_monthly_update.sh
   ```

### Workflow fails
1. Check GitHub Actions log for the failed run.
2. For local runs, check the log file:
   ```bash
   tail -50 logs/citation_update_*.log
   ```
3. Verify API keys in `.secrets` (or repo secrets for GitHub Actions).
4. Test manually:
   ```bash
   ./run_end_to_end_workflow.sh full
   ```

## Disable Local Automation

To remove the local cron job:
```bash
crontab -l | grep -v 'run_monthly_update.sh' | crontab -
```

To disable the GitHub Actions weekly trigger without deleting the workflow, edit `.github/workflows/update_citations.yml` and comment out the `schedule:` block.

## Schedule Customization

GitHub Actions weekly schedule lives in `.github/workflows/update_citations.yml`:
```yaml
schedule:
  - cron: "0 6 * * 0"  # Sunday 06:00 UTC
```

Local cron is in `setup_cron.sh`. Edit the `CRON_SCHEDULE` line:
```bash
# Format: minute hour day month day_of_week
# Examples:
# 0 2 1 * *    -- 1st of each month at 2:00 AM
# 0 14 15 * *  -- 15th of each month at 2:00 PM
# 0 2 * * 1    -- Every Monday at 2:00 AM
```

Then re-run:
```bash
./setup_cron.sh
```
