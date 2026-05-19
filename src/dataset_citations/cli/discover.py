"""Discover BIDS datasets relevant to the citation pipeline.

Primary discovery source is `api.nemar.org/datasets`. One paginated request
covers every nm-* and on-* (NEMAR-imported OpenNeuro) dataset with DOI,
modalities, source, and github_repo, removing the GitHub-pagination hot
path that historically caused rate-limit failures.

Legacy `ds-*` IDs not yet in the NEMAR catalog are still discovered via
the GitHub API against `OpenNeuroDatasets/`, gated behind `--source github`
or `--source both`.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from dataset_citations.sources.models import FetchSuccess
from dataset_citations.sources.nemar_catalog import (
    CatalogRow,
    filter_by_modality,
    get_or_fetch_catalog,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"
TARGET_ORG = "OpenNeuroDatasets"
DEFAULT_PER_PAGE = 100

TARGET_MODALITIES = ["eeg", "ieeg", "meg"]
ALL_POSSIBLE_BIDS_MODALITIES = sorted(
    set(
        TARGET_MODALITIES
        + [
            "anat",
            "func",
            "dwi",
            "fmap",
            "perf",
            "pet",
            "beh",
            "micr",
            "motion",
            "nirs",
            "mrs",
        ]
    )
)

LOOKUP_TABLE_PATH = "citations/dataset_modalities_lookup.csv"
LOOKUP_COLUMNS = ["dataset_name", "modalities", "processed_date"]
DEFAULT_CATALOG_CACHE = Path.home() / ".cache" / "dataset_citations" / "catalog.json"


def load_lookup_table(path: str) -> pd.DataFrame:
    """Load the dataset modalities lookup table, creating an empty one on miss."""
    empty = pd.DataFrame(columns=LOOKUP_COLUMNS).set_index("dataset_name")
    if not os.path.exists(path):
        logger.info("Lookup table %s not found; creating empty.", path)
        return empty
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        logger.info("Lookup table %s empty; starting fresh.", path)
        return empty
    if not all(col in df.columns for col in LOOKUP_COLUMNS):
        logger.warning("Lookup table %s has wrong columns; starting fresh.", path)
        return empty
    return df.set_index("dataset_name")


def save_lookup_table(df: pd.DataFrame, path: str) -> None:
    """Persist the lookup table."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.reset_index().to_csv(path, index=False)
    logger.info("Saved lookup table to %s with %d entries.", path, len(df))


def get_github_api_response(api_url: str, headers: dict) -> requests.Response | None:
    """Single GET with primary rate-limit awareness."""
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        if "X-RateLimit-Remaining" in response.headers:
            remaining = int(response.headers["X-RateLimit-Remaining"])
            limit = int(response.headers["X-RateLimit-Limit"])
            reset_time = int(response.headers["X-RateLimit-Reset"])
            logger.debug(
                "Rate limit: %d/%d remaining; resets %s",
                remaining,
                limit,
                datetime.fromtimestamp(reset_time),
            )
            if remaining < 20:
                wait = max(0.0, reset_time - time.time()) + 15
                logger.warning(
                    "Approaching rate limit (%d remaining); waiting %.0fs",
                    remaining,
                    wait,
                )
                time.sleep(wait)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        logger.error("HTTP error %s on %s", http_err, api_url)
        return http_err.response
    except requests.exceptions.RequestException as req_err:
        logger.error("Request error %s on %s", req_err, api_url)
        return None


def check_repository_for_modalities(
    repo_name: str, org_name: str, headers: dict
) -> list[str]:
    """Probe one dataset repo for the BIDS modality directories under sub-*/.

    Returns every modality directory observed in the first subject directory
    (and its first session, if sessions are used). Empty list on failure.
    """
    found: set[str] = set()
    logger.info("Scanning %s/%s for BIDS modalities…", org_name, repo_name)

    root_url = f"{GITHUB_API_BASE_URL}/repos/{org_name}/{repo_name}/contents/"
    root_response = get_github_api_response(root_url, headers)
    if not (root_response and root_response.status_code == 200):
        logger.warning("Could not list root contents for %s/%s.", org_name, repo_name)
        return []

    for item in root_response.json():
        if not (item["type"] == "dir" and item["name"].startswith("sub-")):
            continue
        subject_dir_name = item["name"]
        subject_response = get_github_api_response(item["url"], headers)
        if not (subject_response and subject_response.status_code == 200):
            logger.warning(
                "Could not list %s in %s; skipping repo.", subject_dir_name, repo_name
            )
            return []

        session_dirs = []
        for sub_item in subject_response.json():
            if sub_item["type"] != "dir":
                continue
            if sub_item["name"].startswith("ses-"):
                session_dirs.append(sub_item)
            else:
                found.add(sub_item["name"])

        if session_dirs:
            first_session = session_dirs[0]
            session_response = get_github_api_response(first_session["url"], headers)
            if session_response and session_response.status_code == 200:
                for session_item in session_response.json():
                    if session_item["type"] == "dir":
                        found.add(session_item["name"])

        return sorted(found)

    logger.info("No 'sub-' directories found in %s.", repo_name)
    return sorted(found)


