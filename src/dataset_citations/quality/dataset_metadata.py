#!/usr/bin/env python3
"""
Dataset metadata retrieval from GitHub API.

This module retrieves dataset metadata (dataset_description.json and README files)
from the dataset's GitHub repository for confidence scoring.

The org each dataset lives in depends on its prefix:
  ds-* -> github.com/OpenNeuroDatasets/<id>  (legacy OpenNeuro tree)
  nm-* -> github.com/nemarDatasets/<id>      (NEMAR-native datasets)
  on-* -> github.com/nemarDatasets/<id>      (OpenNeuro datasets imported into NEMAR)

Before this fix the org was hardcoded to OpenNeuroDatasets, which made
nm-* / on-* lookups 404 and PyGithub's default infinite socket timeout
turned a single bad lookup into a multi-hour CLOSE_WAIT stall.

Copyright (c) 2025 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from github import Github
from github.GithubException import GithubException

logger = logging.getLogger(__name__)

# Bound every GitHub call so a dropped socket can't hang the pipeline.
# PyGithub forwards this to urllib3; the default is no timeout.
_GITHUB_TIMEOUT_SECONDS = 30

# Match a NEMAR-managed dataset id: prefix (nm or on) followed by digits.
# Tighter than `startswith("nm")` so future ids like `nmr-phantom` or
# `online-study-x` don't silently route to nemarDatasets/.
_NEMAR_PREFIX_RE = re.compile(r"^(nm|on)\d")


def _org_for_dataset(dataset_id: str) -> str:
    """Return the GitHub org that hosts the given dataset.

    Routing:
      nm<digits...>  -> nemarDatasets   (NEMAR-native)
      on<digits...>  -> nemarDatasets   (OpenNeuro imported into NEMAR)
      everything else -> OpenNeuroDatasets (legacy)

    Case-insensitive on the prefix; the project's canonical ids are
    lowercase but a stray uppercase input shouldn't silently misroute.
    """
    if _NEMAR_PREFIX_RE.match(dataset_id.lower()):
        return "nemarDatasets"
    return "OpenNeuroDatasets"


class DatasetMetadataRetriever:
    """Retrieve dataset metadata from GitHub repositories."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the metadata retriever.

        Args:
            github_token: GitHub token for API access. If None, uses public access.
        """
        # `timeout` caps how long PyGithub will wait on a single HTTP call
        # before raising; without it a CLOSE_WAIT socket can hang forever.
        if github_token:
            self.github = Github(github_token, timeout=_GITHUB_TIMEOUT_SECONDS)
        else:
            self.github = Github(timeout=_GITHUB_TIMEOUT_SECONDS)

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

        org = _org_for_dataset(dataset_id)
        metadata = {
            "dataset_id": dataset_id,
            "date_retrieved": datetime.now(timezone.utc).isoformat(),
            "dataset_description": None,
            "readme_content": None,
            "github_info": {
                "repository_url": f"https://github.com/{org}/{dataset_id}",
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
            repo = self.github.get_repo(f"{org}/{dataset_id}")
            metadata["github_info"]["exists"] = True
            metadata["retrieval_status"]["repository"] = "success"

            # Add repository information
            metadata["github_info"].update(
                {
                    "description": repo.description,
                    "created_at": (
                        repo.created_at.isoformat() if repo.created_at else None
                    ),
                    "updated_at": (
                        repo.updated_at.isoformat() if repo.updated_at else None
                    ),
                    "default_branch": repo.default_branch,
                }
            )

            logger.info(f"Repository {dataset_id} found successfully")

        except GithubException as e:
            logger.warning(f"Repository {dataset_id} not found or not accessible: {e}")
            metadata["retrieval_status"]["repository"] = f"error: {e!s}"
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
        except (AssertionError, ValueError) as e:
            # PyGithub's ContentFile.decoded_content raises
            # AssertionError("unsupported encoding: None") for files it cannot
            # base64-decode (e.g. a >1MB blob returned with encoding=none, as on
            # ds002001). ValueError covers json.JSONDecodeError and
            # UnicodeDecodeError. Treat the description as unavailable rather than
            # letting one undecodable file abort the whole dataset retrieval.
            logger.warning(f"dataset_description.json unreadable for {dataset_id}: {e}")
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

            except (GithubException, AssertionError, ValueError) as e:
                # AssertionError/ValueError: PyGithub cannot decode an oversized
                # or odd-encoding README; skip it instead of crashing the
                # dataset retrieval. Try the next candidate filename.
                logger.debug(f"{readme_file} unreadable for {dataset_id}: {e}")
                continue

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
    with open(filepath, encoding="utf-8") as f:
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
