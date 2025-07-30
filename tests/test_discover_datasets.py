import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests  # Import requests for requests.Response

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataset_citations.cli.discover import check_repository_for_modalities


class TestDiscoverDatasets(unittest.TestCase):
    def _mock_response(self, status_code, json_data=None, headers=None):
        """Helper to create a MagicMock for requests.Response"""
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = status_code
        mock_resp.json = MagicMock(
            return_value=json_data if json_data is not None else {}
        )
        mock_resp.headers = headers if headers is not None else {}
        if status_code >= 400:
            mock_resp.raise_for_status = MagicMock(
                side_effect=requests.exceptions.HTTPError(response=mock_resp)
            )
        else:
            mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_eeg_present(self, mock_get_api_response):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "sub-01", "type": "dir", "url": "url_to_sub_01"}]
        )
        mock_sub_response = self._mock_response(
            200, json_data=[{"name": "eeg", "type": "dir"}]
        )
        mock_get_api_response.side_effect = [mock_root_response, mock_sub_response]

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000001", "OpenNeuroDatasets", headers
        )
        self.assertIn("eeg", found_modalities)
        self.assertEqual(len(found_modalities), 1)

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_multiple_modalities_present(
        self, mock_get_api_response
    ):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "sub-01", "type": "dir", "url": "url_to_sub_01"}]
        )
        mock_sub_response = self._mock_response(
            200,
            json_data=[
                {"name": "eeg", "type": "dir"},
                {"name": "meg", "type": "dir"},
                {"name": "anat", "type": "dir"},  # Non-target
            ],
        )
        mock_get_api_response.side_effect = [mock_root_response, mock_sub_response]

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000002", "OpenNeuroDatasets", headers
        )
        self.assertIn("eeg", found_modalities)
        self.assertIn("meg", found_modalities)
        self.assertNotIn("anat", found_modalities)
        self.assertEqual(len(found_modalities), 2)

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_no_target_modalities(
        self, mock_get_api_response
    ):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "sub-01", "type": "dir", "url": "url_to_sub_01"}]
        )
        mock_sub_response = self._mock_response(
            200,
            json_data=[
                {"name": "anat", "type": "dir"},
                {"name": "func", "type": "dir"},
            ],
        )
        mock_get_api_response.side_effect = [mock_root_response, mock_sub_response]

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000003", "OpenNeuroDatasets", headers
        )
        self.assertEqual(len(found_modalities), 0)

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_no_sub_directories(
        self, mock_get_api_response
    ):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "README.md", "type": "file"}]
        )
        # The second call for subject directory contents should not happen.
        mock_get_api_response.return_value = mock_root_response

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000004", "OpenNeuroDatasets", headers
        )
        self.assertEqual(len(found_modalities), 0)
        mock_get_api_response.assert_called_once()  # Ensure we only called for root

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_api_error_root(
        self, mock_get_api_response
    ):
        # Simulate get_github_api_response returning None due to critical error
        mock_get_api_response.return_value = None

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000005", "OpenNeuroDatasets", headers
        )
        self.assertEqual(len(found_modalities), 0)

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_api_error_subject(
        self, mock_get_api_response
    ):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "sub-01", "type": "dir", "url": "url_to_sub_01"}]
        )
        # Simulate get_github_api_response returning None for the subject directory call
        mock_get_api_response.side_effect = [mock_root_response, None]

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000006", "OpenNeuroDatasets", headers
        )
        self.assertEqual(len(found_modalities), 0)

    @patch("dataset_citations.cli.discover.get_github_api_response")
    def test_check_repository_for_modalities_empty_subject_dir(
        self, mock_get_api_response
    ):
        mock_root_response = self._mock_response(
            200, json_data=[{"name": "sub-01", "type": "dir", "url": "url_to_sub_01"}]
        )
        mock_sub_response = self._mock_response(
            200,
            json_data=[],  # Empty subject directory
        )
        mock_get_api_response.side_effect = [mock_root_response, mock_sub_response]

        headers = {"Authorization": "token test_token"}
        found_modalities = check_repository_for_modalities(
            "ds000007", "OpenNeuroDatasets", headers
        )
        self.assertEqual(len(found_modalities), 0)


if __name__ == "__main__":
    unittest.main()
