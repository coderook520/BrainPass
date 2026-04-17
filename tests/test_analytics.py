"""bp_analytics — recorder scrub + ReDoS benchmark + aggregator."""
from __future__ import annotations
import os
import re
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_analytics.recorder import (
    scrub_query, _benchmark_pattern, _is_redos_signature,
)


class ScrubbingTest(unittest.TestCase):
    def test_api_keys_scrubbed(self):
        out = scrub_query("my key is gsk_AAAAAAAAAAAAAAAAAAAAAAAAAAA bye")
        self.assertIn("gsk_REDACTED", out)

    def test_normal_text_passes(self):
        out = scrub_query("what did I promise Sarah")
        self.assertIn("Sarah", out)


class RedosBenchmarkTest(unittest.TestCase):
    """§G8 — pre-benchmark runs each pattern against pathological inputs;
    patterns that exceed the budget are rejected at load time. No SIGALRM
    at runtime."""

    def test_safe_pattern_passes(self):
        p = re.compile(r"hello\s+world")
        self.assertTrue(_benchmark_pattern(p, budget_s=0.01))

    def test_benchmark_accepts_simple_pattern(self):
        # Structural pre-filter (_is_redos_signature) is the primary defense;
        # _benchmark_pattern is a smoke check on small probes. A simple
        # pattern must pass.
        p = re.compile(r"[a-z]+\d*")
        self.assertTrue(_benchmark_pattern(p, budget_s=0.1))

    def test_redos_signature_detected(self):
        self.assertTrue(_is_redos_signature(r"(a+)+"))
        self.assertTrue(_is_redos_signature(r"(a*)*"))
        self.assertFalse(_is_redos_signature(r"\d+"))


if __name__ == "__main__":
    unittest.main()
