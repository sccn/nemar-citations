"""
Script to discover datasets from the OpenNeuroDatasets GitHub organization
that contain EEG, iEEG, or MEG data, based on BIDS directory structures.
"""

import argparse
import os
import time
import logging
import requests  # Using requests for simplicity, consider httpx for async later if needed
import pandas as pd  # For lookup table
from datetime import datetime  # For rate limit logging and processed_date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Outputs to console
        # Optionally add logging.FileHandler("discover_datasets.log")
    ]
)
logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
TARGET_ORG = "OpenNeuroDatasets"  # The organization to scan
# Max items per page for GitHub API
# https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api?apiVersion=2022-11-28#changing-the-number-of-items-per-page
DEFAULT_PER_PAGE = 100

# BIDS modalities to search for (for final filtering)
TARGET_MODALITIES = ["eeg", "ieeg", "meg"]
# All BIDS data types that could be present in a subject directory (for comprehensive logging)
# This list can be expanded based on BIDS specs for other common data types.
ALL_POSSIBLE_BIDS_MODALITIES = sorted(list(set(TARGET_MODALITIES + [
    "anat", "func", "dwi", "fmap", "perf", "pet", "beh", "micr", "motion",
    "nirs", "mrs"
])))  # Add more as needed

LOOKUP_TABLE_PATH = "citations/dataset_modalities_lookup.csv"
LOOKUP_COLUMNS = ["dataset_name", "modalities", "processed_date"]


def load_lookup_table(path: str) -> pd.DataFrame:
    """Loads the dataset modalities lookup table from a CSV file."""
    if os.path.exists(path):
        try:
            logger.info(f"Loading existing lookup table from {path}")
            df = pd.read_csv(path)
            # Ensure correct columns, handle if file is empty or malformed
            if not all(col in df.columns for col in LOOKUP_COLUMNS):
                logger.warning(f"Lookup table {path} has incorrect columns. Will create a new one.")
                return pd.DataFrame(columns=LOOKUP_COLUMNS)
            # For simplicity, we'll assume modalities is a comma-separated string and process later as needed.
            return df.set_index("dataset_name")  # Index by dataset_name for quick lookups
        except pd.errors.EmptyDataError:
            logger.info(f"Lookup table {path} is empty. Creating a new one.")
            return pd.DataFrame(columns=LOOKUP_COLUMNS).set_index("dataset_name")
        except Exception as e:
            logger.error(f"Error loading lookup table {path}: {e}. Will create a new one.")
            return pd.DataFrame(columns=LOOKUP_COLUMNS).set_index("dataset_name")
    else:
        logger.info(f"Lookup table {path} not found. Creating a new one.")
        return pd.DataFrame(columns=LOOKUP_COLUMNS).set_index("dataset_name")


def save_lookup_table(df: pd.DataFrame, path: str):
    """Saves the dataset modalities lookup table to a CSV file."""
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.reset_index().to_csv(path, index=False)
        logger.info(f"Successfully saved lookup table to {path} with {len(df)} entries.")
    except Exception as e:
        logger.error(f"Error saving lookup table to {path}: {e}")


def get_github_api_response(api_url: str, headers: dict) -> requests.Response | None:
    """
    Makes a GET request to the specified GitHub API URL.

    Handles basic error checking and returns the response object.
    Includes awareness of primary rate limits.

    Args:
        api_url (str): The full URL for the GitHub API endpoint.
        headers (dict): Dictionary of request headers (including Authorization).

    Returns:
        requests.Response | None: The response object if successful (even if HTTP error),
                                   or None if a critical request exception occurs.
    """
    try:
        response = requests.get(api_url, headers=headers)

        # Check rate limits (primary ones)
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers['X-RateLimit-Remaining'])
            limit = int(response.headers['X-RateLimit-Limit'])
            reset_time = int(response.headers['X-RateLimit-Reset'])
            logger.debug(
                f"Rate limit: {remaining}/{limit} remaining. "
                f"Resets at {datetime.fromtimestamp(reset_time)}."
            )
            if remaining < 20:  # Be conservative
                wait_time = max(0, reset_time - time.time()) + 15  # Add a small buffer
                logger.warning(
                    f"Approaching rate limit ({remaining} remaining). "
                    f"Waiting for {wait_time:.2f} seconds."
                )
                time.sleep(wait_time)

        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        return response
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - URL: {api_url}")
        if response is not None:  # Return response for potential further inspection
            logger.error(f"Response content: {response.text[:500]}")  # Log first 500 chars
            return response
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err} - URL: {api_url}")
    return None


