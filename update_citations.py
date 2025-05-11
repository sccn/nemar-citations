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
        print(f"Created output directory: {args.output_dir}")

    # Initialize proxy after parsing args, as it might be needed by gc functions
    gc.get_working_proxy()

    # %% get the list of datasets and citation numbers
    try:
        datasets = pd.read_csv(args.dataset_list_file, header=None)[0].tolist()
    except FileNotFoundError:
        print(f"ERROR: Dataset list file not found: {args.dataset_list_file}")
        return
    except Exception as e:
        print(f"ERROR: Could not read dataset list file: {args.dataset_list_file}. Error: {e}")
        return
        
    try:
        num_cites_old_df = pd.read_csv(args.previous_citations_file, index_col='dataset_id')
        num_cites_old = num_cites_old_df.iloc[:, 0]
    except FileNotFoundError:
        print(f"INFO: Previous citations file not found: {args.previous_citations_file}. Starting with no previous counts.")
        num_cites_old = pd.Series(name='number_of_citations', dtype='float64') # Empty series if file not found
    except Exception as e:
        print(f"ERROR: Could not read previous citations file: {args.previous_citations_file}. Error: {e}")
        return

    UPDATE_FLAG = False # Initialize UPDATE_FLAG
    datasets_updated = [] # Initialize datasets_updated
    num_cites_new = pd.Series(name='number_of_citations', dtype='float64') # Initialize num_cites_new

    # %% if we need to update the citation numbers
    if args.update_num_cites:
        print("Updating citation numbers...")
        # num_cites_new = pd.Series(name='number_of_citations') # Already initialized
        for i, d in enumerate(datasets):
            print(f"Fetching citation number for {d} ({i+1}/{len(datasets)})...")
            try:
                num_cites_new[d] = gc.get_citation_numbers(d)
            except Exception as e:
                print(f"WARNING: Failed to get citation number for {d}. Error: {e}")
                num_cites_new[d] = num_cites_old.get(d, 0) # Keep old value or 0 if new

        # compare the old and new citation numbers
        # Ensure alignment before subtraction, handle new datasets correctly
        num_cites_new_aligned, num_cites_old_aligned = num_cites_new.align(num_cites_old, join='outer', fill_value=0)
        num_cites_diff = num_cites_new_aligned.sub(num_cites_old_aligned, fill_value=0)
        
        UPDATE_FLAG = (num_cites_diff != 0).any() # Check if any difference exists

        if UPDATE_FLAG:
            print("New citation counts found. Differences:")
            print(num_cites_diff[num_cites_diff != 0])
            # save the new citation numbers
            new_citations_filepath = os.path.join(args.output_dir, 'citations_' + datetime.today().strftime('%d%m%Y') + '.csv')
            num_cites_new.to_csv(new_citations_filepath, index_label='dataset_id')
            print(f"Saved new citation counts to {new_citations_filepath}")

            # Get the list of datasets that have been updated (genuinely new citations or new datasets)
            datasets_updated = num_cites_diff[num_cites_diff > 0].index.tolist()
            newly_added_datasets = num_cites_new.index.difference(num_cites_old.index).tolist()
            datasets_updated.extend([d for d in newly_added_datasets if d not in datasets_updated])
            
            if not datasets_updated:
                print("No datasets found with an increase in citations. UPDATE_FLAG might be due to decreases or NaN handling.")
                UPDATE_FLAG = False # Reset if only decreases or other non-update changes
        else:
            print('No new citation counts found or no change in counts.')
            UPDATE_FLAG = False # Ensure it's false if no real updates

    else:
        print("Skipping update of citation numbers.")
        # If not updating numbers, we need to decide if we proceed with cite list update
        # For now, let's assume if numbers aren't updated, we use previous numbers for list update
        # and the flag means if *any* list should be updated.
        # A more sophisticated logic might be needed based on exact requirements.
        num_cites_new = num_cites_old.copy() # Use old numbers if not updating
        # Potentially set UPDATE_FLAG to True if update_cite_list is True, to force list processing
        if args.update_cite_list:
             print("Force processing citation lists based on previous numbers.")
             UPDATE_FLAG = True # To allow cite list update to run with old numbers
             datasets_updated = datasets # Process all datasets if forcing list update

    # %% if we need to update the citation list
    if args.update_cite_list:
        print("Updating detailed citation lists...")
        if UPDATE_FLAG and datasets_updated: # Ensure there are datasets marked for update
            unsuccessful_list_update = []
            successful_updates_details = {}  # Changed to dict to store both dataset and citation count
            # get the citations for the updated datasets
            print(f"Processing citation lists for {len(datasets_updated)} datasets: {datasets_updated}")
            for i, d in enumerate(datasets_updated):
                print(f"Fetching citation list for {d} ({i+1}/{len(datasets_updated)})...")
                current_num_cites = num_cites_new.get(d)
                if pd.isna(current_num_cites) or current_num_cites == 0:
                    print(f"Skipping citation list for {d} as it has 0 or NaN citations.")
                    continue
                try:
                    citations = gc.get_citations(d, int(current_num_cites))
                    output_pkl_path = os.path.join(args.output_dir, d + '.pkl')
                    citations.to_pickle(output_pkl_path)
                    successful_updates_details[d] = len(citations)  # Store the actual number of citations retrieved
                    print(f"Completed citations for {d}, saved to {output_pkl_path}")
                except Exception as e:
                    unsuccessful_list_update.append(d)
                    print(f"Failed to get citation list for {d}. Error: {e}")

            # Only save the list of datasets that were successfully updated
            if successful_updates_details:
                updated_datasets_filepath = os.path.join(args.output_dir, 'updated_datasets_' + datetime.today().strftime('%d%m%Y') + '.csv')
                pd.Series(successful_updates_details).to_csv(updated_datasets_filepath, index=True, header=['retrieved_citations_count'], index_label='dataset_id')
                print(f"Saved summary of updated citation lists to {updated_datasets_filepath}")
            if unsuccessful_list_update:
                print(f"Failed to get citation lists for {len(unsuccessful_list_update)} datasets: {', '.join(unsuccessful_list_update)}")
        elif not datasets_updated and UPDATE_FLAG:
            print("Citation lists update skipped: UPDATE_FLAG was true, but no specific datasets were marked for update (e.g. only decreases). ")
        else:
            print('Citation lists update skipped as no new citation counts were found or update was not requested.')
    else:
        print("Skipping update of detailed citation lists.")

if __name__ == "__main__":
    main()
