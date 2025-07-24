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
import citation_utils  # Added for JSON citation format support
import argparse
import os
import logging  # Added import
import concurrent.futures  # Added for parallelism

# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # Create a logger instance for this module


def load_input_data(
        dataset_list_file_path: str, previous_citations_file_path: str
) -> tuple[list | None, pd.Series | None]:
    """
    Loads the list of datasets and previous citation counts from specified files.

    Args:
        dataset_list_file_path (str): Path to the file containing dataset IDs.
        previous_citations_file_path (str): Path to the CSV file with previous citation counts.

    Returns:
        tuple[list | None, pd.Series | None]: A tuple containing:
            - list: List of dataset IDs. None if loading fails.
            - pd.Series: Series of previous citation counts, indexed by dataset_id.
                         An empty Series if the file is not found. None if loading fails otherwise.
    """
    datasets = None
    num_cites_old = None

    try:
        datasets = pd.read_csv(dataset_list_file_path, header=None)[0].tolist()
        if not datasets:
            logger.error(f"Dataset list file is empty: {dataset_list_file_path}")
            return None, None
        logger.info(f"Successfully read {len(datasets)} dataset IDs from {dataset_list_file_path}")
    except FileNotFoundError:
        logger.error(f"Dataset list file not found: {dataset_list_file_path}")
        return None, None
    except Exception as e:
        logger.error(f"Could not read dataset list file: {dataset_list_file_path}. Error: {e}")
        return None, None

    try:
        num_cites_old_df = pd.read_csv(previous_citations_file_path, index_col='dataset_id')
        num_cites_old = num_cites_old_df.iloc[:, 0]
        logger.info(
            f"Successfully read {len(num_cites_old)} entries from previous citations file: "
            f"{previous_citations_file_path}"
        )
    except FileNotFoundError:
        logger.info(
            f"Previous citations file not found: {previous_citations_file_path}. "
            "Starting with no previous counts."
        )
        num_cites_old = pd.Series(name='number_of_citations', dtype='float64')
    except Exception as e:
        logger.error(f"Could not read previous citations file: {previous_citations_file_path}. Error: {e}")
        return datasets, None  # Return datasets if successfully loaded, but num_cites_old failed

    return datasets, num_cites_old


def fetch_citation_count(dataset_id: str, num_cites_old_series: pd.Series) -> tuple[str, int]:
    """Helper function to fetch citation count for a single dataset, for parallel execution."""
    logger.info(f"Fetching citation number for {dataset_id}...")
    try:
        count = gc.get_citation_numbers(dataset_id)
        return dataset_id, count
    except Exception as e:
        logger.error(f"Unexpected error calling gc.get_citation_numbers for {dataset_id}. Error: {e}")
        # Fallback to old count if available, otherwise 0
        return dataset_id, num_cites_old_series.get(dataset_id, 0)


