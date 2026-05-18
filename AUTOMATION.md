# Automated Monthly Citation Updates

This document describes the automated monthly citation update system.

## Overview

The system automatically runs the full citation update workflow on the 24th of each month at 2:00 AM, creating a PR with updated citations and deploying the dashboard to GitHub Pages.

## Setup Instructions

### Prerequisites

1. Ensure `.secrets` file exists with your API keys:
   ```bash
   GITHUB_TOKEN=your_token_here
   # Optional, raise opencite rate limits:
   # SEMANTIC_SCHOLAR_API_KEY=your_key
   # OPENALEX_API_KEY=your_key
   ```

2. Ensure PR #26 (deployment fixes) is merged to main

### Install Cron Job

Run the setup script:
```bash
./setup_cron.sh
```

This will:
- Add a cron job that runs on the 24th of each month at 2:00 AM
- Show you the current crontab for verification

### Manual Trigger

To manually trigger the monthly update:
```bash
./run_monthly_update.sh
```

## What Happens During Automated Run

1. **Updates main branch** - Pulls latest changes
2. **Runs full workflow**:
   - Discovers datasets from OpenNeuro
   - Fetches citing works via opencite (OpenAlex / Semantic Scholar / PubMed) anchored on each dataset's reference DOIs
   - Retrieves dataset metadata
   - Calculates confidence scores
   - Generates analysis (network, temporal, themes)
   - Creates dashboard
3. **Creates PR** - Automatic PR for review
4. **Deploys dashboard** - Updates GitHub Pages at https://neuromechanist.github.io/dataset_citations_dashboard.html

## Logs

All runs are logged to:
```
logs/monthly_update_YYYY-MM-DD_HH-MM.log
```

## Monitoring

Check for:
- New PRs created on the 24th of each month
- Dashboard updates at https://neuromechanist.github.io/dataset_citations_dashboard.html
- Log files in `logs/` directory
- Email notifications (if configured in GitHub)

## Troubleshooting

### Cron job not running

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

1. Check the log file:
   ```bash
   tail -50 logs/monthly_update_*.log
   ```

2. Verify API keys in `.secrets`

3. Test manually:
   ```bash
   ./run_end_to_end_workflow.sh full
   ```

## Disable Automation

To remove the cron job:
```bash
crontab -l | grep -v 'run_monthly_update.sh' | crontab -
```

## Schedule Customization

To change the schedule, edit the cron entry in `setup_cron.sh`:

```bash
# Format: minute hour day month day_of_week
# Current: 0 2 24 * *  (2:00 AM on 24th of each month)

# Examples:
# 0 2 1 * *    - 1st of each month at 2:00 AM
# 0 14 15 * *  - 15th of each month at 2:00 PM
# 0 2 * * 1    - Every Monday at 2:00 AM
```

Then re-run:
```bash
./setup_cron.sh
```
