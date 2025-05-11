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
import argparse
import os
import logging  # Added import

# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # Create a logger instance for this module


def load_input_data(dataset_list_file_path: str, previous_citations_file_path: str) -> tuple[list | None, pd.Series | None]:
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
            f"Successfully read {len(num_cites_old)} entries from previous citations file: {previous_citations_file_path}"
        )
    except FileNotFoundError:
        logger.info(
            f"Previous citations file not found: {previous_citations_file_path}. Starting with no previous counts."
        )
        num_cites_old = pd.Series(name='number_of_citations', dtype='float64')
    except Exception as e:
        logger.error(f"Could not read previous citations file: {previous_citations_file_path}. Error: {e}")
        return datasets, None  # Return datasets if successfully loaded, but num_cites_old failed
        
    return datasets, num_cites_old


def update_citation_counts(datasets: list, num_cites_old: pd.Series) -> tuple[pd.Series, pd.Series, list, bool]:
    """
    Updates citation counts for the given list of datasets.

    Args:
        datasets (list): List of dataset IDs to update.
        num_cites_old (pd.Series): Series of old citation counts.

    Returns:
        tuple[pd.Series, pd.Series, list, bool]: A tuple containing:
            - pd.Series: New citation counts.
            - pd.Series: Differences between new and old counts.
            - list: List of dataset IDs that have updated counts (increased or newly added).
            - bool: Flag indicating if any citation counts were updated.
    """
    num_cites_new = pd.Series(name='number_of_citations', dtype='float64')
    logger.info("Updating citation numbers...")
    for i, d in enumerate(datasets):
        logger.info(f"Fetching citation number for {d} ({i + 1}/{len(datasets)})...")
        try:
            num_cites_new[d] = gc.get_citation_numbers(d)
        except Exception as e:
            logger.error(f"Unexpected error calling gc.get_citation_numbers for {d}. Error: {e}")
            num_cites_new[d] = num_cites_old.get(d, 0)

    num_cites_new_aligned, num_cites_old_aligned = num_cites_new.align(num_cites_old, join='outer', fill_value=0)
    num_cites_diff = num_cites_new_aligned.sub(num_cites_old_aligned, fill_value=0)
    
    update_flag = (num_cites_diff != 0).any()
    datasets_updated_for_counts = []

    if update_flag:
        logger.info("New citation counts found. Differences:")
        changed_counts = num_cites_diff[num_cites_diff != 0]
        for dataset_id, diff_value in changed_counts.items():
            old_val = num_cites_old_aligned.get(dataset_id, 'N/A')
            new_val = num_cites_new_aligned.get(dataset_id, 'N/A')
            logger.info(f"  Dataset {dataset_id}: old={old_val}, new={new_val}, diff={diff_value}")
        
        datasets_updated_for_counts = num_cites_diff[num_cites_diff > 0].index.tolist()
        newly_added_datasets = num_cites_new.index.difference(num_cites_old.index).tolist()
        # Line was too long, breaking it for clarity if it doesn't affect list comprehension performance significantly
        for d_new in newly_added_datasets:
            if d_new not in datasets_updated_for_counts:
                datasets_updated_for_counts.append(d_new)
        
        if not datasets_updated_for_counts:
            logger.info("No datasets found with an increase in citations. Update flag might be due to decreases.")
            # update_flag = False # Keep true if there are *any* changes, even decreases
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


