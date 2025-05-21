# Local Workflow Execution with `act`

This document describes how to set up and run the GitHub Actions workflows for this project locally using [`act`](https://github.com/nektos/act). This allows for faster testing and debugging without needing to push changes to GitHub.

## Prerequisites

1.  **Go (Golang):** Version 1.20 or newer.
    *   Installation on macOS (using Homebrew): `brew install go`
    *   Verify: `go version`
2.  **Docker:** Docker Desktop for your OS must be installed and the Docker daemon must be running. `act` uses Docker to execute workflow jobs in containers.
    *   Download from [Docker's website](https://www.docker.com/products/docker-desktop/).
3.  **Git:** Required for cloning `act` and for the workflow's own Git operations.

## Setup

1.  **Install `act`:**
    *   Clone the `act` repository (somewhere outside this project, e.g., in your home directory):
        ```bash
        git clone https://github.com/nektos/act.git
        ```
    *   Navigate into the cloned directory:
        ```bash
        cd act
        ```
    *   Build and install `act` (this usually places the binary in `$GOPATH/bin` or `$HOME/go/bin`, ensure this is in your system `PATH`):
        ```bash
        go install
        ```
    *   Verify installation by navigating back to this project's root directory and running:
        ```bash
        act -l 
        ```
        This should list the workflows found in `.github/workflows/`.

2.  **Configure Secrets (`.secrets` file):**
    *   `act` needs access to secrets your workflow uses (e.g., `GITHUB_TOKEN`, `SCRAPERAPI_KEY`).
    *   In the root of this project (`dataset_citations/`), create a file named `.secrets`.
    *   Add your secrets to this file in the format `KEY=VALUE`, one per line. Refer to `.secrets.example` for the required keys:
        ```
        GITHUB_TOKEN=your_actual_github_personal_access_token
        SCRAPERAPI_KEY=your_actual_scraperapi_key
        ```
    *   **Important:** The `.secrets` file is ignored by Git (via `.gitignore`) and should **never** be committed.
    *   The `GITHUB_TOKEN` should be a Personal Access Token (PAT) with `repo` and `workflow` scopes.

3.  **`act` Configuration File (`.actrc`):**
    *   An `.actrc` file is provided in the project root. It configures `act` to:
        *   Automatically load secrets from the `.secrets` file (`--secret-file .secrets`).
        *   Use a specific container architecture (`--container-architecture linux/amd64`) to avoid potential issues on Apple M-series chips.
    *   No action is needed from you for this file if it's present.

## Running Workflows Locally

A helper script `run_local_workflow.sh` is provided in the project root to simplify local execution.

1.  **Ensure the script is executable:**
    ```bash
    chmod +x run_local_workflow.sh
    ```

2.  **Run the default workflow event (`workflow_dispatch`):**
    ```bash
    ./run_local_workflow.sh
    ```
    This will trigger the `workflow_dispatch` event defined in `.github/workflows/update_citations.yml`.

3.  **Run a specific job from the workflow:**
    If your workflow has multiple jobs and you want to run a specific one (e.g., `update_citations_job`):
    ```bash
    ./run_local_workflow.sh update_citations_job
    ```

    The first time you run a workflow with `act`, it will download the necessary Docker images for the actions and the runner environment. This might take some time. Subsequent runs will be faster.

## Scheduled Local Execution (using `cron` on macOS/Linux)

You can schedule the local execution of the workflow using `cron`.

1.  **Create a logs directory (optional but recommended):**
    In the project root:
    ```bash
    mkdir logs
    ```
    (Consider adding `logs/` to your `.gitignore` if you haven't already to avoid committing local run logs.)

2.  **Edit your crontab:**
    Open your crontab file for editing:
    ```bash
    crontab -e
    ```

3.  **Add the cron job:**
    Add a line similar to the following, adjusting the schedule and paths as needed. This example runs daily at 2 AM:
    ```cron
    0 2 * * * cd /full/path/to/your/dataset_citations && ./run_local_workflow.sh >> /full/path/to/your/dataset_citations/logs/cron_act_run.log 2>&1
    ```
    *   Replace `/full/path/to/your/dataset_citations` with the absolute path to your project.
    *   `0 2 * * *` means "at 02:00 every day".
    *   `>> .../logs/cron_act_run.log 2>&1` redirects both standard output and standard error to a log file.

    **Example for last Friday of the month at 2 PM:**
    ```cron
    0 14 * * 5 [ "$(date +\%d)" -ge 24 ] && [ "$(date +\%d)" -le 31 ] && cd /full/path/to/your/dataset_citations && ./run_local_workflow.sh >> /full/path/to/your/dataset_citations/logs/cron_act_run.log 2>&1
    ```
    Note the escaped `%` for `date` command within cron.

4.  **Save and exit the crontab editor.** Cron will automatically pick up the new schedule.

## Troubleshooting

*   **`unknown command "set-default" for "gh repo"`:** This usually means an outdated version of the `gh` CLI is being used by `act`. The workflow now includes steps to install the latest `gh` CLI from its official source, which should resolve this.
*   **Docker image pulls:** The first run can be slow due to Docker image downloads.
*   **Architecture issues (Apple Silicon M1/M2/M3):** The `.actrc` file specifies `--container-architecture linux/amd64`. If you still encounter architecture-related errors, ensure this setting is active or try other options if necessary.
*   **Secrets:** Double-check that your `.secrets` file is correctly formatted, named, and in the project root, and that the tokens/keys within it are valid and have the correct permissions.
*   **`act` Logs:** `act` provides verbose output. If a step fails, review the logs for that step carefully. You can increase verbosity by running `act -v workflow_dispatch` or `act -vv workflow_dispatch` directly (or modify `run_local_workflow.sh` temporarily). 