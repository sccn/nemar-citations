from scholarly import scholarly
from scholarly import ProxyGenerator
import pandas as pd


def get_working_proxy():
    success = False
    while not success:
        pg = ProxyGenerator()
        success = pg.ScraperAPI("6f1f6b38b5f6b8e4870be1f20df9e4f0")
        if success:
            scholarly.use_proxy(pg)


def get_citation_numbers(dataset: str) -> int:

    return scholarly.search_pubs(dataset).total_results


def get_citations(dataset: str, num_cites: int) -> pd.DataFrame:
    """
    Returns a dataframe of the citations for a given dataset
    """
    if num_cites is None:
        num_cites = get_citation_numbers(dataset)

    # Run the search_pubs function with the dataset name, and get the ith result, sorted by year
    citations = pd.DataFrame(columns=['title', 'author', 'year', 'url', 'cited_by', 'bib'])
    for i in range(num_cites):
        try:
            entry = scholarly.search_pubs(dataset, start_index=i)
        except:
            # likely the proxy is not working, so we need to get a new one
            print("Failed to connected, retrying one more time...")
            get_working_proxy()
            entry = scholarly.search_pubs(dataset, start_index=i)

        entry = next(entry)  # This is the ith result
        citations = citations.append({'title': entry['bib']['title'],
                                      'author': entry['bib']['author'],
                                      'year': entry['bib']['pub_year'],
                                      'url': entry['pub_url'],
                                      'cited_by': entry['num_citations'],
                                      'bib': entry['bib']}, ignore_index=True)
    return citations
