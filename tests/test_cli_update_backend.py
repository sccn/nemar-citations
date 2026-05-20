"""Tests for `dataset-citations-update` (opencite-only after Phase 4).

Uses monkeypatch (stdlib setattr) to substitute one real function for another,
matching the project's "no Mock objects" rule.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase

from dataset_citations.cli import update as cli_update


def _make_args(
    list_file: Path,
    out_dir: str,
    *,
    catalog_doi_map: dict[str, str] | None = None,
) -> argparse.Namespace:
    """Build the argparse.Namespace `run_opencite_backend` expects.

    Writes an empty catalog cache so `_load_catalog_doi_map` returns an
    empty map without hitting the network. Pass `catalog_doi_map` to
    inject a non-empty mapping for tests that exercise catalog-DOI
    seeding.
    """
    cache_path = Path(out_dir) / "catalog.json"
    if catalog_doi_map:
        rows = [
            {
                "dataset_id": did,
                "doi": doi,
                "concept_doi": doi,
                "source": "openneuro" if did.startswith(("ds", "on")) else "nemar",
                "source_id": None,
                "github_repo": f"nemarDatasets/{did}",
                "modalities": "eeg",
                "name": None,
                "visibility": "public",
            }
            for did, doi in catalog_doi_map.items()
        ]
        cache_path.write_text(json.dumps(rows))
    else:
        cache_path.write_text("[]")
    return argparse.Namespace(
        dataset_list_file=str(list_file),
        output_dir=out_dir,
        catalog_cache=cache_path,
        catalog_cache_max_age=3600,
        max_age_days=0,
    )


class CliParserTests(TestCase):
    def test_real_help_text_documents_opencite_pipeline(self) -> None:
        """The CLI is now single-path; help text must describe the opencite
        pipeline and accept --dataset-list-file. The legacy --backend flag
        must NOT be present (Phase 4 retired scholarly)."""
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["dataset-citations-update", "--help"]
        try:
            with self.assertRaises(SystemExit), redirect_stdout(buf):
                cli_update.main()
        finally:
            sys.argv = old_argv
        help_text = buf.getvalue()
        self.assertIn("--dataset-list-file", help_text)
        self.assertIn("opencite", help_text)
        self.assertNotIn("--backend", help_text)
        self.assertNotIn("scholarly", help_text)

    def test_main_invokes_run_opencite_backend(self) -> None:
        """main() always calls run_opencite_backend; no backend dispatch."""
        with tempfile.TemporaryDirectory() as tmp:
            list_file = Path(tmp) / "list.txt"
            list_file.write_text("ds999999\n")

            captured: dict[str, object] = {}

            def recording_run_opencite(args):
                captured["called"] = True
                captured["dataset_list_file"] = args.dataset_list_file
                captured["output_dir"] = args.output_dir

            original = cli_update.run_opencite_backend
            cli_update.run_opencite_backend = recording_run_opencite  # type: ignore[assignment]
            old_argv = sys.argv
            sys.argv = [
                "dataset-citations-update",
                "--dataset-list-file",
                str(list_file),
                "--output-dir",
                tmp,
            ]
            try:
                cli_update.main()
            finally:
                cli_update.run_opencite_backend = original  # type: ignore[assignment]
                sys.argv = old_argv

            self.assertTrue(captured.get("called"))
            self.assertEqual(captured.get("output_dir"), tmp)
            self.assertEqual(captured.get("dataset_list_file"), str(list_file))


class RunOpenciteBackendTests(TestCase):
    """Direct tests for run_opencite_backend's write/dispatch behavior."""

    def test_unsupported_prefix_still_writes_stub(self) -> None:
        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("xx123\n")
            args = _make_args(list_file, out_dir)
            cli_update.run_opencite_backend(args)
            stub = Path(out_dir) / "json_opencite" / "xx123_citations.json"
            self.assertTrue(stub.exists())
            payload = json.loads(stub.read_text())
            self.assertEqual(payload["num_citations"], 0)
            self.assertIn("unsupported_prefix", payload["metadata"]["fetch_status"])
            self.assertFalse((Path(out_dir) / "json").exists())

    def test_all_api_failures_raises_systemexit_3(self) -> None:
        """When every dataset stubs out with an API-failure status (and no
        write succeeded), exit 3 so cron / CI catches the degraded run.

        Phase 4 review finding: a fully-rate-limited run would otherwise
        proceed silently and downstream steps would regenerate empty CSVs.
        Substitute the pipeline call with a recording function via setattr.
        """
        from dataset_citations.cli import update as cli_module

        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("ds111111\nds222222\n")

            def stub_pipeline(dataset_id, **_):
                return {
                    "dataset_id": dataset_id,
                    "num_citations": 0,
                    "date_last_updated": "2026-01-01T00:00:00",
                    "metadata": {
                        "schema_version": "2.0",
                        "discovery_backend": "opencite",
                        "fetch_status": "rate_limit",
                    },
                    "citation_details": [],
                }

            original = cli_module.fetch_dataset_citations_via_opencite
            cli_module.fetch_dataset_citations_via_opencite = stub_pipeline  # type: ignore[assignment]
            args = _make_args(list_file, out_dir)
            try:
                with self.assertRaises(SystemExit) as ctx:
                    cli_update.run_opencite_backend(args)
                self.assertEqual(ctx.exception.code, 3)
            finally:
                cli_module.fetch_dataset_citations_via_opencite = original  # type: ignore[assignment]

    def test_no_doi_references_does_not_exit_nonzero(self) -> None:
        """A run where every dataset legitimately has no DOI references
        should NOT exit non-zero; that's a normal outcome (e.g., new nm
        datasets without metadata.json yet)."""
        from dataset_citations.cli import update as cli_module

        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("nm999999\n")

            def stub_pipeline(dataset_id, **_):
                return {
                    "dataset_id": dataset_id,
                    "num_citations": 0,
                    "date_last_updated": "2026-01-01T00:00:00",
                    "metadata": {
                        "schema_version": "2.0",
                        "discovery_backend": "opencite",
                        "fetch_status": "no_doi_references",
                    },
                    "citation_details": [],
                }

            original = cli_module.fetch_dataset_citations_via_opencite
            cli_module.fetch_dataset_citations_via_opencite = stub_pipeline  # type: ignore[assignment]
            args = _make_args(list_file, out_dir)
            try:
                # Should return normally, no SystemExit.
                cli_update.run_opencite_backend(args)
            finally:
                cli_module.fetch_dataset_citations_via_opencite = original  # type: ignore[assignment]

    def test_total_write_failure_raises_systemexit(self) -> None:
        """When every write fails, surface non-zero exit.

        Force-fail writes by making the json_opencite output directory
        read-only after run_opencite_backend creates it. We re-enter the
        function with the directory already in place but non-writable.
        """
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
            args = _make_args(list_file, out_dir)
            try:
                with self.assertRaises(SystemExit) as ctx:
                    cli_update.run_opencite_backend(args)
                self.assertEqual(ctx.exception.code, 2)
            finally:
                # Restore write perm so tempfile cleanup works.
                os.chmod(json_dir, stat.S_IRWXU)


