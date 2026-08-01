"""Timestamp helpers for reading values written before the UTC-aware switch.

Issue #199 moved every `datetime.now()` in this package to `datetime.now(UTC)`
so timestamps are timezone-aware (ruff's DTZ rules). Data already on disk,
though, was written naive: embedding registries carry entries like
`"created": "2026-06-13T15:32:47.301682"` with no offset, and subtracting one
of those from an aware `datetime.now(UTC)` raises

    TypeError: can't subtract offset-naive and offset-aware datetimes

at runtime, not at lint time. Every site that parses a stored timestamp and
compares it against "now" must therefore normalize on read.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso_utc(raw: str) -> datetime:
    """Parse an ISO 8601 timestamp, treating a naive value as UTC.

    Timestamps written since issue #199 already carry an offset and pass
    through unchanged; older naive ones are assumed UTC, which is what the
    code that wrote them meant on a UTC-configured host.

    Raises `ValueError` on an unparseable string, same as
    `datetime.fromisoformat`, so callers that already handle that keep working.
    """
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