def check_repository_for_modalities(repo_name: str, org_name: str, headers: dict) -> list[str]:
    """
    Checks a given repository for BIDS data types by inspecting subdirectories
    within the first found subject directory (e.g., sub-01).

    Args:
        repo_name (str): The name of the repository.
        org_name (str): The name of the organization owning the repository.
        headers (dict): Headers for GitHub API requests (including auth).

    Returns:
        list[str]: A list of all directory names found within the first subject directory
                   (e.g., ["eeg", "anat", "func"]). Returns an empty list if no subject
                   directory is found, it's empty, or if errors occur.
    """
    all_found_modalities_in_repo = set()  # Using a more generic name now
    logger.info(f"Scanning repository: {org_name}/{repo_name} for all BIDS data types...")

    # 1. List contents of the repository root to find sub-* directories
    root_contents_url = f"{GITHUB_API_BASE_URL}/repos/{org_name}/{repo_name}/contents/"
    root_response = get_github_api_response(root_contents_url, headers)

    if not (root_response and root_response.status_code == 200):
        logger.warning(
            f"Could not list root contents for {org_name}/{repo_name}. "
            f"Status: {root_response.status_code if root_response else 'N/A'}"
        )
        return []

    subject_dirs_found = 0
    for item in root_response.json():
        if item['type'] == 'dir' and item['name'].startswith('sub-'):
            subject_dirs_found += 1
            subject_dir_name = item['name']
            logger.debug(f"  Found subject directory: {subject_dir_name} in {repo_name}. Checking its contents.")

            # 2. List contents of this subject directory to find session directories or modality directories
            subject_contents_url = item['url']  # API URL for subject directory contents
            subject_response = get_github_api_response(subject_contents_url, headers)

            if not (subject_response and subject_response.status_code == 200):
                logger.warning(f"Could not list contents for {subject_dir_name} in {repo_name}. Skipping this sub-dir.")
                # Since we only check the first subject dir, if it fails, we bail for this repo.
                return []

            # Check if there are any session directories (ses-*)
            session_dirs = []
            for sub_item in subject_response.json():
                if sub_item['type'] == 'dir' and sub_item['name'].startswith('ses-'):
                    session_dirs.append(sub_item)
                elif sub_item['type'] == 'dir':  # Also collect direct modality dirs under subject
                    dir_name = sub_item['name']
                    logger.info(f"Found data directory: {dir_name} directly under {subject_dir_name} of {repo_name}")
                    all_found_modalities_in_repo.add(dir_name)

            # If session directories exist, check the first one for modality directories
            if session_dirs:
                logger.debug(f"Found {len(session_dirs)} session directories in {subject_dir_name}."
                             "Checking the first one.")
                first_session = session_dirs[0]
                session_dir_name = first_session['name']

                # List contents of the first session directory
                session_contents_url = first_session['url']
                session_response = get_github_api_response(session_contents_url, headers)

                if not (session_response and session_response.status_code == 200):
                    logger.warning(f"Could not list contents for {session_dir_name} in {subject_dir_name}"
                                   f"of {repo_name}. Using subject-level directories only.")
                else:
                    # Process modality directories within this session
                    for session_item in session_response.json():
                        if session_item['type'] == 'dir':
                            dir_name = session_item['name']
                            logger.info(f"    Found data directory: {dir_name} in {session_dir_name} of"
                                        f"{subject_dir_name} in {repo_name}")
                            all_found_modalities_in_repo.add(dir_name)

            if all_found_modalities_in_repo:
                logger.debug(
                    f"Finished checking subject directory {subject_dir_name}."
                    f"Found data types: {all_found_modalities_in_repo}"
                )
            else:
                logger.debug(f"  No subdirectories found in subject/session directories: {subject_dir_name}")

            # We only check the first representative subject directory to save API calls.
            # Return all unique directory names found within this first subject directory.
            return sorted(list(all_found_modalities_in_repo))

    if subject_dirs_found == 0:
        logger.info(f"No 'sub-' directories found in the root of {repo_name}.")

    return sorted(list(all_found_modalities_in_repo))  # Should be empty if we exited early or no sub-dirs


