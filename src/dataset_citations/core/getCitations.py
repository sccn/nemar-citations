"""
This module provides methods to retrieve citation information for a given dataset using the Google Scholar API.

Methods:
- get_working_proxy: Retrieves a working proxy for making API requests.
- get_citation_numbers: Retrieves the total number of citations for a given dataset.
- get_citations: Retrieves the detailed citation information for a given dataset.

Dependencies:
- scholarly: A Python library for interacting with the Google Scholar API.
- pandas: A data manipulation library for creating and manipulating dataframes.
- os: For environment variable access.
- logging: For logging messages.
- time: For adding delays in retries.

Note:
- The 'get_working_proxy' function, when using the 'ScraperAPI' method, requires the
  SCRAPERAPI_KEY environment variable to be set with a valid API key.
- Functions interacting with Google Scholar are subject to network availability and API changes.

Usage:
1. Ensure SCRAPERAPI_KEY environment variable is set if using ScraperAPI method.
2. Import the module: `import getCitations as gc`
3. Initialize the proxy if needed by other functions: `gc.get_working_proxy()`
4. Use functions like `gc.get_citation_numbers('dataset_id')` or `gc.get_citations('dataset_id', count)`.

(c) 2024, Seyed Yahya Shirazi
"""

from scholarly import scholarly
from scholarly import ProxyGenerator
import pandas as pd
import os
import logging
import time
from typing import Optional

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_working_proxy(method: str = "ScraperAPI") -> None:
    """
    Sets up and validates a proxy for use with the scholarly library.

    This function attempts to configure a proxy using the specified method.
    It retries on failure with a delay. Currently supports 'ScraperAPI'
    (requires SCRAPERAPI_KEY environment variable) and 'Luminati'.
    If successful, `scholarly.use_proxy(pg)` is called.

    Args:
        method (str, optional): The proxy method to use.
                                Defaults to 'ScraperAPI'.
                                Other options include 'Luminati' or 'FreeProxies'.

    Returns:
        None. The function aims to configure the global scholarly proxy.
        It will log errors if it fails to set up a proxy after retries
        or if necessary configurations (like API key) are missing.
    """
    success: bool = False
    scraper_api_key: Optional[str] = None

    if method == "ScraperAPI":
        scraper_api_key = os.environ.get("SCRAPERAPI_KEY")
        if not scraper_api_key:
            print("ERROR: SCRAPERAPI_KEY environment variable not set.")
            print("This key is required for the ScraperAPI method.")
            print("Please set the SCRAPERAPI_KEY environment variable and try again.")
            return

    while not success:
        pg = ProxyGenerator()
        if method == "ScraperAPI":
            if not scraper_api_key:
                # This condition should ideally be caught by the initial check
                # but as a safeguard during the loop if method is ScraperAPI.
                logging.error(
                    "ScraperAPI method chosen but SCRAPERAPI_KEY is missing during proxy setup loop."
                )
                return  # Exit if key is missing

            # This is a PAID API key specific to the NEMAR project, please do NOT share
            # Key is now fetched from environment variable SCRAPERAPI_KEY
            logging.info(
                "Attempting to use ScraperAPI with key from environment variable..."
            )
            try:
                success = pg.ScraperAPI(scraper_api_key)
                if not success:
                    logging.warning(
                        "ScraperAPI proxy setup failed with key. Will retry."
                    )
            except Exception as e:
                logging.error(
                    f"Exception during ScraperAPI setup with key: {e}. Will retry."
                )
                success = False  # Ensure success is false to retry

        elif method == "Luminati":
            success = pg.FreeProxies()
            # Luminati did not work, it connects, but does not return any results
            success = pg.Luminati(
                usr="brd-customer-hl_237c9c0b-zone-residential",
                passwd="eu7qo5tid82s",
                proxy_port=22225,
            )
        else:
            # Try free proxies
            success = pg.FreeProxies()

        if success:
            scholarly.use_proxy(pg)
            logging.info(f"Successfully set up proxy using {method}.")
        else:
            # Add a small delay before retrying to avoid spamming proxy services if continuously failing
            logging.warning(
                f"Proxy setup failed with {method}. Retrying in 5 seconds..."
            )
            time.sleep(5)