def update_citation_counts(
        datasets: list, num_cites_old: pd.Series, max_workers: int
) -> tuple[pd.Series, pd.Series, list, bool]:
    """
    Updates citation counts for the given list of datasets using parallel execution.

    Args:
        datasets (list): List of dataset IDs to update.
        num_cites_old (pd.Series): Series of old citation counts.
        max_workers (int): Maximum number of worker threads for parallel fetching.

    Returns:
        tuple[pd.Series, pd.Series, list, bool]: A tuple containing:
            - pd.Series: New citation counts.
            - pd.Series: Differences between new and old counts.
            - list: List of dataset IDs that have updated counts (increased or newly added).
            - bool: Flag indicating if any citation counts were updated.
    """
    num_cites_new_dict = {}
    logger.info(f"Updating citation numbers for {len(datasets)} datasets using {max_workers} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each dataset
        future_to_dataset = {
            executor.submit(fetch_citation_count, d, num_cites_old): d for d in datasets
        }
        for i, future in enumerate(concurrent.futures.as_completed(future_to_dataset)):
            dataset_id = future_to_dataset[future]
            try:
                _, count = future.result()
                num_cites_new_dict[dataset_id] = count
                logger.info(f"Completed fetching for {dataset_id} ({i + 1}/{len(datasets)}). Count: {count}")
            except Exception as exc:
                logger.error(f"{dataset_id} generated an exception during fetch_citation_count: {exc}")
                num_cites_new_dict[dataset_id] = num_cites_old.get(dataset_id, 0)  # Fallback

    num_cites_new = pd.Series(num_cites_new_dict, name='number_of_citations', dtype='float64')
    num_cites_new_aligned, num_cites_old_aligned = num_cites_new.align(num_cites_old, join='outer', fill_value=0)
    num_cites_diff = num_cites_new_aligned.sub(num_cites_old_aligned, fill_value=0)

    update_flag = (num_cites_diff != 0).any()
    datasets_updated_for_counts = []

    if update_flag:
        logger.info("New citation counts found. Differences:")
        changed_counts = num_cites_diff[num_cites_diff != 0]
        for dataset_id_changed, diff_value in changed_counts.items():
            old_val = num_cites_old_aligned.get(dataset_id_changed, 'N/A')
            new_val = num_cites_new_aligned.get(dataset_id_changed, 'N/A')
            logger.info(f"  Dataset {dataset_id_changed}: old={old_val}, new={new_val}, diff={diff_value}")

        datasets_updated_for_counts = num_cites_diff[num_cites_diff > 0].index.tolist()
        newly_added_datasets = num_cites_new.index.difference(num_cites_old.index).tolist()

        for d_new in newly_added_datasets:
            if d_new not in datasets_updated_for_counts:
                datasets_updated_for_counts.append(d_new)

        if not datasets_updated_for_counts:
            logger.info("No datasets found with an increase in citations. Update flag might be due to decreases.")
    else:
        logger.info('No new citation counts found or no change in counts.')

    return num_cites_new, num_cites_diff, datasets_updated_for_counts, update_flag


def save_citation_counts(num_cites_new: pd.Series, output_dir: str) -> str | None:
    """Saves the new citation counts to a CSV file."""
    filename = 'citations_' + datetime.today().strftime('%d%m%Y') + '.csv'
    filepath = os.path.join(output_dir, filename)
    try:
        num_cites_new.to_csv(filepath, index_label='dataset_id')
        logger.info(f"Saved new citation counts to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save new citation counts to {filepath}. Error: {e}")
        return None


def fetch_detailed_citations_for_dataset(
        dataset_id: str, num_citations_to_fetch: int
) -> tuple[str, pd.DataFrame | None, str | None]:
    """Helper function to fetch detailed citations for a single dataset, for parallel execution."""
    logger.info(f"Fetching detailed citation list for {dataset_id} ({num_citations_to_fetch} citations)...")
    try:
        citations_df = gc.get_citations(dataset_id, num_citations_to_fetch)
        if citations_df is not None and not citations_df.empty:
            return dataset_id, citations_df, None  # dataset_id, dataframe, error_message
        elif citations_df is None:
            logger.warning(f"gc.get_citations returned None for {dataset_id}.")
            return dataset_id, None, "gc.get_citations returned None"
        else:  # Empty dataframe
            logger.info(f"No citations retrieved by gc.get_citations for {dataset_id} (returned empty).")
            return dataset_id, pd.DataFrame(), None  # Return empty df, no error
    except ValueError as ve:
        logger.error(
            f"ValueError converting citation count for {dataset_id} (value: {num_citations_to_fetch}). Error: {ve}"
        )
        return dataset_id, None, str(ve)
    except Exception as e:
        logger.error(f"Failed to get citation list for {dataset_id}. Error: {e}")
        return dataset_id, None, str(e)


def update_detailed_citation_lists(
        datasets_to_process: list, num_cites_new: pd.Series, output_dir: str, max_workers: int, 
        output_format: str = "both"
) -> tuple[dict, list]:
    """
    Fetches and saves detailed citation lists for specified datasets using parallel execution.
    
    Args:
        datasets_to_process (list): List of dataset IDs to process
        num_cites_new (pd.Series): Series with citation counts
        output_dir (str): Output directory path
        max_workers (int): Maximum number of worker threads
        output_format (str): Output format - "pickle", "json", or "both"
    
    Returns:
        tuple[dict, list]: (successful_updates_details, unsuccessful_list_update)
    """
    unsuccessful_list_update = []
    successful_updates_details = {}
    logger.info(
        f"Processing detailed citation lists for {len(datasets_to_process)} datasets "
        f"using {max_workers} workers: {datasets_to_process}"
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_dataset = {}
        for d in datasets_to_process:
            current_num_cites = num_cites_new.get(d)
            if pd.isna(current_num_cites):
                logger.warning(f"Skipping detailed citation list for {d} as its citation count is NaN.")
                continue
            if int(current_num_cites) == 0:
                logger.info(f"Skipping detailed citation list for {d} as it has 0 citations.")
                successful_updates_details[d] = 0  # Consider 0 citations as a successful (empty) update
                continue

            future_to_dataset[executor.submit(
                fetch_detailed_citations_for_dataset, d, int(current_num_cites)
            )] = d

        for i, future in enumerate(concurrent.futures.as_completed(future_to_dataset)):
            dataset_id = future_to_dataset[future]
            try:
                _, citations_df, error_message = future.result()
                logger.info(
                    f"Completed fetching detailed citations for {dataset_id} "
                    f"({i + 1}/{len(future_to_dataset)})..."
                )

                if error_message:
                    logger.error(f"Error fetching detailed citations for {dataset_id}: {error_message}")
                    unsuccessful_list_update.append(dataset_id)
                    continue

                if citations_df is not None and not citations_df.empty:
                    save_success = False
                    fetch_date = datetime.now()
                    
                    # Save pickle file if requested
                    if output_format in ["pickle", "both"]:
                        output_pkl_path = os.path.join(output_dir, dataset_id + '.pkl')
                        try:
                            citations_df.to_pickle(output_pkl_path)
                            logger.info(
                                f"Saved detailed citations for {dataset_id} ({len(citations_df)} entries) "
                                f"to {output_pkl_path}"
                            )
                            save_success = True
                        except Exception as e_save:
                            logger.error(f"Failed to save pickle for {dataset_id} to {output_pkl_path}. Error: {e_save}")
                    
                    # Save JSON file if requested
                    if output_format in ["json", "both"]:
                        try:
                            json_filepath = citation_utils.save_citation_json(
                                dataset_id, citations_df, output_dir, fetch_date
                            )
                            logger.info(
                                f"Saved detailed citations for {dataset_id} ({len(citations_df)} entries) "
                                f"to {json_filepath}"
                            )
                            save_success = True
                        except Exception as e_save:
                            logger.error(f"Failed to save JSON for {dataset_id}. Error: {e_save}")
                    
                    if save_success:
                        successful_updates_details[dataset_id] = len(citations_df)
                    else:
                        unsuccessful_list_update.append(dataset_id)
                elif citations_df is not None and citations_df.empty:
                    logger.info(
                        f"No detailed citations retrieved for {dataset_id} (empty DataFrame). "
                        "No pickle file saved."
                    )
                    successful_updates_details[dataset_id] = 0  # Explicitly state 0 retrieved
                else:  # Should be caught by error_message but as a safeguard
                    logger.warning(
                        f"Unexpected state for {dataset_id} after fetching detailed citations "
                        "(df is None but no error_message). Adding to unsuccessful."
                    )
                    unsuccessful_list_update.append(dataset_id)

            except Exception as exc:
                logger.error(f"{dataset_id} generated an exception during detailed citation processing: {exc}")
                unsuccessful_list_update.append(dataset_id)

    return successful_updates_details, unsuccessful_list_update


def save_updated_dataset_summary(successful_updates_details: dict, output_dir: str) -> str | None:
    """Saves a summary of successfully updated dataset citation lists."""
    if not successful_updates_details:
        logger.info("No successful updates to summarize for detailed citation lists.")
        return None

    filename = 'updated_datasets_' + datetime.today().strftime('%d%m%Y') + '.csv'
    filepath = os.path.join(output_dir, filename)
    try:
        pd.Series(successful_updates_details).to_csv(
            filepath, index=True, header=['retrieved_citations_count'], index_label='dataset_id'
        )
        logger.info(f"Saved summary of updated citation lists to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save updated_datasets summary to {filepath}. Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Update dataset citation numbers and lists.")
    parser.add_argument("--dataset-list-file", required=True,
                        help="Path to the file containing the list of dataset IDs (one per line).")
    parser.add_argument("--previous-citations-file", required=True,
                        help="Path to the CSV file containing previous citation counts.")
    parser.add_argument("--output-dir", default="citations",
                        help="Directory to save output files (default: citations/).")
    parser.add_argument("--workers", type=int, default=10,
                        help="Number of parallel workers for fetching citations (default: 10).")
    parser.add_argument("--no-update-num-cites", action="store_false", dest="update_num_cites",
                        help="Skip updating citation numbers.")
    parser.add_argument("--no-update-cite-list", action="store_false", dest="update_cite_list",
                        help="Skip updating detailed citation lists.")
    parser.add_argument("--output-format", choices=["pickle", "json", "both"], default="both",
                        help="Output format for detailed citation data (default: both).")
    parser.set_defaults(update_num_cites=True, update_cite_list=True)

    args = parser.parse_args()

    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info(f"Created output directory: {args.output_dir}")

    # Initialize proxy after parsing args, as it might be needed by gc functions
    # gc.get_working_proxy() is called, its internal logging will be used.
    # We might want to log before/after this call if it takes time or can fail here.
    logger.info("Initializing proxy for citation fetching...")
    gc.get_working_proxy()  # Relies on logging within getCitations.py
    logger.info("Proxy initialization attempted.")

    # %% get the list of datasets and citation numbers
    datasets, num_cites_old = load_input_data(args.dataset_list_file, args.previous_citations_file)
    if datasets is None or num_cites_old is None:  # Simplified condition
        logger.error("Failed to load initial data. Exiting.")
        return

    num_cites_new = num_cites_old.copy()  # Initialize with old counts
    overall_update_occurred = False  # Tracks if any significant update happened for lists
    datasets_for_list_update = []  # Initialize with an empty list

    if args.update_num_cites:
        num_cites_new_res, _, datasets_with_new_counts, counts_updated_flag = update_citation_counts(
            datasets, num_cites_old, args.workers  # Pass workers argument
        )
        num_cites_new = num_cites_new_res  # Assign to the broader scope variable
        if counts_updated_flag:
            save_citation_counts(num_cites_new, args.output_dir)
            overall_update_occurred = True
            # Use datasets_with_new_counts (increased or new) for targeted list updates
            datasets_for_list_update = datasets_with_new_counts
        else:  # No change in counts, but still might want to update lists
            logger.info(
                "No change in citation counts. Detailed lists will be updated for all datasets "
                "if --update-cite-list is enabled."
            )
            # If counts didn't change, and list update is enabled, process all datasets for list update
            if args.update_cite_list:
                datasets_for_list_update = datasets  # Fallback to all datasets
    elif args.update_cite_list:  # If only updating lists (not counts)
        logger.info("Skipping citation number updates. Will update detailed lists for all datasets.")
        datasets_for_list_update = datasets  # Process all datasets for lists

    if args.update_cite_list and datasets_for_list_update:
        logger.info(f"Updating detailed citation lists for {len(datasets_for_list_update)} dataset(s).")
        successful_details, unsuccessful_details = update_detailed_citation_lists(
            datasets_for_list_update, num_cites_new, args.output_dir, args.workers, args.output_format
        )
        if successful_details:
            save_updated_dataset_summary(successful_details, args.output_dir)
            overall_update_occurred = True  # If any list was successfully processed/saved
        if unsuccessful_details:
            logger.warning(f"Failed to update detailed citation lists for: {unsuccessful_details}")
    elif args.update_cite_list:
        logger.info(
            "Citation list update was enabled, but no datasets were marked for update "
            "(e.g., no count changes and not forced). Consider logic."
        )

    if overall_update_occurred:
        logger.info("Update process completed. Changes were made.")
    else:
        logger.info("Update process completed. No changes were made to citation counts or lists.")

    # Create a summary of new and old citation counts
    logger.info("New and old citation counts:")
    logger.info(f"Old counts: {num_cites_old}")
    logger.info(f"New counts: {num_cites_new}")


if __name__ == "__main__":
    main()
