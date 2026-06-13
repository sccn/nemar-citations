"""Tests for the throttled GitHub client builder (#124).

Env resolution is exercised with real os.environ manipulation (monkeypatch is
env plumbing, not a service mock), and build_github constructs a real PyGithub
client (no network happens at construction time).
"""

from __future__ import annotations

from dataset_citations.utils.github_client import (
    _DEFAULT_SPACING,
    build_github,
    github_request_spacing,
)

_ENV = "GITHUB_SECONDS_BETWEEN_REQUESTS"


def test_default_spacing(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    assert github_request_spacing() == _DEFAULT_SPACING


def test_env_override(monkeypatch):
    monkeypatch.setenv(_ENV, "2.5")
    assert github_request_spacing() == 2.5


def test_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv(_ENV, "not-a-number")
    assert github_request_spacing() == _DEFAULT_SPACING


def test_negative_env_falls_back(monkeypatch):
    monkeypatch.setenv(_ENV, "-3")
    assert github_request_spacing() == _DEFAULT_SPACING


def test_build_github_constructs_without_token(monkeypatch):
    monkeypatch.setenv(_ENV, "1.0")
    client = build_github()
    assert client is not None


def test_build_github_constructs_with_token_and_timeout(monkeypatch):
    monkeypatch.setenv(_ENV, "1.0")
    client = build_github("fake-token-not-used-offline", timeout=30)
    assert client is not None
