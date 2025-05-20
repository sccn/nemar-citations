#!/bin/zsh
#
# Script to run the GitHub Actions workflow locally using act.
# It triggers the 'workflow_dispatch' event by default.
#
# Usage:
#   ./run_local_workflow.sh
#   ./run_local_workflow.sh [job_id]  (to run a specific job from the workflow_dispatch event)
#
# Make sure 'act' is installed and you have a .secrets file configured (or .actrc points to it).

set -e # Exit immediately if a command exits with a non-zero status.

# Navigate to the script's directory (which should be the project root)
# This makes the script runnable from anywhere if called with an absolute path.
cd "$(dirname "$0")"

EVENT_NAME="workflow_dispatch"
JOB_ID="$1" # Optional first argument is the job ID

echo "Attempting to run event '$EVENT_NAME' locally with act..."

if [ -n "$JOB_ID" ]; then
  echo "Targeting specific job: $JOB_ID"
  act "$EVENT_NAME" -j "$JOB_ID"
else
  echo "Running all jobs for event '$EVENT_NAME'."
  act "$EVENT_NAME"
fi

echo "Local execution with act finished." 