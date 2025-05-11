"""
Script to discover datasets from the OpenNeuroDatasets GitHub organization
that contain EEG, iEEG, or MEG data, based on BIDS directory structures.
"""

import argparse
import os
import time
import logging
import requests # Using requests for simplicity, consider httpx for async later if needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Outputs to console
        # Optionally add logging.FileHandler("discover_datasets.log")
    ]
)
logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
TARGET_ORG = "OpenNeuroDatasets" # The organization to scan
# Max items per page for GitHub API
# https://docs.github.com/en/rest/guides/using-pagination-in-the-rest-api?apiVersion=2022-11-28#changing-the-number-of-items-per-page
DEFAULT_PER_PAGE = 100 

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
            if remaining < 20: # Be conservative
                wait_time = max(0, reset_time - time.time()) + 15 # Add a small buffer
                logger.warning(f"Approaching rate limit ({remaining} remaining). Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)
        
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        return response
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - URL: {api_url}")
        if response is not None: # Return response for potential further inspection
            logger.error(f"Response content: {response.text[:500]}") # Log first 500 chars
            return response 
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception occurred: {req_err} - URL: {api_url}")
    return None


def main():
    """Main function to orchestrate dataset discovery."""
    parser = argparse.ArgumentParser(description="Discover BIDS modality datasets from OpenNeuro on GitHub.")
    parser.add_argument(
        "--output-file", 
        default="discovered_datasets.txt", 
        help="Path to the output file where discovered dataset names will be written (one per line)."
    )
    parser.add_argument(
        "--max-repos",
        type=int,
        default=None, # No limit by default
        help="Maximum number of repositories to process (for testing/development)."
    )
    # parser.add_argument(
    #     "--org",
    #     default=TARGET_ORG,
    #     help=f"GitHub organization to scan (default: {TARGET_ORG})"
    # ) # TODO: Make org configurable later if needed

    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set. Please set it to your GitHub Personal Access Token.")
        logger.warning("Proceeding with unauthenticated requests, which are severely rate-limited and may fail.")
        headers = {"Accept": "application/vnd.github.v3+json"}
    else:
        logger.info("Using GITHUB_TOKEN for authenticated requests.")
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    # Initial test: List repositories in the organization
    # repos_url = f"{GITHUB_API_BASE_URL}/orgs/{TARGET_ORG}/repos?per_page=5&page=1" # Get first 5 for testing
    current_repos_url = f"{GITHUB_API_BASE_URL}/orgs/{TARGET_ORG}/repos?per_page={DEFAULT_PER_PAGE}"
    all_repositories = []
    page_num = 1

    logger.info(f"Attempting to list all repositories from {TARGET_ORG} (page by page)...")

    while current_repos_url:
        logger.info(f"Fetching page {page_num} from URL: {current_repos_url}")
        response = get_github_api_response(current_repos_url, headers)

        if response and response.status_code == 200:
            page_repositories = response.json()
            if not page_repositories: # No more repositories on this page, or empty last page
                logger.info("No more repositories found on this page. Assuming end of list.")
                break
            
            all_repositories.extend(page_repositories)
            logger.info(f"Fetched {len(page_repositories)} repositories on this page. Total fetched so far: {len(all_repositories)}.")

            if args.max_repos is not None and len(all_repositories) >= args.max_repos:
                logger.info(f"Reached max_repos limit of {args.max_repos}. Stopping repository fetching.")
                all_repositories = all_repositories[:args.max_repos] # Trim if over limit
                break

            # Check for next page link
            if 'Link' in response.headers:
                links = requests.utils.parse_header_links(response.headers['Link'])
                next_url = None
                for link in links:
                    if link.get('rel') == 'next':
                        next_url = link['url']
                        break
                current_repos_url = next_url
                if current_repos_url:
                    page_num += 1
                else:
                    logger.info("No 'next' link found in Link header. Reached end of repositories.")
                    current_repos_url = None # End loop
            else:
                logger.info("No 'Link' header in response. Assuming single page or end of repositories.")
                current_repos_url = None # End loop
        
        elif response: # Response object exists but status code was not 200
            logger.error(f"Failed to list repositories from {current_repos_url}. Status: {response.status_code}. Resp: {response.text[:200]}")
            current_repos_url = None # Stop on error
            break # Critical error, stop pagination
        else: # No response object means a requests.exceptions.RequestException likely occurred
            logger.error(f"Failed to list repositories from {current_repos_url} due to a request exception. Stopping pagination.")
            current_repos_url = None # Stop on error
            break # Critical error, stop pagination

    logger.info(f"Finished fetching repositories. Total unique repositories found: {len(all_repositories)}.")

    # Log a sample of fetched repositories if any
    if all_repositories:
        logger.info(f"Sample of fetched repositories (up to 5):")
        for repo in all_repositories[:5]: # Log first 5
            logger.info(f"  - {repo['name']} (ID: {repo['id']})")
        # TODO: Further processing will go here in subsequent subtasks
    else:
        logger.warning("No repositories were successfully fetched.")
    
    logger.info(f"Dataset discovery script finished (subtask 2.2 pagination). Output file: {args.output_file}")


if __name__ == "__main__":
    from datetime import datetime # Imported here for rate limit logging only for now
    main() 