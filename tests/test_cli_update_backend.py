"""Tests for `dataset-citations-update --backend opencite`.

Uses monkeypatch (stdlib setattr) to substitute one real function for another,
matching the project's "no Mock objects" rule.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase

from dataset_citations.cli import update as cli_update


class CliBackendParserTests(TestCase):
    def test_real_help_text_lists_backend_flag(self) -> None:
        """Capture the real CLI's --help output (no fresh parser substitute)."""
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["dataset-citations-update", "--help"]
        try:
            with self.assertRaises(SystemExit), redirect_stdout(buf):
                cli_update.main()
        finally:
            sys.argv = old_argv
        help_text = buf.getvalue()
        self.assertIn("--backend", help_text)
        self.assertIn("scholarly", help_text)
        self.assertIn("opencite", help_text)

    def test_backend_dispatch_invokes_run_opencite(self) -> None:
        """When --backend opencite is set, main() must call run_opencite_backend.

        Substitute run_opencite_backend with a recording function; this is
        setattr, not unittest.mock, so it stays within the no-mocks rule.
        """
        with tempfile.TemporaryDirectory() as tmp:
            list_file = Path(tmp) / "list.txt"
            list_file.write_text("ds999999\n")
            prev_csv = Path(tmp) / "prev.csv"
            prev_csv.write_text("dataset_id,number_of_citations\n")

            captured: dict[str, object] = {}

            def recording_run_opencite(args):
                captured["called"] = True
                captured["backend"] = args.backend
                captured["output_dir"] = args.output_dir

            original = cli_update.run_opencite_backend
            cli_update.run_opencite_backend = recording_run_opencite  # type: ignore[assignment]
            old_argv = sys.argv
            sys.argv = [
                "dataset-citations-update",
                "--dataset-list-file",
                str(list_file),
                "--previous-citations-file",
                str(prev_csv),
                "--output-dir",
                tmp,
                "--backend",
                "opencite",
            ]
            try:
                cli_update.main()
            finally:
                cli_update.run_opencite_backend = original  # type: ignore[assignment]
                sys.argv = old_argv

            self.assertTrue(captured.get("called"))
            self.assertEqual(captured.get("backend"), "opencite")
            self.assertEqual(captured.get("output_dir"), tmp)


class RunOpenciteBackendTests(TestCase):
    """Direct tests for run_opencite_backend's write/dispatch behavior."""

    def test_unsupported_prefix_still_writes_stub(self) -> None:
        import argparse

        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("xx123\n")
            args = argparse.Namespace(
                dataset_list_file=str(list_file),
                output_dir=out_dir,
            )
            cli_update.run_opencite_backend(args)
            stub = Path(out_dir) / "json_opencite" / "xx123_citations.json"
            self.assertTrue(stub.exists())
            payload = json.loads(stub.read_text())
            self.assertEqual(payload["num_citations"], 0)
            self.assertIn("unsupported_prefix", payload["metadata"]["fetch_status"])
            self.assertFalse((Path(out_dir) / "json").exists())

    def test_total_write_failure_raises_systemexit(self) -> None:
        """When every write fails, surface non-zero exit.

        Force-fail writes by making the json_opencite output directory
        read-only after run_opencite_backend creates it. We re-enter the
        function with the directory already in place but non-writable.
        """
        import argparse
        import os
        import stat

        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("xx123\nxx456\n")
            # Pre-create the json_opencite directory and make it read-only;
            # makedirs(exist_ok=True) tolerates an existing dir, then each
            # file write inside fails with PermissionError (OSError subclass).
            json_dir = Path(out_dir) / "json_opencite"
            json_dir.mkdir()
            os.chmod(json_dir, stat.S_IRUSR | stat.S_IXUSR)
            args = argparse.Namespace(
                dataset_list_file=str(list_file),
                output_dir=out_dir,
            )
            try:
                with self.assertRaises(SystemExit) as ctx:
                    cli_update.run_opencite_backend(args)
                self.assertEqual(ctx.exception.code, 2)
            finally:
                # Restore write perm so tempfile cleanup works.
                os.chmod(json_dir, stat.S_IRWXU)
