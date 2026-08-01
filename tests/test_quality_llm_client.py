"""Tests for `dataset_citations.quality.llm_client`.

No mocks. The client's HTTP path is overridden via a real subclass that
returns hand-built strings, matching the pattern used by
`tests/test_core_opencite_pipeline.py`.

Integration tests against a real Ollama daemon are gated behind
RUN_INTEGRATION_TESTS=1.
"""

from __future__ import annotations

import os
from unittest import TestCase, skipUnless

from dataset_citations.quality.llm_client import (
    ALLOWED_CLASSIFICATIONS,
    LlmJudgmentError,
    OllamaJudgmentClient,
    build_anchor_prompt,
)


class _FakeClient(OllamaJudgmentClient):
    """Real subclass that bypasses the HTTP step.

    `_generate` is the seam: the parent posts to /api/generate and returns
    the response string. Here we return whatever was preset on the instance.
    """

    def __init__(self, canned_response: str) -> None:
        # Skip parent __init__ so no httpx.Client is constructed.
        self.base_url = "http://test"
        self.model = "test-model"
        self.timeout = 5
        self._canned_response = canned_response

    def _generate(self, prompt: str) -> str:
        return self._canned_response


class BuildAnchorPromptTests(TestCase):
    def test_prompt_includes_taxonomy_and_dataset(self) -> None:
        prompt = build_anchor_prompt(
            dataset_id="ds005505",
            dataset_description="EEG recordings from HBN.",
            anchor_doi="10.1234/example",
            anchor_relation="IsDerivedFrom",
            paper_title="The Healthy Brain Network",
            paper_abstract="Multi-site initiative collecting brain data.",
            paper_venue="Scientific Data",
            paper_authors=[],
            paper_year=2017,
        )
        # Taxonomy labels appear verbatim so the model can pick from them.
        for label in ALLOWED_CLASSIFICATIONS:
            self.assertIn(label, prompt)
        self.assertIn("ds005505", prompt)
        self.assertIn("10.1234/example", prompt)
        self.assertIn("IsDerivedFrom", prompt)
        self.assertIn("EEG recordings from HBN", prompt)
        self.assertIn("Multi-site initiative", prompt)
        # JSON-only directive is critical for parsing.
        self.assertIn("strict JSON only", prompt)

    def test_prompt_distinguishes_journal_method_papers(self) -> None:
        # Issue #131: e4b misclassified analysis-method papers published as
        # journal articles (e.g. NeuroImage) as data_paper. The taxonomy
        # definition and a dedicated few-shot example must steer methodology.
        prompt = build_anchor_prompt(
            dataset_id="ds004362",
            dataset_description="EEG dataset.",
            anchor_doi="10.1016/j.neuroimage.2020.117465",
            anchor_relation="References",
            paper_title="An automated pipeline for EEG artifact rejection",
            paper_abstract="A general analysis method for EEG.",
        )
        self.assertIn("method/algorithm paper is methodology, NOT data_paper", prompt)
        self.assertIn("analysis-method paper in a journal", prompt)

    def test_prompt_handles_missing_abstract(self) -> None:
        prompt = build_anchor_prompt(
            dataset_id="ds000999",
            dataset_description="A test dataset.",
            anchor_doi="10.0000/none",
            anchor_relation="References",
            paper_title="Some Paper",
            paper_abstract=None,
            paper_venue=None,
            paper_authors=None,
            paper_year=None,
        )
        self.assertIn("[unavailable]", prompt)

    def test_prompt_truncates_long_dataset_description(self) -> None:
        long_text = "x" * 5000
        prompt = build_anchor_prompt(
            dataset_id="ds000999",
            dataset_description=long_text,
            anchor_doi="10.0000/none",
            anchor_relation="References",
            paper_title="t",
            paper_abstract="a",
        )
        # The literal 5000 x's must not appear; truncation marker should.
        self.assertNotIn("x" * 5000, prompt)
        self.assertIn("…", prompt)


