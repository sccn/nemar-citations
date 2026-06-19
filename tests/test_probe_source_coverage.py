"""Unit tests for the per-source coverage probe's set arithmetic.

`summarize_source_sets` is a pure function over real Python sets (no network,
no mocks). These tests pin the unique/overlap/union math the probe report and
its prose summary rely on.
"""

from __future__ import annotations

import os
import sys
from unittest import TestCase

# The probe lives in scripts/, which is not an installed package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from probe_source_coverage import summarize_source_sets  # noqa: E402


class TestSummarizeSourceSets(TestCase):
    def test_three_sources_unique_and_overlap(self) -> None:
        # openalex={a,b,c,d}, s2={c,d,e}, pubmed={d,f}
        result = summarize_source_sets(
            {
                "openalex": {"a", "b", "c", "d"},
                "s2": {"c", "d", "e"},
                "pubmed": {"d", "f"},
            }
        )
        self.assertEqual(result["union"], 6)  # {a,b,c,d,e,f}
        self.assertEqual(result["per_source"]["openalex"]["count"], 4)
        self.assertEqual(result["per_source"]["openalex"]["unique"], 2)  # a,b
        self.assertEqual(result["per_source"]["s2"]["unique"], 1)  # e
        self.assertEqual(result["per_source"]["pubmed"]["unique"], 1)  # f
        # sources are sorted: openalex, pubmed, s2
        self.assertEqual(result["pairwise_overlap"]["openalex&s2"], 2)  # c,d
        self.assertEqual(result["pairwise_overlap"]["openalex&pubmed"], 1)  # d
        self.assertEqual(result["pairwise_overlap"]["pubmed&s2"], 1)  # d
        self.assertEqual(result["all_source_overlap"], 1)  # d

    def test_single_source_unique_equals_count(self) -> None:
        result = summarize_source_sets({"openalex": {"a", "b", "c"}})
        self.assertEqual(result["union"], 3)
        self.assertEqual(result["per_source"]["openalex"]["count"], 3)
        self.assertEqual(result["per_source"]["openalex"]["unique"], 3)
        self.assertEqual(result["pairwise_overlap"], {})
        self.assertEqual(result["all_source_overlap"], 3)

    def test_all_empty_sets(self) -> None:
        result = summarize_source_sets({"openalex": set(), "s2": set()})
        self.assertEqual(result["union"], 0)
        self.assertEqual(result["per_source"]["openalex"]["unique"], 0)
        self.assertEqual(result["per_source"]["s2"]["unique"], 0)
        self.assertEqual(result["all_source_overlap"], 0)

    def test_uniques_plus_shared_reconcile_to_union(self) -> None:
        source_dois = {
            "openalex": {"a", "b", "c", "d"},
            "s2": {"c", "d", "e"},
            "pubmed": {"d", "f"},
        }
        result = summarize_source_sets(source_dois)
        total_unique = sum(v["unique"] for v in result["per_source"].values())
        shared = result["union"] - total_unique
        # 6 union = 4 unique (a,b,e,f) + 2 shared-by->=2-sources (c,d)
        self.assertEqual(total_unique, 4)
        self.assertEqual(shared, 2)
