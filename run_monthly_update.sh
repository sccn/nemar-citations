#!/bin/zsh
#
# Monthly automated citation update script
# This wrapper script is designed to be run via cron
#

set -e

# Configuration
REPO_DIR="/Users/yahya/Documents/git/dataset_citations"
LOG_DIR="$REPO_DIR/logs"
DATE=$(date +"%Y-%m-%d_%H-%M")
LOG_FILE="$LOG_DIR/monthly_update_${DATE}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "========================================="
log "Starting monthly citation update"
log "========================================="

# Change to repository directory
cd "$REPO_DIR" || {
    log "ERROR: Failed to change to repository directory"
    exit 1
}

# Ensure we're on main branch and up to date
log "Updating main branch..."
git checkout main >> "$LOG_FILE" 2>&1
git pull origin main >> "$LOG_FILE" 2>&1

# Load secrets
if [ -f ".secrets" ]; then
    log "Loading secrets..."
    set -a
    source .secrets
    set +a
else
    log "ERROR: .secrets file not found"
    exit 1
fi

# Run the full workflow
log "Running full workflow..."
"$REPO_DIR/run_end_to_end_workflow.sh" full >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "Monthly update completed successfully"
    log "Check GitHub for new PR"
else
    log "ERROR: Monthly update failed with exit code: $EXIT_CODE"
    log "Check log file: $LOG_FILE"
fi

log "========================================="
log "Monthly update finished"
log "========================================="

exit $EXIT_CODE
