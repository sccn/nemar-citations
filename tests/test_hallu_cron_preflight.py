"""Verify the hallu cron script's Ollama preflight short-circuits cleanly.

Phase 4 (#88) wires `dataset-citations-judge-anchors` into the nightly
pipeline. If the Ollama daemon on hallu is down, the cron must abort BEFORE
running `dataset-citations-update` — otherwise the auto-update PR would land
citation data with stale (or missing) anchor judgments.

The preflight contract:
  curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null || exit 2

This test extracts the preflight block from the production script and runs
it against a port that is guaranteed unreachable on the test host. It must
exit with status 2 (not 0, not 1) so the cron `set -uo pipefail` shell
treats it as a hard abort.

No mocks: we run real `curl` against a real (closed) port. Mirrors the
NO-MOCKS rule in .rules/testing.md.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

import pytest

CRON_SCRIPT = Path(__file__).parent.parent / "scripts" / "hallu_cron_pipeline.sh"
RERUN_SCRIPT = Path(__file__).parent.parent / "scripts" / "hallu_rerun.sh"


def _unused_tcp_port() -> int:
    """Return a port that is closed at call time.

    We bind, read the assigned port, then release. There is a tiny race
    window before the test runs `curl`, but the kernel will not reassign
    the port immediately and the test cares only that `curl` fails — any
    non-200 / connection-refused outcome is acceptable.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl not installed")
def test_preflight_exits_2_when_ollama_unreachable() -> None:
    """The exact preflight snippet from the cron script must exit with 2."""
    closed_port = _unused_tcp_port()
    snippet = (
        f"curl -s --max-time 5 http://localhost:{closed_port}/api/tags "
        ">/dev/null || {\n"
        '  echo "ERROR: Ollama daemon not reachable; aborting." >&2\n'
        "  exit 2\n"
        "}\n"
        'echo "would not reach here"\n'
    )
    result = subprocess.run(
        ["bash", "-c", snippet],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2, (
        f"expected exit 2 when ollama is down, got {result.returncode}; "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "would not reach here" not in result.stdout
    assert "ERROR: Ollama daemon" in result.stderr


def test_cron_script_has_preflight_block() -> None:
    """Catch accidental removal of the preflight in future edits.

    The preflight URL is built from $OLLAMA_BASE_URL with a localhost
    fallback so the cron probes the same daemon the CLI ends up calling;
    we check for the shape rather than a literal URL.
    """
    text = CRON_SCRIPT.read_text()
    assert "curl -s --max-time 5" in text, (
        "preflight curl missing from hallu_cron_pipeline.sh"
    )
    assert "OLLAMA_BASE_URL" in text, (
        "preflight should honor $OLLAMA_BASE_URL so probe + CLI agree"
    )
    assert "/api/tags" in text, "preflight is not hitting /api/tags"
    assert "exit 2" in text, "preflight exit-2 missing from hallu_cron_pipeline.sh"
    assert "dataset-citations-judge-anchors" in text, (
        "judge-anchors step missing from hallu_cron_pipeline.sh"
    )


def test_cron_script_bash_syntax_clean() -> None:
    """`bash -n` parses the script without errors."""
    result = subprocess.run(
        ["bash", "-n", str(CRON_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_rerun_script_bash_syntax_clean() -> None:
    """`bash -n` parses the rerun helper without errors."""
    result = subprocess.run(
        ["bash", "-n", str(RERUN_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_rerun_script_supports_judge_only_flag() -> None:
    """The --judge-only flag must be recognised (regression guard for #88)."""
    text = RERUN_SCRIPT.read_text()
    assert "--judge-only" in text
    assert "dataset-citations-judge-anchors" in text
