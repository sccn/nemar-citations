"""
CLI command for automated embedding updates when new citations are added.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import json
import time
from datetime import datetime, timedelta
import hashlib

from ..core.citation_utils import load_citations_from_json
from ..embeddings.storage_manager import EmbeddingStorageManager
from .generate_embeddings import (
    generate_dataset_embeddings,
    generate_citation_embeddings,
)


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


class EmbeddingUpdateAutomator:
    """
    Automated system for updating embeddings when citation data changes.
    """

    def __init__(self, embeddings_dir: Path, citations_dir: Path, datasets_dir: Path):
        """Initialize the update automator."""
        self.embeddings_dir = embeddings_dir
        self.citations_dir = citations_dir
        self.datasets_dir = datasets_dir
        self.storage_manager = EmbeddingStorageManager(embeddings_dir)

        # Create state tracking directory
        self.state_dir = embeddings_dir / "automation_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "update_state.json"

    def load_update_state(self) -> Dict:
        """Load the current update state."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        else:
            return {
                "last_update": None,
                "file_hashes": {},
                "processed_citations": set(),
                "failed_updates": [],
                "update_history": [],
            }

    def save_update_state(self, state: Dict):
        """Save the update state."""
        # Convert sets to lists for JSON serialization
        if "processed_citations" in state and isinstance(
            state["processed_citations"], set
        ):
            state["processed_citations"] = list(state["processed_citations"])

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def detect_changed_files(
        self, since_time: Optional[datetime] = None
    ) -> Dict[str, List[Path]]:
        """
        Detect changed citation and dataset files.

        Args:
            since_time: Only detect changes since this time

        Returns:
            Dict with lists of changed citation and dataset files
        """
        state = self.load_update_state()
        current_hashes = state.get("file_hashes", {})

        changed_files = {"citation_files": [], "dataset_files": []}

        # Check citation files
        citation_files = list((self.citations_dir / "json").glob("ds*_citations.json"))
        for file_path in citation_files:
            file_key = str(file_path.relative_to(self.citations_dir))
            current_hash = self.calculate_file_hash(file_path)

            # Check if file is new or changed
            if (
                file_key not in current_hashes
                or current_hashes[file_key] != current_hash
            ):
                # Also check modification time if since_time is specified
                if (
                    since_time is None
                    or datetime.fromtimestamp(file_path.stat().st_mtime) > since_time
                ):
                    changed_files["citation_files"].append(file_path)
                    current_hashes[file_key] = current_hash

        # Check dataset files
        dataset_files = list(self.datasets_dir.glob("ds*_datasets.json"))
        for file_path in dataset_files:
            file_key = str(file_path.relative_to(self.datasets_dir))
            current_hash = self.calculate_file_hash(file_path)

            if (
                file_key not in current_hashes
                or current_hashes[file_key] != current_hash
            ):
                if (
                    since_time is None
                    or datetime.fromtimestamp(file_path.stat().st_mtime) > since_time
                ):
                    changed_files["dataset_files"].append(file_path)
                    current_hashes[file_key] = current_hash

        # Update state with new hashes
        state["file_hashes"] = current_hashes
        self.save_update_state(state)

        return changed_files

    def identify_outdated_embeddings(
        self, changed_files: Dict[str, List[Path]]
    ) -> Dict[str, List[str]]:
        """
        Identify embeddings that need to be updated based on changed files.

        Args:
            changed_files: Dict of changed citation and dataset files

        Returns:
            Dict with lists of outdated embedding IDs
        """
        outdated = {
            "dataset_embeddings": [],
            "citation_embeddings": [],
            "composite_embeddings": [],
        }

        # Check dataset embeddings
        for dataset_file in changed_files["dataset_files"]:
            dataset_id = dataset_file.stem.replace("_datasets", "")

            # Check if embedding exists
            current_embedding = (
                self.storage_manager.registry.get_current_dataset_embedding(dataset_id)
            )
            if current_embedding:
                # Mark as obsolete - will trigger regeneration
                self.storage_manager.registry.mark_as_obsolete(
                    "dataset", dataset_id, "source file updated"
                )
                outdated["dataset_embeddings"].append(dataset_id)

        # Check citation embeddings - more complex as we need to map citations to hashes
        processed_citation_hashes = set()

        for citation_file in changed_files["citation_files"]:
            try:
                citations_data = load_citations_from_json(citation_file)
                if "citation_details" not in citations_data:
                    continue

                for citation in citations_data["citation_details"]:
                    # Generate citation hash
                    title = citation.get("title", "")
                    abstract = citation.get("abstract", "")
                    citation_text = f"{title} {abstract}".strip()

                    if citation_text:
                        citation_hash = hashlib.sha256(
                            citation_text.encode()
                        ).hexdigest()[:8]

                        # Check if this citation already has an embedding
                        current_embedding = self.storage_manager.registry.get_current_citation_embedding(
                            citation_hash
                        )
                        if current_embedding:
                            # Mark as obsolete
                            self.storage_manager.registry.mark_as_obsolete(
                                "citation", citation_hash, "source file updated"
                            )
                            outdated["citation_embeddings"].append(citation_hash)

                        processed_citation_hashes.add(citation_hash)

            except Exception as e:
                logging.warning(f"Error processing citation file {citation_file}: {e}")

        # Note: Composite embeddings will be regenerated when confidence scoring runs
        # after citation embeddings are updated

        return outdated

    def update_embeddings(
        self,
        outdated_embeddings: Dict[str, List[str]],
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        min_confidence: float = 0.4,
    ) -> Dict[str, int]:
        """
        Update outdated embeddings.

        Args:
            outdated_embeddings: Dict of outdated embedding IDs
            model_name: Model to use for embedding generation
            min_confidence: Minimum confidence for citation embeddings

        Returns:
            Dict with counts of updated embeddings
        """
        update_counts = {"datasets_updated": 0, "citations_updated": 0, "errors": 0}

        # Update dataset embeddings
        if outdated_embeddings["dataset_embeddings"]:
            logging.info(
                f"Updating {len(outdated_embeddings['dataset_embeddings'])} dataset embeddings"
            )

            try:
                count = generate_dataset_embeddings(
                    datasets_dir=self.datasets_dir,
                    embeddings_dir=self.embeddings_dir,
                    model_name=model_name,
                    batch_size=5,  # Smaller batch for updates
                    force_regenerate=True,  # Force regeneration of marked obsolete
                )
                update_counts["datasets_updated"] = count
            except Exception as e:
                logging.error(f"Error updating dataset embeddings: {e}")
                update_counts["errors"] += 1

        # Update citation embeddings
        if outdated_embeddings["citation_embeddings"]:
            logging.info(
                f"Updating {len(outdated_embeddings['citation_embeddings'])} citation embeddings"
            )

            try:
                count = generate_citation_embeddings(
                    citations_dir=self.citations_dir,
                    embeddings_dir=self.embeddings_dir,
                    model_name=model_name,
                    batch_size=25,  # Smaller batch for updates
                    force_regenerate=True,  # Force regeneration of marked obsolete
                    min_confidence=min_confidence,
                )
                update_counts["citations_updated"] = count
            except Exception as e:
                logging.error(f"Error updating citation embeddings: {e}")
                update_counts["errors"] += 1

        return update_counts

    def run_automated_update(
        self,
        check_interval_hours: int = 24,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        min_confidence: float = 0.4,
        max_age_days: int = 7,
    ) -> Dict:
        """
        Run automated update check and processing.

        Args:
            check_interval_hours: Hours since last check to trigger update
            model_name: Model for embedding generation
            min_confidence: Minimum confidence for citations
            max_age_days: Only check files modified in last N days

        Returns:
            Update results summary
        """
        state = self.load_update_state()

        # Check if we should run update
        last_update = state.get("last_update")
        if last_update:
            last_update_time = datetime.fromisoformat(last_update)
            time_since_update = datetime.now() - last_update_time

            if time_since_update < timedelta(hours=check_interval_hours):
                logging.info(
                    f"Skipping update - last update was {time_since_update.total_seconds() / 3600:.1f} hours ago"
                )
                return {"status": "skipped", "reason": "too_recent"}

        # Set cutoff time for file changes
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        since_time = last_update_time if last_update else cutoff_time

        logging.info(f"Checking for file changes since {since_time}")

        # Detect changed files
        changed_files = self.detect_changed_files(since_time)

        total_changed = len(changed_files["citation_files"]) + len(
            changed_files["dataset_files"]
        )

        if total_changed == 0:
            logging.info("No file changes detected")
            state["last_update"] = datetime.now().isoformat()
            self.save_update_state(state)
            return {"status": "no_changes", "changed_files": changed_files}

        logging.info(f"Detected {total_changed} changed files")
        logging.info(f"  - Citation files: {len(changed_files['citation_files'])}")
        logging.info(f"  - Dataset files: {len(changed_files['dataset_files'])}")

        # Identify outdated embeddings
        outdated_embeddings = self.identify_outdated_embeddings(changed_files)

        total_outdated = sum(len(items) for items in outdated_embeddings.values())

        if total_outdated == 0:
            logging.info("No embeddings need updating")
            state["last_update"] = datetime.now().isoformat()
            self.save_update_state(state)
            return {
                "status": "no_updates_needed",
                "changed_files": changed_files,
                "outdated_embeddings": outdated_embeddings,
            }

        logging.info(f"Found {total_outdated} outdated embeddings")

        # Update embeddings
        update_counts = self.update_embeddings(
            outdated_embeddings=outdated_embeddings,
            model_name=model_name,
            min_confidence=min_confidence,
        )

        # Update state
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "changed_files": {k: [str(f) for f in v] for k, v in changed_files.items()},
            "outdated_embeddings": outdated_embeddings,
            "update_counts": update_counts,
        }

        state["last_update"] = datetime.now().isoformat()
        state["update_history"].append(update_record)

        # Keep only last 10 update records
        if len(state["update_history"]) > 10:
            state["update_history"] = state["update_history"][-10:]

        self.save_update_state(state)

        return {
            "status": "updated",
            "update_record": update_record,
            "summary": {
                "total_changed_files": total_changed,
                "total_outdated_embeddings": total_outdated,
                "datasets_updated": update_counts["datasets_updated"],
                "citations_updated": update_counts["citations_updated"],
                "errors": update_counts["errors"],
            },
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated embedding updates when citation data changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run automated update check
  dataset-citations-automate-updates --citations-dir citations/ --datasets-dir datasets/

  # Force update check regardless of last update time
  dataset-citations-automate-updates --force-check

  # Custom check interval and file age limits
  dataset-citations-automate-updates --check-interval 12 --max-age-days 3

  # Show update history and status
  dataset-citations-automate-updates --show-status

  # Reset automation state (clears update history)
  dataset-citations-automate-updates --reset-state
        """,
    )

    parser.add_argument(
        "--embeddings-dir",
        type=Path,
        default="embeddings",
        help="Path to embeddings directory (default: embeddings)",
    )

    parser.add_argument(
        "--citations-dir",
        type=Path,
        default="citations",
        help="Path to citations directory (default: citations)",
    )

    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default="datasets",
        help="Path to datasets directory (default: datasets)",
    )

    parser.add_argument(
        "--check-interval",
        type=int,
        default=24,
        help="Hours between update checks (default: 24)",
    )

    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Only check files modified in last N days (default: 7)",
    )

    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Embedding model to use (default: Qwen/Qwen2.5-0.5B-Instruct)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.4,
        help="Minimum confidence score for citations (default: 0.4)",
    )

    parser.add_argument(
        "--force-check",
        action="store_true",
        help="Force update check regardless of last check time",
    )

    parser.add_argument(
        "--show-status", action="store_true", help="Show automation status and history"
    )

    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset automation state (clears history)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Validate inputs
    if not args.embeddings_dir.exists():
        logging.error(f"Embeddings directory not found: {args.embeddings_dir}")
        return 1

    if not args.citations_dir.exists():
        logging.error(f"Citations directory not found: {args.citations_dir}")
        return 1

    if not args.datasets_dir.exists():
        logging.error(f"Datasets directory not found: {args.datasets_dir}")
        return 1

    try:
        # Initialize automator
        automator = EmbeddingUpdateAutomator(
            embeddings_dir=args.embeddings_dir,
            citations_dir=args.citations_dir,
            datasets_dir=args.datasets_dir,
        )

        # Handle different modes
        if args.reset_state:
            # Reset state
            if automator.state_file.exists():
                automator.state_file.unlink()
            logging.info("✅ Automation state reset")
            return 0

        if args.show_status:
            # Show status
            state = automator.load_update_state()

            print("\n" + "=" * 60)
            print("AUTOMATION STATUS")
            print("=" * 60)

            last_update = state.get("last_update")
            if last_update:
                last_update_time = datetime.fromisoformat(last_update)
                time_since = datetime.now() - last_update_time
                print(
                    f"📅 Last Update: {last_update_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(
                    f"⏰ Time Since: {time_since.days} days, {time_since.seconds // 3600} hours"
                )
            else:
                print("📅 Last Update: Never")

            print(f"📁 Tracked Files: {len(state.get('file_hashes', {}))}")
            print(f"📊 Update History: {len(state.get('update_history', []))}")

            if state.get("update_history"):
                print("\n🔄 Recent Updates:")
                for i, record in enumerate(state["update_history"][-3:], 1):
                    timestamp = record["timestamp"]
                    counts = record["update_counts"]
                    print(
                        f"   {i}. {timestamp}: {counts['datasets_updated']} datasets, {counts['citations_updated']} citations"
                    )

            print("=" * 60)
            return 0

        # Run automated update
        logging.info("=" * 60)
        logging.info("AUTOMATED EMBEDDING UPDATE")
        logging.info("=" * 60)

        # Override check interval if force check
        check_interval = 0 if args.force_check else args.check_interval

        start_time = time.time()

        results = automator.run_automated_update(
            check_interval_hours=check_interval,
            model_name=args.model,
            min_confidence=args.min_confidence,
            max_age_days=args.max_age_days,
        )

        elapsed_time = time.time() - start_time

        # Display results
        print(f"\n🔄 Update Status: {results['status'].upper()}")

        if results["status"] == "updated":
            summary = results["summary"]
            print("📊 Summary:")
            print(f"   • Changed files: {summary['total_changed_files']}")
            print(f"   • Outdated embeddings: {summary['total_outdated_embeddings']}")
            print(f"   • Datasets updated: {summary['datasets_updated']}")
            print(f"   • Citations updated: {summary['citations_updated']}")
            if summary["errors"] > 0:
                print(f"   • Errors: {summary['errors']}")

        elif results["status"] == "no_changes":
            print("✅ No file changes detected")

        elif results["status"] == "skipped":
            print(f"⏭️  Skipped: {results['reason']}")

        print(f"⏱️  Total time: {elapsed_time:.1f} seconds")

        return 0

    except Exception as e:
        logging.error(f"Error during automated update: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