class IsFreshSuccessTests(TestCase):
    """Direct tests for the `_is_fresh_success` helper. Pure file reader,
    no network, real JSON fixtures on disk — no stubs of any kind.
    """

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))

    def test_returns_false_when_missing(self) -> None:
        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(
                _is_fresh_success(str(Path(tmp) / "absent.json"), 7 * 86400)
            )

    def test_returns_true_for_fresh_success(self) -> None:
        from datetime import datetime, timezone

        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nm000104_citations.json"
            self._write_json(
                path,
                {
                    "dataset_id": "nm000104",
                    "num_citations": 5,
                    "date_last_updated": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"fetch_status": "success"},
                },
            )
            self.assertTrue(_is_fresh_success(str(path), 7 * 86400))

    def test_returns_false_for_stale_success(self) -> None:
        from datetime import datetime, timedelta, timezone

        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nm000104_citations.json"
            stale = datetime.now(timezone.utc) - timedelta(days=30)
            self._write_json(
                path,
                {
                    "dataset_id": "nm000104",
                    "date_last_updated": stale.isoformat(),
                    "metadata": {"fetch_status": "success"},
                },
            )
            self.assertFalse(_is_fresh_success(str(path), 7 * 86400))

    def test_returns_false_for_non_success_status(self) -> None:
        from datetime import datetime, timezone

        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nm000104_citations.json"
            self._write_json(
                path,
                {
                    "dataset_id": "nm000104",
                    "date_last_updated": datetime.now(timezone.utc).isoformat(),
                    # Fresh but not a success: prior run hit rate_limit.
                    "metadata": {"fetch_status": "rate_limit"},
                },
            )
            self.assertFalse(_is_fresh_success(str(path), 7 * 86400))

    def test_returns_false_for_malformed_json(self) -> None:
        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("not json at all")
            self.assertFalse(_is_fresh_success(str(path), 7 * 86400))

    def test_returns_false_for_missing_metadata(self) -> None:
        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "headerless.json"
            self._write_json(path, {"dataset_id": "x", "num_citations": 0})
            self.assertFalse(_is_fresh_success(str(path), 7 * 86400))

    def test_returns_false_for_unparseable_timestamp(self) -> None:
        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad_date.json"
            self._write_json(
                path,
                {
                    "date_last_updated": "not-a-real-iso-string",
                    "metadata": {"fetch_status": "success"},
                },
            )
            self.assertFalse(_is_fresh_success(str(path), 7 * 86400))

    def test_treats_naive_timestamp_as_utc(self) -> None:
        from datetime import datetime, timezone

        from dataset_citations.cli.update import _is_fresh_success

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "naive.json"
            naive_now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            self._write_json(
                path,
                {
                    "date_last_updated": naive_now,
                    "metadata": {"fetch_status": "success"},
                },
            )
            self.assertTrue(_is_fresh_success(str(path), 7 * 86400))


