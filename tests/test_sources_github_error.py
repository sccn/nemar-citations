"""Tests for the `_github_error` mapper used by both source modules.

We construct real `GithubException` instances (no mocks) and assert the
FetchError reasons match the project's retry contract.
"""

from __future__ import annotations

from unittest import TestCase

from github.GithubException import GithubException

from dataset_citations.sources.bids_metadata import _github_error as bids_github_error
from dataset_citations.sources.nemar_metadata import (
    _github_error as nemar_github_error,
)


def _exc(status: int) -> GithubException:
    return GithubException(status, {"message": "boom"}, headers={})


class NemarGithubErrorMappingTests(TestCase):
    def test_404_is_not_found(self) -> None:
        err = nemar_github_error(_exc(404), ".nemar/metadata.json")
        self.assertEqual(err.reason, "not_found")

    def test_401_is_auth(self) -> None:
        err = nemar_github_error(_exc(401), ".nemar/metadata.json")
        self.assertEqual(err.reason, "auth")

    def test_403_is_auth(self) -> None:
        err = nemar_github_error(_exc(403), ".nemar/metadata.json")
        self.assertEqual(err.reason, "auth")

    def test_429_is_rate_limit(self) -> None:
        err = nemar_github_error(_exc(429), ".nemar/metadata.json")
        self.assertEqual(err.reason, "rate_limit")

    def test_500_is_other(self) -> None:
        err = nemar_github_error(_exc(500), ".nemar/metadata.json")
        self.assertEqual(err.reason, "other")


class BidsGithubErrorMappingTests(TestCase):
    """The bids source has its own _github_error helper; verify parity."""

    def test_404_is_not_found(self) -> None:
        err = bids_github_error(_exc(404), "dataset_description.json")
        self.assertEqual(err.reason, "not_found")

    def test_401_is_auth(self) -> None:
        err = bids_github_error(_exc(401), "dataset_description.json")
        self.assertEqual(err.reason, "auth")

    def test_429_is_rate_limit(self) -> None:
        err = bids_github_error(_exc(429), "dataset_description.json")
        self.assertEqual(err.reason, "rate_limit")

    def test_500_is_other(self) -> None:
        err = bids_github_error(_exc(500), "dataset_description.json")
        self.assertEqual(err.reason, "other")
