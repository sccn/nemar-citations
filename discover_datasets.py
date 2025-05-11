"""
Script to discover datasets from the OpenNeuroDatasets GitHub organization
that contain EEG, iEEG, or MEG data, based on BIDS directory structures.
"""

import argparse
import os
import time
import logging
import requests  # Using requests for simplicity, consider httpx for async later if needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Outputs to console
        # Optionally add logging.FileHandler("discover_datasets.log")
    ]
)
logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
TARGET_ORG = "OpenNeuroDatasets"  # The organization to scan
# Max items per page for GitHub API
# https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api?apiVersion=2022-11-28#changing-the-number-of-items-per-page
DEFAULT_PER_PAGE = 100

# BIDS modalities to search for
TARGET_MODALITIES = ["eeg", "ieeg", "meg"]


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
            logger.debug(f"Rate limit: {remaining}/{limit} remaining. Resets at {datetime.fromtimestamp(reset_time)}.")
            if remaining < 20:  # Be conservative
                wait_time = max(0, reset_time - time.time()) + 15  # Add a small buffer
                logger.warning(f"Approaching rate limit ({remaining} remaining). Waiting for {wait_time:.2f} seconds.")
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
    Checks a given repository for specified BIDS modalities (eeg, ieeg, meg).

    Args:
        repo_name (str): The name of the repository.
        org_name (str): The name of the organization owning the repository.
        headers (dict): Headers for GitHub API requests (including auth).

    Returns:
        list[str]: A list of found target modalities in the repository (e.g., ["eeg", "meg"]).
                   Returns an empty list if no target modalities are found or if errors occur.
    """
    found_modalities_in_repo = set()
    logger.info(f"Checking repository: {org_name}/{repo_name} for BIDS modalities ({', '.join(TARGET_MODALITIES)})...")

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
            logger.debug(f"  Found subject directory: {subject_dir_name} in {repo_name}")

            # 2. List contents of this subject directory to find modality directories
            subject_contents_url = item['url']  # API URL for subject directory contents
            subject_response = get_github_api_response(subject_contents_url, headers)

            if not (subject_response and subject_response.status_code == 200):
                logger.warning(f"Could not list contents for {subject_dir_name} in {repo_name}. Skipping this sub-dir.")
                continue

            modalities_in_subj_dir = set()
            for sub_item in subject_response.json():
                if sub_item['type'] == 'dir' and sub_item['name'] in TARGET_MODALITIES:
                    logger.info(
                        f"    Found modality directory: {sub_item['name']} "
                        f"in {subject_dir_name} of {repo_name}!"
                    )
                    modalities_in_subj_dir.add(sub_item['name'])
                    found_modalities_in_repo.add(sub_item['name'])

            # Optimization: If all target modalities are found within one subject,
            # or if we just need to confirm *any* modality, we could break early.
            # For now, let's check one subject directory thoroughly for its modalities.
            # If we found any modalities in this subject dir, we can often assume BIDS structure is present.
            # We only need to check one subject dir to confirm presence for now, for efficiency.
            if modalities_in_subj_dir:
                logger.debug(
                    f"  Finished checking subject directory {subject_dir_name}. "
                    f"Found modalities: {modalities_in_subj_dir}"
                )
                # We've confirmed modalities in one subject dir, which is enough to classify the repo.
                # We return all unique modalities found across all subject dirs checked (currently just one).
                return list(found_modalities_in_repo)
            else:
                logger.debug(f"  No target modalities found in subject directory: {subject_dir_name}")
            # Only check the first subject directory found to save API calls
            # If this first sub-dir doesn't have modalities, we assume the repo isn't structured as we need
            # or doesn't contain the target modalities in a representative way.
            logger.info(
                f"Checked first subject directory ({subject_dir_name}) in {repo_name}, "
                f"no target modalities found there. Concluding for this repo."
            )
            return []  # Return empty if first subject dir has no target modalities

    if subject_dirs_found == 0:
        logger.info(f"No 'sub-' directories found in the root of {repo_name}.")

    return list(found_modalities_in_repo)  # Should be empty if we exited early or no sub-dirs


def main():
    """Main function to orchestrate dataset discovery."""
    parser = argparse.ArgumentParser(description="Discover OpenNeuro datasets with specific BIDS modalities.")
    parser.add_argument("--output-file", help="Path to save the list of discovered dataset names.")
    parser.add_argument(
        "--max-repos",
        type=int,
        default=None,
        help="Maximum number of repositories to process (for testing)."
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

    all_repositories = []
    url = f"https://api.github.com/orgs/{TARGET_ORG}/repos?type=public&per_page={DEFAULT_PER_PAGE}"
    page_num = 1

    while url:
        if args.max_repos is not None and len(all_repositories) >= args.max_repos:
            logging.info(f"Reached max_repos limit of {args.max_repos}. Stopping repository fetching.")
            break
        logging.info(f"Fetching page {page_num} of repositories from {url.split('?')[0]}...")
        response_data = get_github_api_response(url, headers)
        if not response_data:  # This now assumes get_github_api_response returns None on critical failure
            logging.error("Failed to fetch repositories or hit rate limit after checks in get_github_api_response.")
            break

        # Ensure response_data is a dictionary (parsed JSON) if it's not None
        # The original get_github_api_response returns a Response object or None.
        # Let's adjust to work with the structure from previous edits where response_data holds the parsed json or error info
        
        # This block needs to be re-evaluated based on actual return type of get_github_api_response
        # For now, assuming previous tool edit correctly made response_data a dict with 'data' and 'links'
        # or that get_github_api_response was changed to return such a dict.
        # If get_github_api_response returns a requests.Response object:
        if isinstance(response_data, requests.Response):
             if response_data.status_code == 200:
                 try:
                     actual_data = response_data.json()
                     page_repos = actual_data
                     links_header = requests.utils.parse_header_links(response_data.headers.get('Link', ''))
                     next_url = None
                     for link_info in links_header:
                         if link_info.get('rel') == 'next':
                             next_url = link_info['url']
                             break
                     current_url_links = {'next': {'url': next_url}} if next_url else {} # Mimic structure
                 except ValueError: #Includes JSONDecodeError
                     logging.error("Failed to decode JSON from successful API response.")
                     break
             else:
                 logging.error(f"GitHub API request failed with status {response_data.status_code}. Response: {response_data.text[:200]}")
                 break
        elif response_data is None: # Explicit None means critical error from get_github_api_response
            break # Already logged in get_github_api_response
        else: # Assuming response_data is already a dict from a previous version of get_github_api_response
             page_repos = response_data.get("data", [])
             current_url_links = response_data.get("links", {})


        if not isinstance(page_repos, list):
            logging.error(f"Expected a list of repositories, but got {type(page_repos)}. Response: {page_repos}")
            break

        all_repositories.extend(page_repos)
        logging.info(
            f"Fetched {len(page_repos)} repositories on this page. "
            f"Total fetched so far: {len(all_repositories)}."
        )

        if "next" in current_url_links and "url" in current_url_links["next"]:
            url = current_url_links["next"]["url"]
            page_num += 1
        else:
            url = None

        # Optional: add a small delay to be extremely cautious with API rate limits,
        # though get_github_api_response handles explicit limits
        # time.sleep(0.1)

    logging.info(f"Total repositories fetched: {len(all_repositories)}")
    if args.max_repos is not None:
        all_repositories = all_repositories[:args.max_repos]
        logging.info(f"Processing the first {len(all_repositories)} repositories due to --max-repos limit.")

    identified_datasets_info = []
    for repo in all_repositories:
        repo_name = repo.get("name")
        if not repo_name:
            logging.warning(f"Repository found without a name: {repo.get('html_url')}. Skipping.")
            continue

        logging.debug(f"Checking repository: {repo_name}")
        found_modalities = check_repository_for_modalities(repo_name, TARGET_ORG, headers)
        if found_modalities:
            logging.info(f"Relevant dataset {repo_name} found with modalities: {', '.join(found_modalities)}")
            identified_datasets_info.append({"name": repo_name, "modalities": found_modalities})
        else:
            logging.debug(f"No target modalities found in {repo_name}")

    logging.info(f"Identified {len(identified_datasets_info)} relevant datasets.")

    if args.output_file:
        logging.info(f"Saving discovered dataset names to {args.output_file}...")
        try:
            with open(args.output_file, 'w') as f:
                for dataset_info in identified_datasets_info:
                    f.write(f"{dataset_info['name']}\\n")
            logging.info(f"Successfully saved {len(identified_datasets_info)} dataset names to {args.output_file}")
        except IOError as e:
            logging.error(f"Error writing to output file {args.output_file}: {e}")
    else:
        logging.info(
            "No output file specified. Discovered dataset names will not be saved to a file. "
            "Log will contain the list."
        )

    logging.info("Dataset discovery process completed.")


if __name__ == "__main__":
    from datetime import datetime  # Imported here for rate limit logging only for now
    main() 