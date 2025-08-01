"""
CLI command for automating visualization and report updates.

This module provides an automated pipeline that detects changes in citation/dataset data
and regenerates visualizations, interactive reports, and export files accordingly.
"""

import argparse
import logging
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class VisualizationUpdatePipeline:
    """Automated pipeline for keeping visualizations and reports up-to-date."""

    def __init__(
        self, data_dirs: List[Path], output_dir: Path, state_file: Optional[Path] = None
    ):
        """
        Initialize the update pipeline.

        Args:
            data_dirs: Directories containing source data to monitor
            output_dir: Directory for generated outputs
            state_file: File to store pipeline state (optional)
        """
        self.data_dirs = [Path(d) for d in data_dirs]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = state_file or (self.output_dir / "pipeline_state.json")
        self.pipeline_state = self._load_pipeline_state()

        # Configure monitoring patterns
        self.monitored_patterns = [
            "*citations.json",
            "*datasets.json",
            "*.csv",
            "*.pkl",
            "embeddings/*.pkl",
            "embeddings/*.json",
        ]

        # Pipeline stages
        self.pipeline_stages = [
            "embedding_generation",
            "network_analysis",
            "temporal_analysis",
            "theme_analysis",
            "visualization_generation",
            "interactive_reports",
            "external_exports",
        ]

    def _load_pipeline_state(self) -> Dict[str, Any]:
        """Load pipeline state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Could not load pipeline state: {e}")

        return {
            "last_update": None,
            "file_hashes": {},
            "stage_timestamps": {},
            "failed_stages": [],
            "update_count": 0,
        }

    def _save_pipeline_state(self) -> None:
        """Save pipeline state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.pipeline_state, f, indent=2)
        except Exception as e:
            logging.error(f"Could not save pipeline state: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents."""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logging.warning(f"Could not hash file {file_path}: {e}")
            return ""

    def detect_file_changes(self) -> Dict[str, List[Path]]:
        """
        Detect changed files since last update.

        Returns:
            Dictionary mapping change types to file lists
        """
        logging.info("Detecting file changes...")

        changes = {"modified": [], "added": [], "deleted": []}

        current_files = {}
        stored_hashes = self.pipeline_state.get("file_hashes", {})

        # Scan all monitored directories
        for data_dir in self.data_dirs:
            if not data_dir.exists():
                continue

            for pattern in self.monitored_patterns:
                for file_path in data_dir.glob(f"**/{pattern}"):
                    if file_path.is_file():
                        file_key = str(file_path.relative_to(data_dir))
                        current_hash = self._calculate_file_hash(file_path)
                        current_files[file_key] = {
                            "path": file_path,
                            "hash": current_hash,
                        }

                        # Check for changes
                        if file_key in stored_hashes:
                            if stored_hashes[file_key] != current_hash:
                                changes["modified"].append(file_path)
                        else:
                            changes["added"].append(file_path)

        # Detect deleted files
        for file_key in stored_hashes:
            if file_key not in current_files:
                # Reconstruct path for deleted file
                for data_dir in self.data_dirs:
                    deleted_path = data_dir / file_key
                    if not deleted_path.exists():
                        changes["deleted"].append(deleted_path)
                        break

        # Update stored hashes
        self.pipeline_state["file_hashes"] = {
            key: info["hash"] for key, info in current_files.items()
        }

        total_changes = sum(len(files) for files in changes.values())
        logging.info(f"Detected {total_changes} file changes")

        return changes

    def should_update(self, force_update: bool = False) -> bool:
        """
        Determine if pipeline should run based on changes or schedule.

        Args:
            force_update: Force update regardless of changes

        Returns:
            True if update should proceed
        """
        if force_update:
            logging.info("Force update requested")
            return True

        # Check for file changes
        changes = self.detect_file_changes()
        if any(changes.values()):
            logging.info("File changes detected, update needed")
            return True

        # Check if enough time has passed since last update
        last_update = self.pipeline_state.get("last_update")
        if last_update:
            last_update_time = datetime.fromisoformat(last_update)
            time_since_update = datetime.now() - last_update_time

            # Update weekly even without changes
            if time_since_update > timedelta(days=7):
                logging.info("Weekly update due")
                return True
        else:
            logging.info("No previous update found")
            return True

        logging.info("No update needed")
        return False

    def run_pipeline_stage(self, stage_name: str, **kwargs) -> bool:
        """
        Run a specific pipeline stage.

        Args:
            stage_name: Name of the stage to run
            **kwargs: Additional arguments for the stage

        Returns:
            True if stage completed successfully
        """
        logging.info(f"Running pipeline stage: {stage_name}")

        try:
            start_time = datetime.now()

            if stage_name == "embedding_generation":
                success = self._run_embedding_generation(**kwargs)
            elif stage_name == "network_analysis":
                success = self._run_network_analysis(**kwargs)
            elif stage_name == "temporal_analysis":
                success = self._run_temporal_analysis(**kwargs)
            elif stage_name == "theme_analysis":
                success = self._run_theme_analysis(**kwargs)
            elif stage_name == "visualization_generation":
                success = self._run_visualization_generation(**kwargs)
            elif stage_name == "interactive_reports":
                success = self._run_interactive_reports(**kwargs)
            elif stage_name == "external_exports":
                success = self._run_external_exports(**kwargs)
            else:
                logging.error(f"Unknown pipeline stage: {stage_name}")
                return False

            # Record stage completion
            if success:
                self.pipeline_state["stage_timestamps"][stage_name] = (
                    start_time.isoformat()
                )
                if stage_name in self.pipeline_state.get("failed_stages", []):
                    self.pipeline_state["failed_stages"].remove(stage_name)
                logging.info(f"Stage '{stage_name}' completed successfully")
            else:
                if "failed_stages" not in self.pipeline_state:
                    self.pipeline_state["failed_stages"] = []
                if stage_name not in self.pipeline_state["failed_stages"]:
                    self.pipeline_state["failed_stages"].append(stage_name)
                logging.error(f"Stage '{stage_name}' failed")

            return success

        except Exception as e:
            logging.error(f"Stage '{stage_name}' failed with exception: {e}")
            return False

    def _run_command(self, command: List[str], description: str) -> bool:
        """Run a command and return success status."""
        try:
            logging.debug(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                logging.info(f"{description} completed successfully")
                if result.stdout:
                    logging.debug(f"Output: {result.stdout}")
                return True
            else:
                logging.error(f"{description} failed with code {result.returncode}")
                if result.stderr:
                    logging.error(f"Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logging.error(f"{description} timed out")
            return False
        except Exception as e:
            logging.error(f"{description} failed: {e}")
            return False

    def _run_embedding_generation(self, **kwargs) -> bool:
        """Run embedding generation stage."""
        command = [
            "dataset-citations-generate-embeddings",
            "--embedding-type",
            "both",
            "--min-confidence",
            "0.4",
            "--batch-size",
            "25",
        ]

        if kwargs.get("verbose"):
            command.append("--verbose")

        return self._run_command(command, "Embedding generation")

    def _run_network_analysis(self, **kwargs) -> bool:
        """Run network analysis stage."""
        command = [
            "dataset-citations-analyze-networks",
            "--all-analyses",
            "--output-format",
            "both",
        ]

        if kwargs.get("confidence_threshold"):
            command.extend(
                ["--confidence-threshold", str(kwargs["confidence_threshold"])]
            )

        return self._run_command(command, "Network analysis")

    def _run_temporal_analysis(self, **kwargs) -> bool:
        """Run temporal analysis stage."""
        command = [
            "dataset-citations-analyze-temporal",
            "--create-visualizations",
            "--export-data",
        ]

        return self._run_command(command, "Temporal analysis")

    def _run_theme_analysis(self, **kwargs) -> bool:
        """Run theme analysis stage."""
        # Run UMAP analysis
        umap_success = self._run_command(
            [
                "dataset-citations-analyze-umap",
                "--clustering",
                "--create-visualizations",
            ],
            "UMAP analysis",
        )

        # Run theme networks
        theme_success = self._run_command(
            [
                "dataset-citations-create-theme-networks",
                "--create-networks",
                "--create-word-clouds",
            ],
            "Theme networks",
        )

        # Run research context networks
        context_success = self._run_command(
            [
                "dataset-citations-create-research-context-networks",
                "--similarity-threshold",
                "0.6",
                "--create-visualizations",
            ],
            "Research context networks",
        )

        return umap_success and theme_success and context_success

    def _run_visualization_generation(self, **kwargs) -> bool:
        """Run visualization generation stage."""
        command = [
            "dataset-citations-create-network-visualizations",
            "--all-visualizations",
            "--output-format",
            "both",
        ]

        return self._run_command(command, "Network visualizations")

    def _run_interactive_reports(self, **kwargs) -> bool:
        """Run interactive reports generation stage."""
        command = [
            "dataset-citations-create-interactive-reports",
            "--results-dir",
            str(self.output_dir / "results"),
            "--output-dir",
            str(self.output_dir / "interactive_reports"),
        ]

        if kwargs.get("verbose"):
            command.append("--verbose")

        return self._run_command(command, "Interactive reports")

    def _run_external_exports(self, **kwargs) -> bool:
        """Run external tool exports stage."""
        # Export from network analysis results
        results_dir = self.output_dir / "results"
        if not results_dir.exists():
            logging.warning("No results directory found for export")
            return True  # Not a failure, just no data to export

        command = [
            "dataset-citations-export-external-tools",
            "--input",
            str(results_dir),
            "--output-dir",
            str(self.output_dir / "exports"),
            "--format",
            "all",
        ]

        if kwargs.get("verbose"):
            command.append("--verbose")

        return self._run_command(command, "External tool exports")

    def run_full_pipeline(
        self,
        force_update: bool = False,
        stages: Optional[List[str]] = None,
        **stage_kwargs,
    ) -> bool:
        """
        Run the complete visualization update pipeline.

        Args:
            force_update: Force update regardless of changes
            stages: Specific stages to run (default: all)
            **stage_kwargs: Additional arguments for stages

        Returns:
            True if pipeline completed successfully
        """
        logging.info("Starting visualization update pipeline")

        # Check if update is needed
        if not self.should_update(force_update):
            logging.info("No update needed, pipeline skipped")
            return True

        # Determine stages to run
        stages_to_run = stages or self.pipeline_stages

        pipeline_start = datetime.now()
        successful_stages = []
        failed_stages = []

        # Run each stage
        for stage in stages_to_run:
            logging.info(
                f"Pipeline stage {len(successful_stages) + 1}/{len(stages_to_run)}: {stage}"
            )

            if self.run_pipeline_stage(stage, **stage_kwargs):
                successful_stages.append(stage)
            else:
                failed_stages.append(stage)

                # Stop pipeline on critical failures
                if stage in ["embedding_generation", "network_analysis"]:
                    logging.error(f"Critical stage '{stage}' failed, stopping pipeline")
                    break

        # Update pipeline state
        self.pipeline_state["last_update"] = pipeline_start.isoformat()
        self.pipeline_state["update_count"] = (
            self.pipeline_state.get("update_count", 0) + 1
        )
        self._save_pipeline_state()

        # Report results
        pipeline_duration = datetime.now() - pipeline_start

        if failed_stages:
            logging.warning(
                f"Pipeline completed with {len(failed_stages)} failed stages"
            )
            logging.warning(f"Failed stages: {', '.join(failed_stages)}")
        else:
            logging.info("Pipeline completed successfully")

        logging.info(f"Pipeline duration: {pipeline_duration}")
        logging.info(
            f"Successful stages: {len(successful_stages)}/{len(stages_to_run)}"
        )

        return len(failed_stages) == 0

    def setup_scheduled_updates(
        self, schedule_type: str = "daily", time_of_day: str = "02:00"
    ) -> None:
        """
        Set up scheduled automatic updates using cron (Linux/Mac) or Task Scheduler (Windows).

        Args:
            schedule_type: Type of schedule (daily, weekly, monthly)
            time_of_day: Time to run updates (HH:MM format)
        """
        logging.info(f"Setting up {schedule_type} scheduled updates at {time_of_day}")

        # Create update script
        script_content = f"""#!/bin/bash
# Automated visualization update script
# Generated by dataset-citations-automate-visualization-updates

cd "{Path.cwd()}"

# Activate conda environment if available
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate dataset-citations 2>/dev/null || true
fi

# Run the update pipeline
dataset-citations-automate-visualization-updates \\
    --data-dirs {" ".join(str(d) for d in self.data_dirs)} \\
    --output-dir "{self.output_dir}" \\
    --force-update \\
    --verbose

# Log completion
echo "Scheduled update completed at $(date)" >> "{self.output_dir}/update_log.txt"
"""

        script_file = self.output_dir / "automated_update.sh"
        with open(script_file, "w") as f:
            f.write(script_content)

        # Make script executable
        script_file.chmod(0o755)

        logging.info(f"Update script created: {script_file}")
        logging.info("To enable scheduled updates:")
        logging.info(
            f"  Linux/Mac: Add to crontab: 0 {time_of_day.split(':')[1]} {time_of_day.split(':')[0]} * * {script_file}"
        )
        logging.info(f"  Windows: Use Task Scheduler to run: {script_file}")

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics."""
        status = {
            "last_update": self.pipeline_state.get("last_update"),
            "update_count": self.pipeline_state.get("update_count", 0),
            "failed_stages": self.pipeline_state.get("failed_stages", []),
            "stage_timestamps": self.pipeline_state.get("stage_timestamps", {}),
            "monitored_files": len(self.pipeline_state.get("file_hashes", {})),
            "data_directories": [str(d) for d in self.data_dirs],
            "output_directory": str(self.output_dir),
        }

        # Calculate time since last update
        if status["last_update"]:
            last_update_time = datetime.fromisoformat(status["last_update"])
            status["time_since_update"] = str(datetime.now() - last_update_time)

        return status


def main() -> int:
    """Main entry point for visualization update automation."""
    parser = argparse.ArgumentParser(
        description="Automate visualization and report updates"
    )
    parser.add_argument(
        "--data-dirs",
        nargs="+",
        type=Path,
        default=[Path("citations"), Path("datasets"), Path("embeddings")],
        help="Directories to monitor for data changes",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory for generated files (default: results)",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update regardless of file changes",
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=[
            "embedding_generation",
            "network_analysis",
            "temporal_analysis",
            "theme_analysis",
            "visualization_generation",
            "interactive_reports",
            "external_exports",
        ],
        help="Specific stages to run (default: all)",
    )
    parser.add_argument(
        "--schedule",
        choices=["daily", "weekly", "monthly"],
        help="Set up scheduled updates",
    )
    parser.add_argument(
        "--schedule-time",
        default="02:00",
        help="Time for scheduled updates (HH:MM format, default: 02:00)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status and exit",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.4,
        help="Confidence threshold for citations (default: 0.4)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Validate data directories
    existing_dirs = [d for d in args.data_dirs if d.exists()]
    if not existing_dirs:
        logging.error("No valid data directories found")
        return 1

    try:
        # Initialize pipeline
        pipeline = VisualizationUpdatePipeline(
            data_dirs=existing_dirs, output_dir=args.output_dir
        )

        # Handle status request
        if args.status:
            status = pipeline.get_pipeline_status()
            print("\n📊 Pipeline Status")
            print(f"   Last update: {status['last_update'] or 'Never'}")
            print(f"   Update count: {status['update_count']}")
            print(f"   Monitored files: {status['monitored_files']}")
            print(f"   Failed stages: {len(status['failed_stages'])}")
            if status.get("time_since_update"):
                print(f"   Time since update: {status['time_since_update']}")
            return 0

        # Handle scheduled setup
        if args.schedule:
            pipeline.setup_scheduled_updates(args.schedule, args.schedule_time)
            return 0

        # Run pipeline
        stage_kwargs = {
            "verbose": args.verbose,
            "confidence_threshold": args.confidence_threshold,
        }

        success = pipeline.run_full_pipeline(
            force_update=args.force_update, stages=args.stages, **stage_kwargs
        )

        # Report results
        status = pipeline.get_pipeline_status()

        print("\n🔄 Pipeline Update Completed!")
        print(f"   Success: {'✅' if success else '❌'}")
        print(f"   Update count: {status['update_count']}")
        print(f"   Failed stages: {len(status['failed_stages'])}")

        if status["failed_stages"]:
            print(f"   Failed: {', '.join(status['failed_stages'])}")

        print(f"\n📁 Output directory: {args.output_dir}")
        print(f"🌐 Interactive reports: {args.output_dir}/interactive_reports/")
        print(f"📊 Exports: {args.output_dir}/exports/")

        return 0 if success else 1

    except Exception as e:
        logging.error(f"Pipeline automation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