class CatalogDoiWiringTests(TestCase):
    """run_opencite_backend forwards catalog_doi + use_checkpoint=True to
    the pipeline. Substitutes the pipeline call to record arguments."""

    def test_catalog_doi_and_checkpoint_forwarded(self) -> None:
        from dataset_citations.cli import update as cli_module

        with tempfile.TemporaryDirectory() as out_dir:
            list_file = Path(out_dir) / "list.txt"
            list_file.write_text("nm000104\nnm000999\n")

            captured: list[dict] = []

            def stub_pipeline(dataset_id, **kwargs):
                captured.append({"dataset_id": dataset_id, **kwargs})
                return {
                    "dataset_id": dataset_id,
                    "num_citations": 0,
                    "date_last_updated": "2026-01-01T00:00:00",
                    "metadata": {
                        "schema_version": "2.0",
                        "discovery_backend": "opencite",
                        "fetch_status": "no_doi_references",
                    },
                    "citation_details": [],
                }

            original = cli_module.fetch_dataset_citations_via_opencite
            cli_module.fetch_dataset_citations_via_opencite = stub_pipeline  # type: ignore[assignment]
            args = _make_args(
                list_file,
                out_dir,
                catalog_doi_map={"nm000104": "10.82901/nemar.nm000104"},
            )
            try:
                cli_update.run_opencite_backend(args)
            finally:
                cli_module.fetch_dataset_citations_via_opencite = original  # type: ignore[assignment]

            self.assertEqual(len(captured), 2)
            # nm000104 was in the catalog -> catalog_doi forwarded.
            self.assertEqual(captured[0]["catalog_doi"], "10.82901/nemar.nm000104")
            # nm000999 was NOT in the catalog -> catalog_doi=None.
            self.assertIsNone(captured[1]["catalog_doi"])
            # Both calls opt in to checkpoint resume.
            self.assertTrue(captured[0]["use_checkpoint"])
            self.assertTrue(captured[1]["use_checkpoint"])
