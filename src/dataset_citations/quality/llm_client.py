#!/usr/bin/env python3
"""
Ollama-backed LLM client for anchor adjudication.

Epic #76 fixes citation inflation by asking a local LLM (the largest local
Gemma checkpoint served by Ollama on the hallu RTX 4090; see _DEFAULT_MODEL)
to classify each DOI anchor in a dataset's metadata as one of five buckets.
Phase 1 (#85) stands up the client + the prompt + a throwaway probe script;
phase 2 (#86) productizes the storage.

This module is the single place where the prompt + classification taxonomy
live. Phases 2, 3, and 4 all import from here so a prompt revision is a
single-file change, not a sweep.

The classification schema is:

  - data_paper:    the paper IS the data paper for this dataset (or the
                   dataset's preprint / curation paper).
  - umbrella:      the paper is a multi-dataset / multi-study initiative
                   (HBN, UK Biobank, ABCD) that contains this dataset but
                   is not its data paper.
  - methodology:   the paper is a software / method / analysis tool the
                   dataset's protocol uses (MNE-Python, BIDS-EEG spec).
  - related_work:  the paper is topically related but does not describe
                   this dataset specifically.
  - irrelevant:    the paper has no meaningful relationship to this
                   dataset (mis-attached anchor, token collision, etc.).

Copyright (c) 2026 Seyed Yahya Shirazi (neuromechanist)
All rights reserved.

Author: Seyed Yahya Shirazi
GitHub: https://github.com/neuromechanist
Email: shirazi@ieee.org
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable

import httpx

logger = logging.getLogger(__name__)

# The five-class taxonomy is the contract phase 2's sidecar schema and
# phase 3's pipeline filter both depend on. Adding or removing a class is a
# cross-phase change; doc the rationale before edits.
ALLOWED_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"data_paper", "umbrella", "methodology", "related_work", "irrelevant"}
)

# Env vars + defaults. The default base URL is localhost so the production
# cron path (which runs on hallu next to the Ollama daemon) needs no
# overrides. Developer workstations reach the daemon either by ssh-ing
# directly to hallu and running there, OR by forwarding a *non-default*
# local port (e.g. `ssh -fN -L 21434:localhost:11434 hallu`) and setting
# OLLAMA_BASE_URL=http://localhost:21434. Using 11434 for the tunnel
# collides with a workstation-local `ollama serve` and silently routes
# the request to the wrong daemon. See scripts/probe_anchor_judgment.py
# docstring for the canonical workflow.
# Default model tracks the largest Gemma checkpoint currently pulled on
# hallu; epic #76 spec'd Gemma 3 27B, but the live deployment is the
# next-generation model. Update the constant when the pulled model
# changes.
_ENV_BASE_URL = "OLLAMA_BASE_URL"
_ENV_MODEL = "OLLAMA_MODEL"
_ENV_TIMEOUT = "OLLAMA_TIMEOUT_SECONDS"

_DEFAULT_BASE_URL = "http://localhost:11434"
# Single source of truth for the deployed model. Bump this one constant
# (and re-run the probe) when a new checkpoint is pulled on hallu. 31B
# is the smallest checkpoint that handles the methodology-vs-data_paper
# discrimination correctly on the acceptance-gate probe; 26B confused a
# Brainstorm-tools anchor for a data paper.
_DEFAULT_MODEL = "gemma4:31b"
# Per-judgment timeout: most calls return in 3-10s, but cold loads + long
# prompts on the 26B checkpoint have been observed at ~150s. 300s gives
# headroom without hanging the probe forever on a stuck request.
_DEFAULT_TIMEOUT = 300

# Truncate long dataset descriptions to keep the prompt under the model's
# practical context budget while leaving room for the candidate paper. The
# probe script's hand-picked datasets all fit comfortably under this.
_DATASET_DESCRIPTION_CHAR_LIMIT = 1500
_ABSTRACT_CHAR_LIMIT = 2000


class LlmJudgmentError(RuntimeError):
    """Raised when the LLM returns malformed JSON or an out-of-taxonomy label.

    The probe and the phase 2 CLI catch this so a single bad anchor doesn't
    abort a batch run. The detail string carries the raw response for
    auditing.
    """

    def __init__(self, message: str, *, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return "[unavailable]"
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _format_authors(authors: Iterable[Any]) -> str:
    """Render a small authors list for the prompt. Trims at 5 names."""
    names: list[str] = []
    for author in authors:
        name = getattr(author, "name", None) or str(author)
        if name:
            names.append(name)
        if len(names) >= 5:
            names.append("et al.")
            break
    return ", ".join(names) if names else "[unavailable]"


def build_anchor_prompt(
    *,
    dataset_id: str,
    dataset_description: str | None,
    anchor_doi: str,
    anchor_relation: str,
    paper_title: str | None,
    paper_abstract: str | None,
    paper_venue: str | None = None,
    paper_authors: Iterable[Any] | None = None,
    paper_year: int | None = None,
) -> str:
    """Return the full Ollama prompt for one (dataset, anchor) judgment.

    Kept as a module-level pure function so phases 2/3/4 all build identical
    prompts. The opening lays out the taxonomy with one-line definitions,
    then hands the model the dataset description + candidate paper + the
    DataCite `source_relation` value, then three few-shot examples covering
    the acceptance-gate cases from epic #76 (HBN umbrella, dataset preprint,
    MNE-Python methodology).
    """
    description = _truncate(dataset_description, _DATASET_DESCRIPTION_CHAR_LIMIT)
    abstract = _truncate(paper_abstract, _ABSTRACT_CHAR_LIMIT)
    title = paper_title or "[unavailable]"
    venue = paper_venue or "[unavailable]"
    authors = _format_authors(paper_authors or [])
    year = str(paper_year) if paper_year else "[unavailable]"

    return f"""You are classifying the relationship between a neuroscience dataset and a candidate paper that the dataset's metadata cites as a related identifier.

