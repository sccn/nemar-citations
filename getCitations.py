from scholarly import scholarly
from scholarly import ProxyGenerator
import pandas as pandas


def get_working_proxy():
    success = False
    while not success:
        pg = ProxyGenerator()
        success = pg.ScraperAPI("a1f816f445e51567c8d721966808953a")
        if success:
            scholarly.use_proxy(pg)


def get_citation_numbers(dataset: str) -> int:

    get_working_proxy()
    return scholarly.search_pubs(dataset).total_results


def get_citations(dataset: str, num_cites: int) -> list:
    
    if num_cites is None:
        num_cites = get_citation_numbers(dataset)
    
    get_working_proxy()
    # Run the search_pubs function with the dataset name, and get the ith result, sorted by year
    citations = []
    for i in range(num_cites):
        try:
            citation = scholarly.search_pubs(dataset, start_index=i)
            citations.append(citation)
        except:
            # likely the proxy is not working, so we need to get a new one
            print("Failed to connected, retrying one more time...")
            get_working_proxy()
            citation = scholarly.search_pubs(dataset, start_index=i)
            citations.append(citation)

    return citations