def get_citation_numbers(dataset: str) -> int:
    """
    Retrieves the total number of citations for a given dataset ID using Google Scholar.

    Args:
        dataset (str): The dataset ID or search query string for Google Scholar.

    Returns:
        int: The total number of citations found. Returns 0 if no results are found
             or if a network error occurs during the search.

    Raises:
        TypeError: If dataset is None or not a string
        ValueError: If dataset is an empty string
    """
    # Validate input
    if dataset is None:
        raise TypeError("Dataset cannot be None")
    if not isinstance(dataset, str):
        raise TypeError("Dataset must be a string")
    if dataset == "":
        return 0  # Empty string is handled gracefully

    try:
        search_results = scholarly.search_pubs(dataset)
        if (
            search_results
            and hasattr(search_results, "total_results")
            and search_results.total_results is not None
        ):
            total_results = int(search_results.total_results)
            logging.info(f"Found {total_results} citation(s) for dataset: {dataset}")
            return total_results
        else:
            logging.warning(
                f"No search results from scholarly.search_pubs for dataset: {dataset}"
            )
            return 0
    except (ConnectionError, TimeoutError, OSError) as e:
        # Handle network-related errors gracefully
        logging.error(f"Network error getting citation number for {dataset}: {e}")
        return 0
    except Exception as e:
        # Log other errors but don't suppress them
        logging.error(f"Error getting citation number for {dataset}: {e}")
        raise


