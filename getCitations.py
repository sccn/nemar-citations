"""
This module provides methods to retrieve citation information for a given dataset using the Google Scholar API.

Methods:
- get_working_proxy: Retrieves a working proxy for making API requests.
- get_citation_numbers: Retrieves the total number of citations for a given dataset.
- get_citations: Retrieves the detailed citation information for a given dataset.

Dependencies:
- scholarly: A Python library for interacting with the Google Scholar API.
- pandas: A data manipulation library for creating and manipulating dataframes.

Note: The 'get_working_proxy' function requires a paid API key specific to the NEMAR project.
Please do NOT share this key with anyone outside the project team.

Usage:
1. Import the module using the 'import' statement.
2. Call the 'get_working_proxy' function to initialize the proxy.
3. Use the 'get_citation_numbers' function to retrieve the total number of citations for a dataset.
4. Use the 'get_citations' function to retrieve detailed citation information for a dataset.

(c) 2024, Seyed Yahya Shirazi
"""

from scholarly import scholarly
from scholarly import ProxyGenerator
import pandas as pd
import os


def get_working_proxy(method: str = 'ScraperAPI'):
    success = False
    scraper_api_key = None

    if method == 'ScraperAPI':
        scraper_api_key = os.environ.get('SCRAPERAPI_KEY')
        if not scraper_api_key:
            print("ERROR: SCRAPERAPI_KEY environment variable not set.")
            print("This key is required for the ScraperAPI method.")
            print("Please set the SCRAPERAPI_KEY environment variable and try again.")
            return
    
    while not success:
        pg = ProxyGenerator()
        if method == 'ScraperAPI':
            if not scraper_api_key:
                print("ERROR: ScraperAPI method chosen but SCRAPERAPI_KEY is missing.")
                return

            print("Attempting to use ScraperAPI with key from environment variable...")
            success = pg.ScraperAPI(scraper_api_key)
        elif method == 'Luminati':
            success = pg.FreeProxies()
            # Luminati did not work, it connects, but does not return any results
            success = pg.Luminati(usr='brd-customer-hl_237c9c0b-zone-residential',
                                  passwd='eu7qo5tid82s', proxy_port=22225)
        else:
            # Try free proxies
            success = pg.FreeProxies()

        if success:
            scholarly.use_proxy(pg)


def get_citation_numbers(dataset: str) -> int:

    return scholarly.search_pubs(dataset).total_results


def get_citations(dataset: str, num_cites: int,
                  year_low: int = None, year_high: int = None, start_index: int = 0,
                  citations: pd.DataFrame = None) -> pd.DataFrame:
    """
    Returns a dataframe of the citations for a given dataset
    """
    if num_cites is None:
        num_cites = get_citation_numbers(dataset)

    # Run the search_pubs function with the dataset name, and get the ith result, sorted by year
    if citations is None:
        citations = pd.DataFrame(columns=['title', 'author', 'venue', 'year', 'url', 'cited_by', 'bib'])
    for i in range(num_cites):
        try:
            entry = scholarly.search_pubs(dataset, start_index=i + start_index, year_low=year_low, year_high=year_high)
        except Exception:
            # likely the proxy is not working, so we need to get a new one
            print("Failed to connected, retrying one more time...")
            get_working_proxy()
            entry = scholarly.search_pubs(dataset, start_index=i)

        entry = next(entry)  # This is the ith result, do not use fill() command (very API expensive)
        entry_fields = entry.keys()
        bib_fields = entry['bib'].keys()
        # Check if all expected fields are present, if not, add n/a to the dataframe
        if 'pub_url' not in entry_fields:
            entry['pub_url'] = 'n/a'
        if 'num_citations' not in entry_fields:
            entry['num_citations'] = 'n/a'
        if 'bib' not in entry_fields:
            entry['bib'] = 'n/a'
        else:
            if 'title' not in bib_fields:
                entry['bib']['title'] = 'n/a'
            if 'author' not in bib_fields:
                entry['bib']['author'] = 'n/a'
            if 'venue' not in bib_fields:
                entry['bib']['venue'] = 'n/a'
            if 'pub_year' not in bib_fields:
                entry['bib']['pub_year'] = 'n/a'

        # Check the venue, if it is not "na", then check if the name contains "...",
        # then retrieve the name using the fill() command
        if entry['bib']['venue'] != 'n/a':
            if "…" in entry['bib']['venue']:
                authors = entry['bib']['author']  # save the author list as it will be expanded
                filled_entry = scholarly.fill(entry)
                entry['bib']['author'] = authors
                # check if the "journal" or "conference" key is present, replace the venue with the name
                if 'journal' in filled_entry['bib']:
                    entry['bib']['venue'] = filled_entry['bib']['journal']
                elif 'conference' in filled_entry['bib']:
                    entry['bib']['venue'] = filled_entry['bib']['conference']
                elif 'booktitle' in filled_entry['bib']:
                    entry['bib']['venue'] = filled_entry['bib']['booktitle']
                else:
                    print('cannnot fill the venue for ' + entry['bib']['title'] + ' in ' + dataset)

        # join the author list into a string
        entry['bib']['author'] = ', '.join(entry['bib']['author'])

        # If there are more than 3 authors, replace the last
        # 'and' with ', et al.'
        if entry['bib']['author'] != 'n/a':
            if entry['bib']['author'].count(',') > 3:
                entry['bib']['short_author'] = ', '.join(entry['bib']['author'].rsplit(', ')[0:3]) + ', et al.'
            else:
                entry['bib']['short_author'] = entry['bib']['author']

        # Add the entry to the data frame
        citations = pd.concat([citations,
                               pd.DataFrame.from_records([
                                   {'title': entry['bib']['title'],
                                    'author': entry['bib']['author'],
                                    'venue': entry['bib']['venue'],
                                    'year': entry['bib']['pub_year'],
                                    'url': entry['pub_url'],
                                    'cited_by': entry['num_citations'],
                                    'bib': entry['bib']}])
                               ], ignore_index=True)
    return citations
