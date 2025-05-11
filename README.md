# Dataset Citations
This repository contains methods to retrieve citations to NEMAR.org datasets.
To use the methods, you need to have an API key to scraperAPI, which you can get for free at https://www.scraperapi.com/.

## Warning
The contained API keys are paid through the NEMAR project. Please do not use them for other purposes.

## Usage

The primary script for updating citations is `update_citations.py`. It now requires command-line arguments to specify input files and behavior.

### Prerequisites

1.  **Python Environment**: Ensure you have Python 3 installed along with the necessary libraries. You can typically install them using pip:
    ```bash
    pip install pandas scholarly # Add any other specific dependencies if introduced
    ```
2.  **ScraperAPI Key**: The system uses ScraperAPI to fetch citation data from Google Scholar. You need to obtain an API key from [ScraperAPI](https://www.scraperapi.com/).
    Once you have the key, you **must** set it as an environment variable named `SCRAPERAPI_KEY`:
    ```bash
    export SCRAPERAPI_KEY="your_actual_api_key_here"
    ```
    On Windows, you might use:
    ```bash
    set SCRAPERAPI_KEY="your_actual_api_key_here"
    ```
    Or set it through your system's environment variable settings.

### Running `update_citations.py`

The script `update_citations.py` is used to fetch and update citation counts and detailed citation lists for a given set of datasets.

**Command-Line Arguments:**

*   `--dataset-list-file FILE_PATH` (Required): Path to a text file containing the list of dataset IDs (one per line) for which to fetch citations. 
    Example: `citations/dataset_ids.txt`
*   `--previous-citations-file FILE_PATH` (Required): Path to a CSV file containing previously fetched citation counts. This file should have a 'dataset_id' column as the index and a column with citation counts. If the file does not exist for a first run, the script will proceed assuming zero previous citations.
    Example: `citations/previous_counts.csv`
*   `--output-dir DIRECTORY_PATH` (Optional): Directory where output files (new citation counts CSV, updated datasets summary CSV, and individual dataset .pkl files) will be saved. 
    Defaults to `citations/`.
*   `--no-update-num-cites`: (Optional Flag) If specified, the script will skip the step of fetching and updating the summary citation *numbers*.
*   `--no-update-cite-list`: (Optional Flag) If specified, the script will skip the step of fetching and saving the detailed citation *lists* (the .pkl files).

**Example Invocation:**

```bash
python update_citations.py \
    --dataset-list-file path/to/your/dataset_list.txt \
    --previous-citations-file path/to/your/previous_citations.csv \
    --output-dir custom_output_directory/
```

To run with default output directory (`citations/`) and update both numbers and lists:
```bash
python update_citations.py \
    --dataset-list-file citations/discovered_datasets_YYYY-MM-DD.txt \
    --previous-citations-file citations/citations_DDMMYYYY.csv
```

### Output Files

Running the script can produce the following files in the specified output directory:

*   `citations_DDMMYYYY.csv`: A CSV file containing the updated total citation counts for each dataset.
*   `updated_datasets_DDMMYYYY.csv`: A CSV file summarizing which datasets had their detailed citation lists updated and how many citations were retrieved for each.
*   `<dataset_id>.pkl`: Pickle files, one for each dataset for which the detailed citation list was successfully fetched and saved. These contain a pandas DataFrame of the citation details.

(Note: `DDMMYYYY` in filenames will be replaced by the current date.)