def discover_via_catalog(
    cache_path: Path | None,
    target_modalities: list[str],
    max_age_seconds: int,
) -> list[CatalogRow]:
    """Return nm-* / on-* rows from the NEMAR catalog matching target modalities."""
    logger.info("Discovering datasets from api.nemar.org/datasets…")
    result = get_or_fetch_catalog(
        cache_path=cache_path, max_age_seconds=max_age_seconds
    )
    if not isinstance(result, FetchSuccess):
        logger.error("Catalog fetch failed (%s): %s", result.reason, result.detail)
        return []
    rows = result.value
    logger.info("Catalog returned %d total rows.", len(rows))
    filtered = filter_by_modality(rows, target_modalities)
    logger.info(
        "Catalog rows matching modalities %s: %d",
        target_modalities,
        len(filtered),
    )
    return filtered


def discover_via_github(
    headers: dict,
    lookup_df: pd.DataFrame,
    max_repos: int | None,
    force_rescan_all: bool,
    target_modalities: list[str],
) -> tuple[list[str], pd.DataFrame]:
    """Walk OpenNeuroDatasets on GitHub, refreshing the lookup CSV.

    Returns (dataset_names_matching_modalities, updated_lookup_df).
    """
    url: str | None = (
        f"https://api.github.com/orgs/{TARGET_ORG}/repos?type=public&per_page={DEFAULT_PER_PAGE}"
    )
    all_repos: list[dict] = []
    page_num = 1

    while url:
        if max_repos is not None and len(all_repos) >= max_repos:
            logger.info("Reached max_repos=%d for repo listing.", max_repos)
            break
        response_obj = get_github_api_response(url, headers)
        if not response_obj or response_obj.status_code != 200:
            logger.error("Failed to list repos from %s.", TARGET_ORG)
            return [], lookup_df

        try:
            page_repos = response_obj.json()
        except ValueError:
            logger.error("Could not decode GitHub repo-list JSON.")
            return [], lookup_df
        if not isinstance(page_repos, list):
            logger.error("Expected list, got %s.", type(page_repos).__name__)
            return [], lookup_df

        all_repos.extend(page_repos)
        logger.info(
            "Page %d: %d repos (total so far: %d)",
            page_num,
            len(page_repos),
            len(all_repos),
        )

        next_url: str | None = None
        for link in requests.utils.parse_header_links(
            response_obj.headers.get("Link", "")
        ):
            if link.get("rel") == "next":
                next_url = link["url"]
                break
        url = next_url
        page_num += 1

    logger.info("Total GitHub repos listed: %d", len(all_repos))
    processed = 0
    now_iso = datetime.now().isoformat()

    for repo_data in all_repos:
        if max_repos is not None and processed >= max_repos:
            logger.info("Stopping after %d repos (--max-repos).", max_repos)
            break
        repo_name = repo_data.get("name")
        if not repo_name:
            continue
        processed += 1

        if not force_rescan_all and repo_name in lookup_df.index:
            cached = lookup_df.loc[repo_name, "modalities"]
            if pd.notna(cached) and cached != "":
                cached_set = set(str(cached).split(","))
                if not (cached_set.issubset(target_modalities) and len(cached_set) > 0):
                    continue

        logger.info("Processing %s (%d/%d)", repo_name, processed, len(all_repos))
        found = check_repository_for_modalities(repo_name, TARGET_ORG, headers)
        modalities_str = ",".join(sorted(set(found)))

        if repo_name in lookup_df.index:
            lookup_df.loc[repo_name, "modalities"] = modalities_str
            lookup_df.loc[repo_name, "processed_date"] = now_iso
        else:
            new_row = pd.DataFrame(
                [{"modalities": modalities_str, "processed_date": now_iso}],
                index=[repo_name],
            )
            new_row.index.name = "dataset_name"
            lookup_df = pd.concat([lookup_df, new_row])

    matches: list[str] = []
    for dataset_name, row in lookup_df.iterrows():
        if pd.isna(row["modalities"]) or row["modalities"] == "":
            continue
        repo_modalities = [m.strip() for m in str(row["modalities"]).split(",")]
        if any(tm in repo_modalities for tm in target_modalities):
            matches.append(str(dataset_name))
    return matches, lookup_df