Choose exactly one class from this taxonomy:

- data_paper: the paper IS this dataset's data paper, dataset preprint, or curation paper. It introduces, describes, or releases the data in this specific dataset.
- umbrella: the paper is a multi-dataset / multi-study initiative (e.g. HBN, UK Biobank, ABCD) that this dataset belongs to, but the paper is NOT this specific dataset's data paper.
- methodology: the paper is a software tool, analysis method, or technical specification that this dataset's protocol uses (e.g. MNE-Python, EEGLAB, BIDS-EEG spec, FieldTrip).
- related_work: the paper is topically related (same brain region, task, modality) but does not describe this dataset specifically.
- irrelevant: the paper has no meaningful relationship to this dataset (mis-attached anchor, token-collision false positive).

Respond with strict JSON only, no prose, no markdown:
{{"classification": "<one of the five labels>", "reason": "<one sentence, <= 200 chars, citing concrete evidence from the title or abstract>"}}

=== DATASET ===
dataset_id: {dataset_id}
description (truncated):
{description}

=== CANDIDATE PAPER ===
DOI: {anchor_doi}
source_relation (DataCite, may be hint but is NOT ground truth): {anchor_relation}
title: {title}
authors: {authors}
venue: {venue}
year: {year}
abstract:
{abstract}

=== EXAMPLES ===
Example 1 (HBN umbrella):
  dataset_id: ds004186 (one of many HBN sibling releases)
  candidate paper: "The Healthy Brain Network Serial Scanning Initiative: a resource for evaluating inter-individual differences and their reliabilities across scan conditions and sessions"
  Correct output: {{"classification": "umbrella", "reason": "Paper describes the broader Healthy Brain Network initiative containing many sibling datasets, not this specific release."}}

Example 2 (dataset preprint as data paper):
  dataset_id: ds002718
  candidate paper: "An open dataset of EEG recordings from face perception experiments"
  Correct output: {{"classification": "data_paper", "reason": "Title and abstract describe the release of this specific EEG face-perception dataset."}}

Example 3 (methodology tool):
  dataset_id: ds000117 (anchor DOI 10.3389/fnins.2013.00267)
  candidate paper: "MEG and EEG data analysis with MNE-Python"
  Correct output: {{"classification": "methodology", "reason": "Describes the MNE-Python analysis library; tool used in the protocol, not a paper about this dataset."}}

