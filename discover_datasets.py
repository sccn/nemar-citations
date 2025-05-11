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
    repos_url = f"{GITHUB_API_BASE_URL}/orgs/{TARGET_ORG}/repos?per_page=5&page=1" # Get first 5 for testing
    logger.info(f"Attempting to list repositories from {TARGET_ORG}...")
    
    response = get_github_api_response(repos_url, headers)

    if response and response.status_code == 200:
        repositories = response.json()
        logger.info(f"Successfully fetched {len(repositories)} repositories (sample):")
        for repo in repositories:
            logger.info(f"  - {repo['name']} (ID: {repo['id']})")
        # TODO: Further processing will go here in subsequent subtasks
    elif response: # Response object exists but status code was not 200
        logger.error(f"Failed to list repositories. Status code: {response.status_code}. Response: {response.text[:200]}")
    else: # No response object means a requests.exceptions.RequestException likely occurred
        logger.error("Failed to list repositories due to a request exception (see previous logs).")
    
    logger.info(f"Dataset discovery script finished (subtask 2.1 basic connection test). Output file: {args.output_file}")


if __name__ == "__main__":
    from datetime import datetime # Imported here for rate limit logging only for now
    main() 