def main() -> None:
    """Discover datasets relevant to the citation pipeline."""
    parser = argparse.ArgumentParser(
        description=(
            "Discover BIDS datasets for citation tracking. Uses api.nemar.org "
            "as the primary catalog; GitHub OpenNeuroDatasets as legacy fallback."
        )
    )
    parser.add_argument(
        "--output-file",
        help="Path to write the discovered dataset names (one per line).",
    )
    parser.add_argument(
        "--source",
        choices=("catalog", "github", "both"),
        default="catalog",
        help=(
            "Discovery source. 'catalog' (default) uses api.nemar.org. "
            "'github' uses GitHub OpenNeuroDatasets. 'both' merges the two, "
            "preferring catalog rows and falling back to GitHub for ds-* IDs "
            "not yet in the catalog."
        ),
    )
    parser.add_argument(
        "--catalog-cache",
        type=Path,
        default=DEFAULT_CATALOG_CACHE,
        help=f"Path to cache the catalog response (default: {DEFAULT_CATALOG_CACHE}).",
    )
    parser.add_argument(
        "--catalog-cache-max-age",
        type=int,
        default=3600,
        help="Seconds before the catalog cache is considered stale (default: 3600).",
    )
    parser.add_argument(
        "--no-catalog-cache",
        action="store_true",
        help="Bypass the catalog cache and always fetch fresh.",
    )
    parser.add_argument(
        "--max-repos",
        type=int,
        default=None,
        help="GitHub path only: cap the number of repos processed (testing).",
    )
    parser.add_argument(
        "--force-rescan-all",
        action="store_true",
        help="GitHub path only: ignore the lookup CSV cache.",
    )
    args = parser.parse_args()

    cache_path: Path | None = None if args.no_catalog_cache else args.catalog_cache

    catalog_names: list[str] = []
    catalog_rows_by_source_id: dict[str, CatalogRow] = {}
    if args.source in ("catalog", "both"):
        catalog_rows = discover_via_catalog(
            cache_path=cache_path,
            target_modalities=TARGET_MODALITIES,
            max_age_seconds=args.catalog_cache_max_age,
        )
        catalog_names = [r.dataset_id for r in catalog_rows]
        for r in catalog_rows:
            if r.source == "openneuro" and r.source_id:
                catalog_rows_by_source_id[r.source_id] = r

    github_names: list[str] = []
    if args.source in ("github", "both"):
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN unset; cannot run GitHub discovery.")
            if args.source == "github":
                return
        else:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            lookup_df = load_lookup_table(LOOKUP_TABLE_PATH)
            github_names, lookup_df = discover_via_github(
                headers=headers,
                lookup_df=lookup_df,
                max_repos=args.max_repos,
                force_rescan_all=args.force_rescan_all,
                target_modalities=TARGET_MODALITIES,
            )
            save_lookup_table(lookup_df, LOOKUP_TABLE_PATH)

    if args.source == "both":
        # GitHub-discovered names are dropped if (a) their string ID matches a
        # catalog source_id (openneuro ds-* mirrored as on-* in the catalog),
        # or (b) their string ID matches a catalog dataset_id directly (when
        # GitHub happens to list a repo named identically to a NEMAR-native
        # nm-* row). Both checks keep the merge stable across either kind of
        # collision.
        catalog_name_set = set(catalog_names)
        already_covered = set(catalog_rows_by_source_id.keys()) | catalog_name_set
        github_only = [name for name in github_names if name not in already_covered]
        merged = sorted(catalog_name_set | set(github_only))
        logger.info(
            "Merged discovery: %d catalog + %d github-only = %d total",
            len(catalog_names),
            len(github_only),
            len(merged),
        )
        discovered = merged
    elif args.source == "catalog":
        discovered = sorted(set(catalog_names))
    else:
        discovered = sorted(set(github_names))

    logger.info("Total discovered datasets: %d", len(discovered))

    if args.output_file:
        Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_file, "w") as f:
            for name in discovered:
                f.write(f"{name}\n")
        logger.info("Wrote %d names to %s", len(discovered), args.output_file)
    else:
        logger.info("No --output-file given; not writing list to disk.")


if __name__ == "__main__":
    main()
