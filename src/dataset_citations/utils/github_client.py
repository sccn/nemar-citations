"""Shared PyGithub client builder with request spacing.

A full citation re-fetch loops `get_repo` + `get_contents` over hundreds of
legacy ds-* datasets to extract DOI anchors. Unspaced, that burst trips
GitHub's *secondary* (abuse) rate limit even though the primary 5000/hr budget
is nearly untouched, and PyGithub then backs off for the full primary-reset
window (~59 min) on a single request, stalling the whole pipeline.

Spacing requests a minimum interval apart keeps the burst under the secondary
limit. The interval is configurable via ``GITHUB_SECONDS_BETWEEN_REQUESTS``
(default 1.0s ~= 60 req/min) so a dedicated host can speed it up or a throttled
one can slow it down without code changes.
"""

from __future__ import annotations

import os

from github import Auth, Github

_ENV_SPACING = "GITHUB_SECONDS_BETWEEN_REQUESTS"
_DEFAULT_SPACING = 1.0


def github_request_spacing() -> float:
    """Minimum seconds between GitHub requests (env-configurable, >= 0)."""
    raw = os.getenv(_ENV_SPACING)
    if raw is None:
        return _DEFAULT_SPACING
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_SPACING
    return value if value >= 0 else _DEFAULT_SPACING


def build_github(token: str | None = None, *, timeout: int | None = None) -> Github:
    """Return a PyGithub client throttled to stay under the secondary limit."""
    auth = Auth.Token(token) if token else None
    spacing = github_request_spacing()
    if timeout is None:
        return Github(auth=auth, seconds_between_requests=spacing)
    return Github(auth=auth, seconds_between_requests=spacing, timeout=timeout)
