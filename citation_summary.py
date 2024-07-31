# Description: This script reads the citation data for each dataset and summarizes the number of citations
# and cumulative citations to papers in each dataset.
#
# (c) Seyed Yahya Shirazi, 2024, SCCN, INC, UCSD

# %% Load the necessary libraries
import pandas as pd
from os import listdir

# %% List of file paths for all datasets
# find path to the datasets pickle files. They are in the citations folder
file_paths = ['citations/' + f for f in listdir('citations') if f.endswith('.pkl')]

# %% Load the datasets
# Create an empty list to hold dataframes
dataframes = []

# Load each file into a dataframe and add it to the list
for file in file_paths:
    df = pd.read_pickle(file)
    dataframes.append(df)

# %% Process the datasets
# Initialize a dictionary to hold the results
results = {'Dataset': [], 'Number of Citations': [], 'Cumulative Citations to Papers': []}

# Process each dataframe
for file_path, df in zip(file_paths, dataframes):
    dataset_name = file_path.split('/')[-1].split('.')[0]
    number_of_citations = len(df)
    cumulative_citations = df['cited_by'].sum()

    results['Dataset'].append(dataset_name)
    results['Number of Citations'].append(number_of_citations)
    results['Cumulative Citations to Papers'].append(cumulative_citations)

# Convert the results dictionary to a dataframe
results_df = pd.DataFrame(results)

# %% Save the results
# Save the dataframe to a CSV file (optional)
results_df.to_csv('citations/dataset_citations_analysis.csv', index=False)