Now classify the candidate paper for dataset {dataset_id}. Respond with the JSON object only."""


class OllamaJudgmentClient:
    """Sync HTTP client for Ollama's `/api/generate` JSON-mode endpoint.

    One client per process is fine; httpx.Client handles connection pooling.
    Phase 4's cron preflight uses `health_check()` to fail fast if the GPU
    host is unreachable.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get(_ENV_BASE_URL) or _DEFAULT_BASE_URL
        ).rstrip("/")
        self.model = model or os.environ.get(_ENV_MODEL) or _DEFAULT_MODEL
        timeout_env = os.environ.get(_ENV_TIMEOUT)
        if timeout is not None:
            self.timeout = timeout
        elif timeout_env:
            self.timeout = int(timeout_env)
        else:
            self.timeout = _DEFAULT_TIMEOUT
        self._client = httpx.Client(timeout=self.timeout)
        logger.debug(
            "OllamaJudgmentClient ready (base_url=%s, model=%s, timeout=%ds)",
            self.base_url,
            self.model,
            self.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OllamaJudgmentClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        del exc_type, exc_val, exc_tb
        self.close()

    def health_check(self) -> bool:
        """Return True iff the Ollama daemon answers `/api/tags`.

        Used by phase 4's cron preflight so a down GPU host aborts the run
        cleanly instead of writing empty judgments.
        """
        try:
            resp = self._post_health()
        except httpx.HTTPError as exc:
            logger.warning("ollama health_check failed: %s", exc)
            return False
        return resp.status_code == 200

    def _post_health(self) -> httpx.Response:
        return self._client.get(f"{self.base_url}/api/tags", timeout=5)

    def judge_anchor(self, prompt: str) -> dict[str, Any]:
        """Send `prompt` to Ollama, parse the JSON response, validate.

        Returns a dict with keys:
          - classification (str, one of ALLOWED_CLASSIFICATIONS)
          - reason (str, non-empty)
          - raw_response (str, the model's verbatim output)
          - model (str)

        Raises LlmJudgmentError if the response is not parseable JSON, is
        missing required keys, or has an out-of-taxonomy classification.
        """
        raw = self._generate(prompt)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LlmJudgmentError(
                f"ollama returned non-JSON content: {exc}",
                raw_response=raw,
            ) from exc

        if not isinstance(parsed, dict):
            raise LlmJudgmentError(
                f"ollama JSON root is not an object (got {type(parsed).__name__})",
                raw_response=raw,
            )

        classification = parsed.get("classification")
        reason = parsed.get("reason")

        if not isinstance(classification, str):
            raise LlmJudgmentError(
                "missing or non-string 'classification' field",
                raw_response=raw,
            )
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise LlmJudgmentError(
                f"classification {classification!r} not in taxonomy "
                f"{sorted(ALLOWED_CLASSIFICATIONS)}",
                raw_response=raw,
            )
        if not isinstance(reason, str) or not reason.strip():
            raise LlmJudgmentError(
                "missing or empty 'reason' field",
                raw_response=raw,
            )

        return {
            "classification": classification,
            "reason": reason.strip(),
            "raw_response": raw,
            "model": self.model,
        }

    def _generate(self, prompt: str) -> str:
        """POST `/api/generate` with format=json, return the `response` field.

        Split out so tests can subclass the client and override the HTTP step
        with a hand-built response (matches the no-mocks pattern used by
        `tests/test_core_opencite_pipeline.py`).

        All httpx-level failures (timeout, connect, non-2xx) are wrapped in
        `LlmJudgmentError` so the caller's per-anchor try/except catches them
        uniformly and one slow / failed anchor doesn't abort a batch run.
        Ollama's error JSON (when present) is surfaced in the message so the
        operator sees, e.g., "model not found" instead of a generic 500.
        """
        try:
            resp = self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as exc:
            body_error = self._extract_ollama_error(exc.response)
            raise LlmJudgmentError(
                f"ollama HTTP {exc.response.status_code}"
                + (f": {body_error}" if body_error else ""),
                raw_response=exc.response.text,
            ) from exc
        except httpx.HTTPError as exc:
            raise LlmJudgmentError(
                f"ollama HTTP transport error ({type(exc).__name__}): {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise LlmJudgmentError(
                f"ollama payload is not a JSON object: {type(payload).__name__}"
            )
        upstream_err = payload.get("error")
        if upstream_err:
            raise LlmJudgmentError(f"ollama returned error: {upstream_err!r}")
        response_text = payload.get("response")
        if not isinstance(response_text, str):
            raise LlmJudgmentError(
                f"ollama payload missing 'response' string field: {payload!r}"
            )
        return response_text

    @staticmethod
    def _extract_ollama_error(response: httpx.Response) -> str | None:
        """Return Ollama's `error` field from a non-2xx response body, if any.

        Ollama serves JSON error bodies like `{"error": "model 'foo' not
        found, try pulling it first"}` for many failure modes. Surface that
        string in `LlmJudgmentError` so the operator's debug loop is one
        step shorter.
        """
        try:
            body = response.json()
        except ValueError:
            return None
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, str) and err:
                return err
        return None