def update_detailed_citation_lists(
        datasets_to_process: list, num_cites_new: pd.Series, output_dir: str
) -> tuple[dict, list]:
    """Fetches and saves detailed citation lists for specified datasets."""
    unsuccessful_list_update = []
    successful_updates_details = {}
    logger.info(f"Processing citation lists for {len(datasets_to_process)} datasets: {datasets_to_process}")
    for i, d in enumerate(datasets_to_process):
        logger.info(f"Fetching citation list for {d} ({i + 1}/{len(datasets_to_process)})...")
        current_num_cites = num_cites_new.get(d)

        if pd.isna(current_num_cites):
            logger.warning(f"Skipping citation list for {d} as its citation count is NaN.")
            continue
        if current_num_cites == 0:
            logger.info(f"Skipping citation list for {d} as it has 0 citations.")
            continue
        
        try:
            citations = gc.get_citations(d, int(current_num_cites))
            if citations is not None and not citations.empty:
                output_pkl_path = os.path.join(output_dir, d + '.pkl')
                try:
                    citations.to_pickle(output_pkl_path)
                    successful_updates_details[d] = len(citations)
                    logger.info(f"Completed citations for {d} ({len(citations)} entries), saved to {output_pkl_path}")
                except Exception as e:
                    logger.error(f"Failed to save pickle for {d} to {output_pkl_path}. Error: {e}")
                    unsuccessful_list_update.append(d)
            elif citations is None:
                logger.warning(f"gc.get_citations returned None for {d}. No pickle file saved.")
                unsuccessful_list_update.append(d)
            else:  # Empty dataframe
                logger.info(
                    f"No citations retrieved by gc.get_citations for {d} (returned empty). No pickle file saved."
                )
                successful_updates_details[d] = 0
        except ValueError as ve:
            logger.error(f"ValueError converting citation count for {d} (value: {current_num_cites}). Error: {ve}")
            unsuccessful_list_update.append(d)
        except Exception as e:
            logger.error(f"Failed to get citation list for {d}. Error: {e}")
            unsuccessful_list_update.append(d)
            
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
    parser.add_argument("--no-update-num-cites", action="store_false", dest="update_num_cites",
                        help="Skip updating citation numbers.")
    parser.add_argument("--no-update-cite-list", action="store_false", dest="update_cite_list",
                        help="Skip updating detailed citation lists.")
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
    if datasets is None or num_cites_old is None:
        logger.error("Failed to load initial data. Exiting.")
        return

    num_cites_new = num_cites_old.copy()
    overall_update_occurred = False  # Tracks if any significant update happened for lists
    datasets_for_list_update = []

    if args.update_num_cites:
        num_cites_new_res, _, datasets_with_new_counts, counts_updated_flag = update_citation_counts(
            datasets, num_cites_old
        )
        num_cites_new = num_cites_new_res # Assign to the broader scope variable
        if counts_updated_flag:
            save_citation_counts(num_cites_new, args.output_dir)
            overall_update_occurred = True 
            # Use datasets_with_new_counts (increased or new) for targeted list updates
            datasets_for_list_update = datasets_with_new_counts 
        else:  # No change in counts
            logger.info("Citation counts were not updated as no changes were found.")
            # If counts didn't change, but user wants to update lists, process all datasets
            if args.update_cite_list:
                logger.info(
                    "Proceeding to update citation lists for all datasets based on existing counts as per --update-cite-list."
                )
                datasets_for_list_update = datasets
                overall_update_occurred = True  # Force list update if requested
            # else: No count change AND no list update requested -> datasets_for_list_update remains []

    else:  # Not updating numbers
        logger.info("Skipping update of citation numbers.")
        # If not updating numbers, but want to update lists, use all datasets with old numbers
        if args.update_cite_list:
            logger.info(
                "Updating citation lists for all datasets based on previous counts as num_cites update was skipped."
            )
            datasets_for_list_update = datasets
            overall_update_occurred = True  # Indicate that list update will proceed
        # else: datasets_for_list_update remains []


    if args.update_cite_list:
        if overall_update_occurred and datasets_for_list_update:
            successful_updates, unsuccessful_updates = update_detailed_citation_lists(
                datasets_for_list_update, num_cites_new, args.output_dir
            )
            if successful_updates:
                save_updated_dataset_summary(successful_updates, args.output_dir)
            if unsuccessful_updates:
                logger.warning(
                    f"Failed to get/save complete citation lists for {len(unsuccessful_updates)} datasets: "
                    f"{', '.join(unsuccessful_updates)}"
                )
        elif not overall_update_occurred:
            logger.info(
                "Citation lists update skipped as no prior updates indicated a need (e.g., no count changes and not forced)."
            )
        elif not datasets_for_list_update:
            logger.info(
                "Citation lists update skipped as no datasets were identified for processing "
                "(e.g. counts updated but only decreases, and not forcing all lists)."
            )
    else:
        logger.info("Skipping update of detailed citation lists.")

    logger.info("Dataset citation update process finished.")


if __name__ == "__main__":
    main()
