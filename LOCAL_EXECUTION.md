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

2.  **Ensure your `.secrets` file is populated** with your `GITHUB_TOKEN` and `SCRAPERAPI_KEY`.

3.  **Execute the local run script:**
    ```bash
    ./run_local_workflow.sh
    ```
    This script uses `act` to run the `workflow_dispatch` event defined in your `.github/workflows/update_citations.yml` file.
    It will use the configurations from `.actrc` (which points to your `.secrets` file and sets container architecture).

4.  **To run a specific job within the workflow** (if your workflow has multiple jobs triggered by `workflow_dispatch`):
    ```bash
    ./run_local_workflow.sh [job_id]
    ```
    You can find job IDs by running `act -l` in the project root.

5.  **Directly invoking `act` (alternative to the script):**
    If you prefer, you can call `act` directly. The `.actrc` file helps simplify this.
    To trigger the `workflow_dispatch` event:
    ```bash
    act workflow_dispatch
    ```
    To trigger a specific job:
    ```bash
    act workflow_dispatch -j <job_id>
    ```

    **Note on Concurrency for `update_citations.py`:**
    The `update_citations.py` script, when run via the GitHub Action (and thus by `act`), now supports parallel processing for fetching citations. This is controlled by the `--workers` argument within the Python script itself. The GitHub workflow file (`update_citations.yml`) calls this script. If you need to adjust the concurrency when running locally via `act`, you would modify the `python update_citations.py ...` line within the `update_citations.yml` workflow file to change the default `--workers` value passed to it, or add it if not present.

    The default number of workers in `update_citations.py` is 10. You can change this in the script if needed or by modifying how the workflow calls it.

## Scheduled Local Execution (using `cron` on macOS/Linux)

You can schedule the local execution of the workflow using `