def main():
    """Main function to orchestrate dataset discovery."""
    parser = argparse.ArgumentParser(description="Discover OpenNeuro datasets with specific BIDS modalities.")
    parser.add_argument("--output-file", help="Path to save the list of discovered dataset names"
                        "(those matching TARGET_MODALITIES).")
    parser.add_argument(
        "--max-repos",
        type=int,
        default=None,
        help="Maximum number of repositories to process (for testing)."
    )
    parser.add_argument(
        "--force-rescan-all",
        action="store_true",
        help="Force a full rescan of all repositories, ignoring the lookup table for fetching modalities."
    )
    args = parser.parse_args()

    logging.info("Starting dataset discovery process...")

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN environment variable not set.")
        return

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Load existing lookup table or create an empty one
    lookup_df = load_lookup_table(LOOKUP_TABLE_PATH)
    # Ensure 'modalities' column is treated as string for consistent handling, especially if empty then filled
    if 'modalities' not in lookup_df.columns and not lookup_df.empty:
        lookup_df['modalities'] = pd.NA  # Or empty string, depending on how we handle it later
    elif lookup_df.empty and LOOKUP_COLUMNS:
        lookup_df = pd.DataFrame(columns=LOOKUP_COLUMNS).set_index("dataset_name")

    all_gh_repositories = []
    url = f"https://api.github.com/orgs/{TARGET_ORG}/repos?type=public&per_page={DEFAULT_PER_PAGE}"
    page_num = 1

    logging.info(f"Fetching list of all repositories from {TARGET_ORG}...")
    while url:
        if args.max_repos is not None and len(all_gh_repositories) >= args.max_repos:
            logging.info(f"Reached max_repos limit of {args.max_repos} for initial GitHub repo listing.")
            break
        logging.info(f"Fetching page {page_num} of repositories from {url.split('?')[0]}...")
        response_obj = get_github_api_response(url, headers)  # Renamed to response_obj for clarity

        if not response_obj:
            logging.error("Critical error fetching repository list from GitHub. Aborting.")
            return  # Cannot proceed without the repo list

        page_repos_json = []
        next_page_url = None

        if response_obj.status_code == 200:
            try:
                page_repos_json = response_obj.json()
                links_header = requests.utils.parse_header_links(response_obj.headers.get('Link', ''))
                for link_info in links_header:
                    if link_info.get('rel') == 'next':
                        next_page_url = link_info['url']
                        break
            except ValueError:  # Includes JSONDecodeError
                logging.error("Failed to decode JSON from GitHub API response for repository list.")
                return  # Critical error
        else:
            logging.error(
                f"GitHub API request for repository list failed with status {response_obj.status_code}. "
                f"Response: {response_obj.text[:200]}"
            )
            return  # Critical error

        if not isinstance(page_repos_json, list):
            logging.error(f"Expected a list of repositories, got {type(page_repos_json)}. Aborting.")
            return

        all_gh_repositories.extend(page_repos_json)
        logging.info(f"Fetched {len(page_repos_json)} repositories on this page. Total fetched so far:"
                     f"{len(all_gh_repositories)}.")
        url = next_page_url
        page_num += 1

    logging.info(f"Total repositories listed from GitHub: {len(all_gh_repositories)}")
    if args.max_repos is not None:
        # Apply max_repos limit *after* fetching all, then trim for processing if needed
        # Or, if meant to limit API calls, the break inside loop is primary.
        # For processing, we can re-slice if a different number is desired for actual checks vs listing.
        # Current logic limits actual processing by index in loop below if max_repos is set.
        pass

    processed_repo_count = 0
    for repo_data in all_gh_repositories:
        if args.max_repos is not None and processed_repo_count >= args.max_repos:
            logging.info(f"Reached processing limit of --max-repos ({args.max_repos})."
                         "Stopping further repository checks.")
            break

        repo_name = repo_data.get("name")
        if not repo_name:
            logging.warning(f"Repository found without a name: {repo_data.get('html_url')}. Skipping.")
            continue

        processed_repo_count += 1
        current_time_iso = datetime.now().isoformat()

        if not args.force_rescan_all and repo_name in lookup_df.index:
            logging.info(f"Dataset {repo_name} found in lookup table. Using cached modalities.")
            # Optionally, update processed_date if we want to track when it was last seen/confirmed
            # lookup_df.loc[repo_name, 'processed_date'] = current_time_iso
            continue  # Already processed and in table, unless forcing rescan

        logging.info(f"Processing {repo_name} (New or --force-rescan-all)..."
                     f"({processed_repo_count}/{len(all_gh_repositories)
                     if args.max_repos is None else args.max_repos})")
        all_modalities_found = check_repository_for_modalities(repo_name, TARGET_ORG, headers)

        modalities_str = ",".join(sorted(list(set(all_modalities_found))))  # Ensure unique and sorted for consistency

        # Update or add to lookup DataFrame
        if repo_name in lookup_df.index:  # If force_rescan_all, update existing
            lookup_df.loc[repo_name, 'modalities'] = modalities_str
            lookup_df.loc[repo_name, 'processed_date'] = current_time_iso
        else:  # New entry
            new_row = pd.DataFrame([{'modalities': modalities_str, 'processed_date': current_time_iso}],
                                   index=[repo_name])
            new_row.index.name = "dataset_name"
            lookup_df = pd.concat([lookup_df, new_row])

    # Save the potentially updated lookup table
    save_lookup_table(lookup_df, LOOKUP_TABLE_PATH)

    # Filter datasets for output based on TARGET_MODALITIES
    relevant_datasets_for_output = []
    if not lookup_df.empty:
        for dataset_name, row in lookup_df.iterrows():
            if pd.isna(row['modalities']) or row['modalities'] == '':
                repo_modalities = []
            else:
                repo_modalities = [m.strip() for m in str(row['modalities']).split(',')]

            if any(tm in repo_modalities for tm in TARGET_MODALITIES):
                relevant_datasets_for_output.append(dataset_name)

    logging.info(f"Found {len(relevant_datasets_for_output)} datasets matching target modalities "
                 f"({', '.join(TARGET_MODALITIES)}) from lookup table.")

    if args.output_file:
        logging.info(f"Saving {len(relevant_datasets_for_output)} relevant dataset names to {args.output_file}...")
        try:
            with open(args.output_file, 'w') as f:
                for dataset_name in sorted(relevant_datasets_for_output):
                    f.write(f"{dataset_name}\n")
            logging.info(f"Successfully saved relevant dataset names to {args.output_file}")
        except IOError as e:
            logging.error(f"Error writing to output file {args.output_file}: {e}")
    else:
        logging.info("No output file specified. Filtered dataset names will not be saved to a file.")

    logging.info("Dataset discovery process completed.")


if __name__ == "__main__":
    main()
