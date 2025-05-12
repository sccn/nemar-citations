#!/usr/bin/env python3
"""
Script to dynamically generate PR content for citation updates.
This script analyzes the changed citation files and generates a formatted
PR title and body with summary information.
"""

import os
import argparse
import pandas as pd
from datetime import datetime
import subprocess


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate PR content for citation updates')
    parser.add_argument('--previous-file', required=True, help='Path to previous citations file')
    parser.add_argument('--current-file', required=True, help='Path to current citations file')
    parser.add_argument('--output-file', help='File to save PR content to (default: stdout)')
    parser.add_argument('--format', choices=['github', 'text'], default='github',
                        help='Output format (default: github for GitHub markdown)')
    parser.add_argument('--repo-url', help='Repository URL for file links',
                        default='https://github.com/NEMAR/dataset_citations')
    return parser.parse_args()


def load_citations(file_path):
    """Load citations from CSV file."""
    if not os.path.exists(file_path):
        print(f"Warning: File does not exist: {file_path}")
        return pd.DataFrame()
    
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return pd.DataFrame()


def generate_pr_title():
    """Generate a descriptive PR title."""
    today = datetime.now()
    return f"Update dataset citations - {today.strftime('%B %Y')}"


def get_changed_files(directory_paths=None):
    """
    Get a list of changed files from git.
    
    Args:
        directory_paths: List of directories to filter by (optional)
    
    Returns:
        List of dictionaries with file information
    """
    try:
        # Build git command for detecting changed files
        git_cmd = ["git", "diff", "--cached", "--name-status"]
        if directory_paths:
            git_cmd.extend(["--"] + directory_paths)
        
        # Execute git command
        result = subprocess.run(
            git_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Process output
        changed_files = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) >= 2:
                status, file_path = parts[0], parts[1]
                
                # Skip files we don't want to include
                if not any(file_path.endswith(ext) for ext in ['.csv', '.pkl', '.txt']):
                    continue
                
                # Map git status codes to readable descriptions
                status_desc = {
                    'A': 'Added',
                    'M': 'Modified',
                    'D': 'Deleted',
                    'R': 'Renamed',
                    'C': 'Copied',
                    'U': 'Updated but unmerged'
                }.get(status[0], 'Changed')
                
                changed_files.append({
                    'path': file_path,
                    'status': status_desc,
                    'raw_status': status
                })
        
        return changed_files
    except subprocess.SubprocessError as e:
        print(f"Error getting changed files: {e}")
        return []


