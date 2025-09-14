"""
Asset management for dashboard files and resources.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List


class AssetManager:
    """Manage dashboard assets and support files."""

    def __init__(self, output_dir: Path):
        """
        Initialize asset manager.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.data_dir = self.output_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_data_file(self, data: Dict[str, Any]) -> str:
        """
        Create external data file for lazy loading.

        Args:
            data: Data to save

        Returns:
            Relative path to data file
        """
        data_file = self.data_dir / "complete_analysis_data_clean.json"

        # Clean and optimize data for web
        clean_data = self._clean_data_for_web(data)

        with open(data_file, "w") as f:
            json.dump({"analysisData": clean_data}, f, separators=(",", ":"))

        return "data/complete_analysis_data_clean.json"

    def copy_support_files(self):
        """Copy JavaScript and CSS support files."""
        # Check if support files exist in interactive_reports
        source_dir = Path("interactive_reports")

        files_to_copy = ["dashboard_templates.js", "dashboard_styles.css"]

        for file_name in files_to_copy:
            source_file = source_dir / file_name
            if source_file.exists():
                dest_file = self.output_dir / file_name
                shutil.copy2(source_file, dest_file)

    def copy_theme_images(self, image_files: List[str]):
        """
        Copy theme wordcloud images.

        Args:
            image_files: List of image filenames to copy
        """
        source_dir = Path("interactive_reports")

        for image_file in image_files:
            source_file = source_dir / image_file
            if source_file.exists():
                dest_file = self.output_dir / image_file
                shutil.copy2(source_file, dest_file)

    def _clean_data_for_web(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and optimize data for web usage.

        Args:
            data: Raw data

        Returns:
            Cleaned data
        """
        # Remove any None values and convert to web-friendly format
        clean_data = {}

        for key, value in data.items():
            if value is not None:
                if isinstance(value, Path):
                    clean_data[key] = str(value)
                elif isinstance(value, dict):
                    clean_data[key] = self._clean_data_for_web(value)
                elif isinstance(value, list):
                    clean_data[key] = [
                        self._clean_data_for_web(item)
                        if isinstance(item, dict)
                        else item
                        for item in value
                    ]
                else:
                    clean_data[key] = value

        return clean_data