class JudgeAnchorParseTests(TestCase):
    """Validate response parsing without touching the network."""

    def test_valid_response_parses(self) -> None:
        client = _FakeClient('{"classification": "data_paper", "reason": "ok"}')
        out = client.judge_anchor("prompt")
        self.assertEqual(out["classification"], "data_paper")
        self.assertEqual(out["reason"], "ok")
        self.assertEqual(out["model"], "test-model")
        self.assertIn("raw_response", out)

    def test_reason_is_stripped(self) -> None:
        client = _FakeClient(
            '{"classification": "methodology", "reason": "  trimmed  "}'
        )
        out = client.judge_anchor("prompt")
        self.assertEqual(out["reason"], "trimmed")

    def test_unknown_classification_raises(self) -> None:
        client = _FakeClient('{"classification": "nonsense", "reason": "bad label"}')
        with self.assertRaises(LlmJudgmentError) as ctx:
            client.judge_anchor("prompt")
        self.assertIn("not in taxonomy", str(ctx.exception))

    def test_missing_classification_raises(self) -> None:
        client = _FakeClient('{"reason": "no class field"}')
        with self.assertRaises(LlmJudgmentError):
            client.judge_anchor("prompt")

    def test_missing_reason_raises(self) -> None:
        client = _FakeClient('{"classification": "umbrella"}')
        with self.assertRaises(LlmJudgmentError):
            client.judge_anchor("prompt")

    def test_empty_reason_raises(self) -> None:
        client = _FakeClient('{"classification": "irrelevant", "reason": "   "}')
        with self.assertRaises(LlmJudgmentError):
            client.judge_anchor("prompt")

    def test_non_json_response_raises(self) -> None:
        client = _FakeClient("this is not json at all")
        with self.assertRaises(LlmJudgmentError) as ctx:
            client.judge_anchor("prompt")
        self.assertEqual(ctx.exception.raw_response, "this is not json at all")

    def test_json_array_root_raises(self) -> None:
        client = _FakeClient('["data_paper", "ok"]')
        with self.assertRaises(LlmJudgmentError):
            client.judge_anchor("prompt")


class EnvDefaultsTests(TestCase):
    """Verify env var overrides without touching the network."""

    def test_explicit_args_win(self) -> None:
        client = OllamaJudgmentClient(
            base_url="http://override:9999",
            model="custom-model",
            timeout=11,
        )
        try:
            self.assertEqual(client.base_url, "http://override:9999")
            self.assertEqual(client.model, "custom-model")
            self.assertEqual(client.timeout, 11)
        finally:
            client.close()

    def test_env_overrides(self) -> None:
        prior = {
            "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL"),
            "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL"),
            "OLLAMA_TIMEOUT_SECONDS": os.environ.get("OLLAMA_TIMEOUT_SECONDS"),
        }
        try:
            os.environ["OLLAMA_BASE_URL"] = "http://env-host:12345"
            os.environ["OLLAMA_MODEL"] = "env-model"
            os.environ["OLLAMA_TIMEOUT_SECONDS"] = "99"
            client = OllamaJudgmentClient()
            try:
                self.assertEqual(client.base_url, "http://env-host:12345")
                self.assertEqual(client.model, "env-model")
                self.assertEqual(client.timeout, 99)
            finally:
                client.close()
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


@skipUnless(
    os.getenv("RUN_INTEGRATION_TESTS"),
    "live ollama call; set RUN_INTEGRATION_TESTS=1 to enable",
)
class OllamaJudgmentClientIntegration(TestCase):
    """Live integration test against a running Ollama daemon.

    Set OLLAMA_BASE_URL to point at your daemon (defaults to hallu). The
    test asks the model to classify a fabricated MNE-Python anchor for a
    fictional dataset and asserts the response is valid + in taxonomy.
    """

    def test_methodology_anchor_round_trip(self) -> None:
        prompt = build_anchor_prompt(
            dataset_id="ds000117",
            dataset_description=(
                "Multi-subject MEG and EEG dataset for a face-perception "
                "experiment, BIDS-formatted."
            ),
            anchor_doi="10.3389/fnins.2013.00267",
            anchor_relation="IsDerivedFrom",
            paper_title="MEG and EEG data analysis with MNE-Python",
            paper_abstract=(
                "MNE-Python is an open-source software package for "
                "processing MEG and EEG data."
            ),
            paper_venue="Frontiers in Neuroscience",
            paper_year=2013,
        )
        with OllamaJudgmentClient() as client:
            if not client.health_check():
                self.skipTest("ollama daemon not reachable")
            result = client.judge_anchor(prompt)
        self.assertIn(result["classification"], ALLOWED_CLASSIFICATIONS)
        self.assertTrue(result["reason"])
