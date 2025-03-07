"""
This script updates the citation numbers and citation lists for the datasets
in the datasets.csv file. It is meant to be run periodically to keep the
citations up to date.
(c) 2024, Seyed Yahya Shirazi
"""
# %% initialize
import pandas as pd
from datetime import datetime
import getCitations as gc
gc.get_working_proxy()  # initialize the proxy

UPDATE_NUM_CITES = True
UPDATE_CITE_LIST = True

# %% get the list of datasets and citation numbers
datasets = pd.read_csv('citations/directories_list_jan25.txt', header=None)[0].tolist()
num_cites = pd.read_csv('citations/citations_25102024.csv', index_col='dataset_id')
num_cites = num_cites.iloc[:, 0]

# %% if we need to update the citation numbers
if UPDATE_NUM_CITES:
    num_cites_new = pd.Series(name='number_of_citations')
    for i, d in enumerate(datasets):
        num_cites_new[d] = gc.get_citation_numbers(d)

    # compare the old and new citation numbers
    num_cites_diff = num_cites_new.sub(num_cites, fill_value=0)
    UPDATE_FLAG = num_cites_diff.sum() != 0

    if UPDATE_FLAG:
        # save the new citation numbers
        num_cites_new.to_csv('citations/citations_' + datetime.today().strftime('%d%m%Y') + '.csv',
                             index_label='dataset_id')

        # Get the list of datasets that have been updated
        datasets_updated = num_cites_diff.drop(index=num_cites_diff[num_cites_diff < 1].index).index.tolist()
    else:
        print('No new citations found')

# %% if we need to update the citation list
if UPDATE_CITE_LIST:
    if UPDATE_FLAG:
        unsucessful = []
        successful_updates = {}  # Changed to dict to store both dataset and citation count
        # get the citations for the updated datasets
        for d in datasets_updated:
            try:
                citations = gc.get_citations(d, int(num_cites_new[d]))
                citations.to_pickle('citations/' + d + '.pkl')
                successful_updates[d] = len(citations)  # Store the actual number of citations retrieved
                print('Completed citations for ' + d)
            except Exception:
                unsucessful.append(d)
                print('Failed to get citations for ' + d)

        # Only save the list of datasets that were successfully updated
        if successful_updates:
            output_file = 'citations/updated_datasets_' + datetime.today().strftime('%d%m%Y') + '.csv'
            pd.Series(successful_updates).to_csv(output_file, index=True)  # index=True to save dataset IDs
        if unsucessful:
            print(f"Failed to get citations for {len(unsucessful)} datasets: {', '.join(unsucessful)}")
    else:
        print('No new citations found')
