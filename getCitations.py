from scholarly import scholarly
from scholarly import ProxyGenerator
import pandas as pd


def get_working_proxy():
    success = False
    while not success:
        pg = ProxyGenerator()
        # This is a PAID API key specific to the NEMAR project, please do NOT share
        success = pg.ScraperAPI("2b1a9b9f4327a5bec275d0261231886b")
        # success = pg.FreeProxies()
        # Luminati did not work, it connects, but does not return any results
        # success = pg.Luminati(usr='brd-customer-hl_237c9c0b-zone-residential',
        #                       passwd='eu7qo5tid82s', proxy_port=22225)
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
    citations = pd.DataFrame(columns=['title', 'author', 'venue', 'year', 'url', 'cited_by', 'bib'])
    for i in range(num_cites):
        try:
            entry = scholarly.search_pubs(dataset, start_index=i)
        except:
            # likely the proxy is not working, so we need to get a new one
            print("Failed to connected, retrying one more time...")
            get_working_proxy()
            entry = scholarly.search_pubs(dataset, start_index=i)

        entry = scholarly.fill(next(entry))  # This is the ith result
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

        # Check the author list, replace 'and' with ';' Then, if there are more than 3 authors, replace the last
        # 'and' with ', et al.'
        if entry['bib']['author'] != 'n/a':
            entry['bib']['author'] = entry['bib']['author'].replace(' and', ';')
            if entry['bib']['author'].count(';') > 3:
                entry['bib']['short_author'] = '; '.join(entry['bib']['author'].rsplit(';')[0:3]) + '; et al.'

        # Add the entry to the data frame
        citations = pd.concat([citations,
                               pd.DataFrame.from_records([
                                   {'title': entry['bib']['title'],
                                    'author': entry['bib']['short_author'],
                                    'venue': entry['bib']['venue'],
                                    'year': entry['bib']['pub_year'],
                                    'url': entry['pub_url'],
                                    'cited_by': entry['num_citations'],
                                    'bib': entry['bib']}])
                               ], ignore_index=True)
    return citations
