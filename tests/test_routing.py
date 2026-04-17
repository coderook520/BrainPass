"""Path normalization + dispatch + _path_in_gated_set tests.

Covers §F2 (normalize_request_path), §G1 (glob-aware gate helper),
§F10/§G16 (dispatch contract).
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_routing import (
    normalize_request_path, register_get, register_post, dispatch,
    _reset_routes_for_tests,
)
from bp_gate.gate_mixin import _path_in_gated_set


class NormalizeTest(unittest.TestCase):
    def test_canonical_paths_pass_through(self):
        self.assertEqual(normalize_request_path("/recall"), "/recall")
        self.assertEqual(normalize_request_path("/health"), "/health")
        self.assertEqual(normalize_request_path("/write-queue"), "/write-queue")

    def test_query_stripped(self):
        self.assertEqual(normalize_request_path("/recall?x=1"), "/recall")
        self.assertEqual(normalize_request_path("/changed?since=2026"), "/changed")

    def test_fragment_stripped(self):
        self.assertEqual(normalize_request_path("/recall#abc"), "/recall")

    def test_params_stripped(self):
        self.assertEqual(normalize_request_path("/recall;sessionid=xyz"), "/recall")

    def test_traversal_rejected(self):
        self.assertIsNone(normalize_request_path("/../recall"))
        self.assertIsNone(normalize_request_path("/foo/../recall"))

    def test_double_slash_rejected(self):
        self.assertIsNone(normalize_request_path("//recall"))

    def test_trailing_slash_rejected(self):
        self.assertIsNone(normalize_request_path("/recall/"))

    def test_percent_encoded_rejected(self):
        # unquote once, then refuse if % still present (double-encode)
        self.assertIsNone(normalize_request_path("/recall%2520"))
        # single-encoded %20 decodes to space — not canonical
        self.assertIsNone(normalize_request_path("/recall%20"))

    def test_empty_rejected(self):
        self.assertIsNone(normalize_request_path(""))
        self.assertIsNone(normalize_request_path(None))  # type: ignore

    def test_relative_rejected(self):
        self.assertIsNone(normalize_request_path("recall"))

    def test_dot_segment_rejected(self):
        self.assertIsNone(normalize_request_path("/./recall"))


class PathInGatedSetTest(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(_path_in_gated_set("/recall", {"/recall"}))

    def test_no_match(self):
        self.assertFalse(_path_in_gated_set("/public", {"/recall"}))

    def test_empty_path_returns_false(self):
        self.assertFalse(_path_in_gated_set("", {"/recall"}))

    def test_single_star_matches_segment(self):
        self.assertTrue(_path_in_gated_set(
            "/write-queue/abc/approve",
            {"/write-queue/*/approve"},
        ))

    def test_single_star_does_not_cross_slash(self):
        self.assertFalse(_path_in_gated_set(
            "/write-queue/a/b/approve",
            {"/write-queue/*/approve"},
        ))

    def test_question_mark_glob(self):
        self.assertTrue(_path_in_gated_set("/v1", {"/v?"}))
        self.assertFalse(_path_in_gated_set("/v12", {"/v?"}))

    def test_accepts_set_and_frozenset(self):
        self.assertTrue(_path_in_gated_set("/recall", {"/recall"}))
        self.assertTrue(_path_in_gated_set("/recall", frozenset({"/recall"})))

    def test_exact_wins_over_glob(self):
        self.assertTrue(_path_in_gated_set("/foo", {"/foo", "/*"}))


class DispatchTest(unittest.TestCase):
    def setUp(self):
        _reset_routes_for_tests()

    def tearDown(self):
        _reset_routes_for_tests()

    def test_dispatch_matches_and_runs(self):
        calls = []
        def handler(h, *, params): calls.append(("get", params))
        register_get("/foo", handler)
        self.assertTrue(dispatch("GET", "/foo", self))
        self.assertEqual(calls, [("get", {})])

    def test_dispatch_captures_params(self):
        calls = []
        def handler(h, *, params): calls.append(params)
        register_post("/write-queue/{id}/approve", handler)
        self.assertTrue(dispatch("POST", "/write-queue/abc123/approve", self))
        self.assertEqual(calls, [{"id": "abc123"}])

    def test_dispatch_no_match_returns_false(self):
        self.assertFalse(dispatch("GET", "/nonsense", self))

    def test_dispatch_method_specific(self):
        def handler(h, *, params): pass
        register_get("/foo", handler)
        self.assertTrue(dispatch("GET", "/foo", self))
        self.assertFalse(dispatch("POST", "/foo", self))


if __name__ == "__main__":
    unittest.main()
