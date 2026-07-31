"""Per-stage `{dataset_id: last_checked_iso}` caches backing freshness gates.

Pipeline stages that hit a rate-limited external API (`cli/update.py` against
opencite, `cli/find_mentions.py` against OpenAlex) skip datasets they checked
recently. The timestamp driving that gate is kept in a gitignored sidecar next
to the citation JSONs rather than inside them: `date_last_updated` in the
committed JSON means "last content change" (issue #165), so it cannot double as
the freshness signal without churning every diff.

Each stage owns its own state file so their windows advance independently.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


def load_state(path: str) -> dict[str, str]:
    """Load a `{dataset_id: iso_timestamp}` cache; empty dict if absent.

    A missing file is an expected cold-start case and returns `{}` silently. A
    file that exists but cannot be read/parsed is logged at WARNING, because
    silently treating a corrupt cache as absent would re-check every dataset
    every run with no trace in the cron log.
    """
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read state cache %s (%s); treating as empty", path, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("State cache %s is not a JSON object; treating as empty", path)
        return {}
    valid = {k: v for k, v in data.items() if isinstance(v, str)}
    dropped = len(data) - len(valid)
    if dropped:
        logger.warning(
            "state cache %s: dropped %d entries with non-string values", path, dropped
        )
    return valid


def save_state(path: str, state: dict[str, str]) -> None:
    """Persist the state cache. Best-effort: log and continue on failure.

    Logged at ERROR (not WARNING): a failed save means the next run starts from
    a cold cache and re-checks every dataset, and the same disk/permission
    condition likely failed the citation writes too, so it must be visible in
    the cron log.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
    except OSError as e:
        logger.error("Could not write state cache %s: %s", path, e)


def parse_checked_at(state: dict[str, str], dataset_id: str) -> datetime | None:
    """Return `dataset_id`'s last-checked time, or None if absent/unparseable.

    Naive timestamps are read as UTC, matching what `stamp_checked` writes.
    """
    raw = state.get(dataset_id)
    if not isinstance(raw, str):
        return None
    try:
        checked_at = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    return checked_at


def checked_within(
    dataset_id: str, state: dict[str, str], max_age_seconds: int
) -> bool:
    """Return True if `dataset_id` was checked within `max_age_seconds`.

    Any missing entry or unparseable timestamp returns False (re-check).
    """
    checked_at = parse_checked_at(state, dataset_id)
    if checked_at is None:
        return False
    return datetime.now(UTC) - checked_at <= timedelta(seconds=max_age_seconds)


def stamp_checked(state: dict[str, str], dataset_id: str) -> None:
    """Record `dataset_id` as checked now (UTC, ISO 8601)."""
    state[dataset_id] = datetime.now(UTC).isoformat()


def stalest_first(dataset_ids: list[str], state: dict[str, str]) -> list[str]:
    """Order datasets by how long since they were last checked, stalest first.

    Never-checked datasets sort ahead of every checked one. Ties (including the
    whole never-checked group on a cold start) keep the caller's input order,
    which is alphabetical for a directory glob, so a truncated run is
    reproducible rather than arbitrary.
    """
    epoch = datetime.min.replace(tzinfo=UTC)
    position = {d: i for i, d in enumerate(dataset_ids)}
    return sorted(
        dataset_ids,
        key=lambda d: (parse_checked_at(state, d) or epoch, position[d]),
    )
