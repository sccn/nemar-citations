#!/usr/bin/env python3
"""
Dataset metadata retrieval from GitHub API.

This module retrieves dataset metadata (dataset_description.json and README files)
from the OpenNeuro GitHub repository for confidence scoring.

Copyright (c) 2024 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from github import Github
from github.GithubException import GithubException

logger = logging.getLogger(__name__)


class DatasetMetadataRetriever:
    """Retrieve dataset metadata from GitHub repositories."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the metadata retriever.

        Args:
            github_token: GitHub token for API access. If None, uses public access.
        """
        self.github = Github(github_token) if github_token else Github()
        self.openneuro_repo = "OpenNeuroDatasets"

    def get_dataset_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific dataset from OpenNeuro GitHub.

        Args:
            dataset_id: The dataset ID (e.g., 'ds000117')

        Returns:
            Dict containing dataset metadata structure:
            - dataset_id: Dataset identifier
            - date_retrieved: ISO format timestamp
            - dataset_description: Parsed dataset_description.json content
            - readme_content: README file content
            - github_info: Repository information
            - retrieval_status: Success/failure status for each component
        """
        logger.info(f"Retrieving metadata for dataset: {dataset_id}")

        metadata = {
            "dataset_id": dataset_id,
            "date_retrieved": datetime.now(timezone.utc).isoformat(),
            "dataset_description": None,
            "readme_content": None,
            "github_info": {
                "repository_url": f"https://github.com/{self.openneuro_repo}/{dataset_id}",
                "exists": False,
            },
            "retrieval_status": {
                "dataset_description": "not_found",
                "readme": "not_found",
                "repository": "not_found",
            },
        }

        try:
            # Get the repository
            repo = self.github.get_repo(f"{self.openneuro_repo}/{dataset_id}")
            metadata["github_info"]["exists"] = True
            metadata["retrieval_status"]["repository"] = "success"

            # Add repository information
            metadata["github_info"].update(
                {
                    "description": repo.description,
                    "created_at": repo.created_at.isoformat()
                    if repo.created_at
                    else None,
                    "updated_at": repo.updated_at.isoformat()
                    if repo.updated_at
                    else None,
                    "default_branch": repo.default_branch,
                }
            )

            logger.info(f"Repository {dataset_id} found successfully")

        except GithubException as e:
            logger.warning(f"Repository {dataset_id} not found or not accessible: {e}")
            metadata["retrieval_status"]["repository"] = f"error: {str(e)}"
            return metadata

        # Retrieve dataset_description.json
        metadata["dataset_description"] = self._get_dataset_description(
            repo, dataset_id
        )

        # Retrieve README content
        metadata["readme_content"] = self._get_readme_content(repo, dataset_id)

        return metadata

    def _get_dataset_description(
        self, repo, dataset_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve and parse dataset_description.json."""
        try:
            content = repo.get_contents("dataset_description.json")
            description_data = json.loads(content.decoded_content.decode("utf-8"))
            logger.info(f"Retrieved dataset_description.json for {dataset_id}")
            return description_data

        except GithubException as e:
            logger.warning(f"dataset_description.json not found for {dataset_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in dataset_description.json for {dataset_id}: {e}"
            )
            return None

    def _get_readme_content(self, repo, dataset_id: str) -> Optional[str]:
        """Retrieve README content."""
        readme_files = ["README.md", "README.txt", "README", "readme.md", "readme.txt"]

        for readme_file in readme_files:
            try:
                content = repo.get_contents(readme_file)
                readme_text = content.decoded_content.decode("utf-8")
                logger.info(f"Retrieved {readme_file} for {dataset_id}")
                return readme_text

            except GithubException:
                continue  # Try next README file

        logger.warning(f"No README file found for {dataset_id}")
        return None

    def retrieve_multiple_datasets(
        self, dataset_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve metadata for multiple datasets.

        Args:
            dataset_ids: List of dataset IDs to retrieve

        Returns:
            Dict mapping dataset_id to metadata dict
        """
        results = {}

        for dataset_id in dataset_ids:
            try:
                results[dataset_id] = self.get_dataset_metadata(dataset_id)
            except Exception as e:
                logger.error(f"Failed to retrieve metadata for {dataset_id}: {e}")
                results[dataset_id] = {
                    "dataset_id": dataset_id,
                    "date_retrieved": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                    "retrieval_status": {
                        "dataset_description": "error",
                        "readme": "error",
                        "repository": "error",
                    },
                }

        return results


def save_dataset_metadata(metadata: Dict[str, Any], output_dir: str) -> str:
    """
    Save dataset metadata to JSON file.

    Args:
        metadata: Dataset metadata dict
        output_dir: Directory to save the file

    Returns:
        Path to the saved file
    """
    dataset_id = metadata["dataset_id"]
    filename = f"{dataset_id}_datasets.json"
    filepath = os.path.join(output_dir, filename)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved dataset metadata to {filepath}")
    return filepath


def load_dataset_metadata(filepath: str) -> Dict[str, Any]:
    """
    Load dataset metadata from JSON file.

    Args:
        filepath: Path to the metadata JSON file

    Returns:
        Dataset metadata dict
    """
    with open(filepath, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return metadata


def extract_dataset_text(metadata: Dict[str, Any]) -> str:
    """
    Extract combined text content from dataset metadata for similarity scoring.

    Args:
        metadata: Dataset metadata dict

    Returns:
        Combined text string for embedding
    """
    text_parts = []

    # Add dataset description content
    if metadata.get("dataset_description"):
        desc = metadata["dataset_description"]

        # Add key fields from dataset_description.json
        if desc.get("Name"):
            text_parts.append(f"Dataset Name: {desc['Name']}")
        if desc.get("BIDSVersion"):
            text_parts.append(f"BIDS Version: {desc['BIDSVersion']}")
        if desc.get("License"):
            text_parts.append(f"License: {desc['License']}")
        if desc.get("Authors"):
            authors = (
                ", ".join(desc["Authors"])
                if isinstance(desc["Authors"], list)
                else str(desc["Authors"])
            )
            text_parts.append(f"Authors: {authors}")
        if desc.get("DatasetType"):
            text_parts.append(f"Dataset Type: {desc['DatasetType']}")
        if desc.get("TaskName"):
            text_parts.append(f"Task Name: {desc['TaskName']}")

    # Add README content (first 2000 characters to avoid overly long text)
    if metadata.get("readme_content"):
        readme_text = metadata["readme_content"][:2000]
        text_parts.append(f"README: {readme_text}")

    # Add repository description
    if metadata.get("github_info", {}).get("description"):
        text_parts.append(
            f"Repository Description: {metadata['github_info']['description']}"
        )

    return "\n\n".join(text_parts)