def get_file_diff_stats(file_path):
    """Get insertion and deletion statistics for a file."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--numstat", file_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            return {'insertions': 0, 'deletions': 0}
            
        parts = lines[0].split()
        if len(parts) >= 2:
            return {
                'insertions': int(parts[0]) if parts[0] != '-' else 0,
                'deletions': int(parts[1]) if parts[1] != '-' else 0
            }
        return {'insertions': 0, 'deletions': 0}
    except (subprocess.SubprocessError, ValueError) as e:
        print(f"Error getting diff stats for {file_path}: {e}")
        return {'insertions': 0, 'deletions': 0}


def analyze_citation_changes(prev_df, curr_df):
    """
    Analyze changes between previous and current citation files.
    Returns a dictionary with change statistics.
    """
    if prev_df.empty and curr_df.empty:
        return {
            "total_datasets": 0,
            "new_datasets": 0,
            "updated_datasets": 0,
            "new_citations": 0,
            "new_dataset_list": [],
            "updated_dataset_list": []
        }
    
    # Handle case where previous file doesn't exist or is empty
    if prev_df.empty:
        return {
            "total_datasets": len(curr_df),
            "new_datasets": len(curr_df),
            "updated_datasets": 0,
            "new_citations": curr_df["citation_count"].sum() if "citation_count" in curr_df.columns else 0,
            "new_dataset_list": curr_df["dataset"].tolist() if "dataset" in curr_df.columns else [],
            "updated_dataset_list": []
        }
    
    # Handle required columns
    required_cols = ["dataset", "citation_count"]
    for df in [prev_df, curr_df]:
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0 if col == "citation_count" else ""
    
    # Identify new and updated datasets
    if "dataset" in prev_df.columns and "dataset" in curr_df.columns:
        prev_datasets = set(prev_df["dataset"])
        curr_datasets = set(curr_df["dataset"])
        
        new_datasets = curr_datasets - prev_datasets
        common_datasets = curr_datasets.intersection(prev_datasets)
        
        # For common datasets, check which ones have updated citation counts
        updated_datasets = []
        for dataset in common_datasets:
            prev_count = prev_df[prev_df["dataset"] == dataset]["citation_count"].values[0]
            curr_count = curr_df[curr_df["dataset"] == dataset]["citation_count"].values[0]
            
            if curr_count != prev_count:
                updated_datasets.append({
                    "name": dataset,
                    "prev_count": prev_count,
                    "curr_count": curr_count,
                    "diff": curr_count - prev_count
                })
        
        # Calculate total new citations
        prev_total = prev_df["citation_count"].sum()
        curr_total = curr_df["citation_count"].sum()
        new_citations = curr_total - prev_total
        
        return {
            "total_datasets": len(curr_df),
            "new_datasets": len(new_datasets),
            "updated_datasets": len(updated_datasets),
            "new_citations": new_citations,
            "new_dataset_list": sorted(list(new_datasets)),
            "updated_dataset_list": sorted(updated_datasets, key=lambda x: x["diff"], reverse=True)
        }
    else:
        return {
            "total_datasets": len(curr_df),
            "new_datasets": 0,
            "updated_datasets": 0,
            "new_citations": 0,
            "new_dataset_list": [],
            "updated_dataset_list": []
        }


def format_pr_body(changes, format_type="github", repo_url=None):
    """Format PR body content with analysis of changes."""
    if format_type == "github":
        # Get GitHub Actions metadata
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        workflow = os.environ.get("GITHUB_WORKFLOW", "")
        workflow_run_number = os.environ.get("GITHUB_RUN_NUMBER", "")
        server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        
        # Create workflow run URL if available
        workflow_url = ""
        if run_id and repository:
            workflow_url = f"{server_url}/{repository}/actions/runs/{run_id}"
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        body = "## Automated Dataset Citation Update\n\n"
        body += "This pull request contains updates to the dataset citation database.\n\n"
        
        # Add metadata
        body += "### Metadata\n"
        body += f"- **Timestamp:** {timestamp}\n"
        if workflow_url:
            body += f"- **Workflow Run:** [{workflow} #{workflow_run_number}]({workflow_url})\n"
        body += "\n"
        
        # Add summary
        body += "### Summary\n"
        body += f"- Total datasets tracked: {changes['total_datasets']}\n"
        body += f"- New datasets added: {changes['new_datasets']}\n"
        body += f"- Datasets with updated citations: {changes['updated_datasets']}\n"
        body += f"- Total new citations: {changes['new_citations']}\n\n"
        
        # Add changed files section
        changed_files = get_changed_files(directory_paths=["citations/", "citations_output/"])
        if changed_files:
            body += "### Changed Files\n"
            
            # Group files by directory/type
            files_by_dir = {}
            for file_info in changed_files:
                file_path = file_info['path']
                directory = os.path.dirname(file_path) or "Root"
                if directory not in files_by_dir:
                    files_by_dir[directory] = []
                files_by_dir[directory].append(file_info)
            
            # Create markdown list with links
            for directory, files in sorted(files_by_dir.items()):
                body += f"\n**{directory}:**\n"
                for file_info in files:
                    file_path = file_info['path']
                    status = file_info['status']
                    
                    # Create link if repo URL is available
                    if repo_url:
                        link_text = os.path.basename(file_path)
                        link_url = f"{repo_url}/blob/main/{file_path}"
                        diff_stats = get_file_diff_stats(file_path)
                        
                        changes_text = ""
                        if diff_stats['insertions'] > 0 or diff_stats['deletions'] > 0:
                            changes_text = " (+"
                            if diff_stats['insertions'] > 0:
                                changes_text += f"{diff_stats['insertions']}/-"
                            if diff_stats['deletions'] > 0:
                                changes_text += f"{diff_stats['deletions']}"
                            changes_text += ")"
                        
                        body += f"- [{status}] [{link_text}]({link_url}){changes_text}\n"
                    else:
                        body += f"- [{status}] {file_path}\n"
            body += "\n"
        
        # Add datasets sections
        if changes['new_datasets'] > 0:
            body += "### New Datasets Added\n"
            for dataset in changes['new_dataset_list'][:10]:  # Limit to first 10
                body += f"- {dataset}\n"
            
            if len(changes['new_dataset_list']) > 10:
                body += f"- ... and {len(changes['new_dataset_list']) - 10} more\n"
            body += "\n"
        
        if changes['updated_datasets'] > 0:
            body += "### Datasets With Updated Citations\n"
            body += "| Dataset | Previous | Current | Change |\n"
            body += "|---------|----------|---------|--------|\n"
            
            # Show top 10 datasets with most citation changes
            for dataset in changes['updated_dataset_list'][:10]:
                name, prev, curr, diff = (
                    dataset['name'], 
                    dataset['prev_count'], 
                    dataset['curr_count'], 
                    dataset['diff']
                )
                body += f"| {name} | {prev} | {curr} | +{diff} |\n"
            
            if len(changes['updated_dataset_list']) > 10:
                remaining = len(changes['updated_dataset_list']) - 10
                body += f"\n... and {remaining} more datasets updated\n"
            body += "\n"
        
        body += "@cdesyoun Please review these citation updates when you have a chance.\n"
        
        return body
    else:
        # Plain text format, simpler version
        body = "Automated Dataset Citation Update\n\n"
        body += f"Total datasets: {changes['total_datasets']}\n"
        body += f"New datasets: {changes['new_datasets']}\n"
        body += f"Updated datasets: {changes['updated_datasets']}\n"
        body += f"New citations: {changes['new_citations']}\n"
        return body


def write_github_output(title, body, changes):
    """Write PR content to GitHub Actions output file if running in GitHub Actions."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"pr_title<<EOF\n{title}\nEOF\n")
            f.write(f"pr_body<<EOF\n{body}\nEOF\n")
            
            # Generate labels based on changes
            labels = ["automated", "citation-update"]
            
            # Add new-dataset label if new datasets were found
            if changes.get("new_datasets", 0) > 0:
                labels.append("new-dataset")
                
            # Add data-update label for regular updates
            if changes.get("updated_datasets", 0) > 0:
                labels.append("data-update")
                
            # Write labels as comma-separated list for GitHub Actions
            f.write(f"pr_labels={','.join(labels)}\n")
            
        print(f"Wrote PR content to GitHub output: {github_output}")
    else:
        print("Warning: GITHUB_OUTPUT environment variable not set. Not writing GitHub output.")


def main():
    """Main function to generate PR content."""
    args = parse_arguments()
    
    # Load citation files
    prev_df = load_citations(args.previous_file)
    curr_df = load_citations(args.current_file)
    
    # Generate PR title
    pr_title = generate_pr_title()
    
    # Analyze changes
    changes = analyze_citation_changes(prev_df, curr_df)
    
    # Format PR body
    pr_body = format_pr_body(changes, args.format, args.repo_url)
    
    # Output results
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(f"PR_TITLE: {pr_title}\n\n")
            f.write("PR_BODY:\n")
            f.write(pr_body)
        print(f"PR content written to {args.output_file}")
    else:
        print(f"PR_TITLE: {pr_title}\n")
        print("PR_BODY:")
        print(pr_body)
    
    # If running in GitHub Actions, write to GitHub output
    write_github_output(pr_title, pr_body, changes)


if __name__ == "__main__":
    main() 