def get_citations(
    dataset: str,
    num_cites: Optional[int],
    year_low: Optional[int] = None,
    year_high: Optional[int] = None,
    start_index: int = 0,
    citations: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns a dataframe of the citations for a given dataset.

    Fetches detailed citation information for a specified number of citations
    for the given dataset ID. It handles potential errors during fetching,
    including attempting to refresh the proxy if issues occur.

    Args:
        dataset (str): The dataset ID or search query string.
        num_cites (int): The number of citations to retrieve.
        year_low (int, optional): The earliest publication year to include. Defaults to None.
        year_high (int, optional): The latest publication year to include. Defaults to None.
        start_index (int, optional): The starting index for fetching citations. Defaults to 0.
        citations (pd.DataFrame, optional): An existing DataFrame to append citations to.
                                            If None, a new DataFrame is created.
                                            Columns: ['title', 'author', 'venue', 'year', 'url', 'cited_by', 'bib'].

    Returns:
        pd.DataFrame: A DataFrame containing the fetched citation details.
                      Returns an empty DataFrame or the original DataFrame if num_cites is 0
                      or if errors prevent fetching any new citations.
    """
    if num_cites is None or num_cites == 0:  # Added check for num_cites being 0
        logging.info(
            f"Number of citations to fetch for {dataset} is None or 0. Returning existing/empty DataFrame."
        )
        return (
            citations
            if citations is not None
            else pd.DataFrame(
                columns=["title", "author", "venue", "year", "url", "cited_by", "bib"]
            )
        )

    # Run the search_pubs function with the dataset name, and get the ith result, sorted by year
    if citations is None:
        citations = pd.DataFrame(
            columns=["title", "author", "venue", "year", "url", "cited_by", "bib"]
        )
    for i in range(num_cites):
        try:
            entry_search = scholarly.search_pubs(
                dataset,
                start_index=i + start_index,
                year_low=year_low,
                year_high=year_high,
            )
            entry = next(entry_search)
        except StopIteration:
            logging.warning(
                f"StopIteration: Expected {num_cites} citations for {dataset},"
                f"but found fewer after index {i + start_index - 1}. Processing what was found."
            )
            break  # Stop if no more entries are found
        except Exception as e:
            logging.error(
                f"Failed to get publication entry {i + start_index} for {dataset}."
                f"Attempting to get new proxy. Error: {e}"
            )
            get_working_proxy()  # Attempt to refresh proxy
            try:
                entry_search = scholarly.search_pubs(
                    dataset,
                    start_index=i + start_index,
                    year_low=year_low,
                    year_high=year_high,
                )
                entry = next(entry_search)
                logging.info(
                    f"Successfully retrieved entry {i + start_index} for {dataset} after proxy refresh."
                )
            except Exception as e2:
                logging.error(
                    f"Still failed to get publication entry {i + start_index} for {dataset}"
                    f"after proxy refresh. Skipping this entry. Error: {e2}"
                )
                continue  # Skip this entry and try the next one

        # entry = next(entry)  # This is the ith result, do not use fill()
        # command (very API expensive) - already done above
        if not entry:  # Should not happen if next() was successful, but as a safeguard
            logging.warning(
                f"Entry {i + start_index} for {dataset} was unexpectedly None. Skipping."
            )
            continue

        entry_fields = entry.keys()
        bib_fields = entry["bib"].keys()
        # Check if all expected fields are present, if not, add n/a to the dataframe
        if "pub_url" not in entry_fields:
            entry["pub_url"] = "n/a"
        if "num_citations" not in entry_fields:
            entry["num_citations"] = "n/a"
        if "bib" not in entry_fields:
            entry["bib"] = "n/a"
        else:
            if "title" not in bib_fields:
                entry["bib"]["title"] = "n/a"
            if "author" not in bib_fields:
                entry["bib"]["author"] = "n/a"
            if "venue" not in bib_fields:
                entry["bib"]["venue"] = "n/a"
            if "pub_year" not in bib_fields:
                entry["bib"]["pub_year"] = "n/a"

        # Check the venue, if it is not "na", then check if the name contains "...",
        # then retrieve the name using the fill() command
        if entry["bib"]["venue"] != "n/a":
            if "…" in entry["bib"]["venue"]:
                authors = entry["bib"][
                    "author"
                ]  # save the author list as it will be expanded
                filled_entry = scholarly.fill(entry)
                entry["bib"]["author"] = authors
                # check if the "journal" or "conference" key is present, replace the venue with the name
                if "journal" in filled_entry["bib"]:
                    entry["bib"]["venue"] = filled_entry["bib"]["journal"]
                elif "conference" in filled_entry["bib"]:
                    entry["bib"]["venue"] = filled_entry["bib"]["conference"]
                elif "booktitle" in filled_entry["bib"]:
                    entry["bib"]["venue"] = filled_entry["bib"]["booktitle"]
                else:
                    print(
                        "cannnot fill the venue for "
                        + entry["bib"]["title"]
                        + " in "
                        + dataset
                    )

        # join the author list into a string
        entry["bib"]["author"] = ", ".join(entry["bib"]["author"])

        # If there are more than 3 authors, replace the last
        # 'and' with ', et al.'
        if entry["bib"]["author"] != "n/a":
            if entry["bib"]["author"].count(",") > 3:
                entry["bib"]["short_author"] = (
                    ", ".join(entry["bib"]["author"].rsplit(", ")[0:3]) + ", et al."
                )
            else:
                entry["bib"]["short_author"] = entry["bib"]["author"]

        # Add the entry to the data frame
        citations = pd.concat(
            [
                citations,
                pd.DataFrame.from_records(
                    [
                        {
                            "title": entry["bib"]["title"],
                            "author": entry["bib"]["author"],
                            "venue": entry["bib"]["venue"],
                            "year": entry["bib"]["pub_year"],
                            "url": entry["pub_url"],
                            "cited_by": entry["num_citations"],
                            "bib": entry["bib"],
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    return citations
