#!/bin/zsh
#
# Setup cron job for monthly citation updates
# Runs on the 24th of each month at 2:00 AM
#

REPO_DIR="/Users/yahya/Documents/git/dataset_citations"
CRON_CMD="0 2 24 * * $REPO_DIR/run_monthly_update.sh"

echo "Setting up monthly cron job..."
echo "This will run on the 24th of each month at 2:00 AM"
echo ""
echo "Cron command:"
echo "$CRON_CMD"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_monthly_update.sh"; then
    echo "Cron job already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l 2>/dev/null | grep "run_monthly_update.sh"
    echo ""
    read "response?Replace existing cron job? (y/N): "
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Aborted. No changes made."
        exit 0
    fi
    # Remove old entry
    crontab -l 2>/dev/null | grep -v "run_monthly_update.sh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo ""
echo "Cron job added successfully!"
echo ""
echo "Current crontab entries:"
crontab -l
echo ""
echo "The script will run automatically on the 24th of each month at 2:00 AM"
echo "Logs will be saved to: $REPO_DIR/logs/monthly_update_*.log"
echo ""
echo "To remove the cron job later, run:"
echo "  crontab -l | grep -v 'run_monthly_update.sh' | crontab -"
