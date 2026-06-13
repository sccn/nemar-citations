"""Tests for nightly metadata-retrieval resilience (issue #118).

The unit tests exercise the pure exit-code policy with real integers (no
mocks). The integration test hits the real GitHub repo whose oversized file
(``ds002001``) used to crash the whole nightly cron; it is gated behind
RUN_INTEGRATION_TESTS so the fast suite stays offline.
"""

from __future__ import annotations

import os

import pytest

from dataset_citations.cli.retrieve_metadata import resolve_exit_code


def test_no_failures_is_success():
    assert resolve_exit_code(successful=10, skipped=0, failed=0, max_failures=0) == 0


def test_single_failure_is_fatal_under_strict_default():
    # The exact ds002001 cron case: 0 new, 592 cached, 1 failed, strict.
    assert resolve_exit_code(successful=0, skipped=592, failed=1, max_failures=0) == 1


def test_single_failure_tolerated_when_cron_opts_in():
    # The fix: the cron passes --max-failures 10, so 1 failure no longer aborts.
    assert resolve_exit_code(successful=0, skipped=592, failed=1, max_failures=10) == 0


def test_failures_exceeding_threshold_still_fail():
    assert resolve_exit_code(successful=0, skipped=580, failed=13, max_failures=10) == 1


def test_threshold_is_inclusive():
    assert resolve_exit_code(successful=0, skipped=0, failed=10, max_failures=10) == 0
    assert resolve_exit_code(successful=0, skipped=0, failed=11, max_failures=10) == 1


@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS") or not os.getenv("GITHUB_TOKEN"),
    reason="needs network + GITHUB_TOKEN",
)
def test_undecodable_file_does_not_crash_dataset_retrieval():
    """ds002001 has a file PyGithub cannot decode; retrieval must not raise.

    Before the fix this raised AssertionError('unsupported encoding: None')
    out of get_dataset_metadata, counting the dataset as failed and (under the
    strict default) aborting the nightly cron.
    """
    from dataset_citations.quality.dataset_metadata import DatasetMetadataRetriever

    retriever = DatasetMetadataRetriever(os.getenv("GITHUB_TOKEN"))
    metadata = retriever.get_dataset_metadata("ds002001")

    # The repo is found, so the dataset is usable even though the oversized
    # file could not be decoded; the CLI counts this as successful, not failed.
    assert metadata["retrieval_status"]["repository"] == "success"
    assert metadata["github_info"]["exists"] is True
