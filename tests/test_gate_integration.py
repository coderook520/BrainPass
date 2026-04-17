"""Regression test for Phase-4 P5 CRITICAL finding.

The gate's _path_in_gated_set only understands `*` and `?` glob vocab.
Using `{id}`-style named-capture syntax (which bp_routing.dispatch uses)
in the GATED set would silently leak endpoints.

These tests assert that the gate set entries in bp_writeback and any
other v3 module use the correct glob vocab, not named captures.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_gate.gate_mixin import _path_in_gated_set


class GateSetGlobTest(unittest.TestCase):
    def test_writeback_approve_path_gated(self):
        # The canonical gate entry for writeback approve must match a real
        # request path. If the entry used `{id}` it would be literal and fail.
        import bp_writeback
        g = set()
        gget = set()
        bp_writeback.register_endpoints(g, gget)
        self.assertTrue(
            _path_in_gated_set("/write-queue/abc123/approve", g),
            f"writeback approve endpoint NOT gated by any entry in {g}",
        )
        self.assertTrue(
            _path_in_gated_set("/write-queue/abc123/reject", g),
            f"writeback reject endpoint NOT gated by any entry in {g}",
        )

    def test_braces_do_not_match(self):
        # Sanity: bracket-style names NEVER match actual IDs (would be a bug)
        self.assertFalse(
            _path_in_gated_set("/write-queue/abc/approve",
                                {"/write-queue/{id}/approve"}),
            "_path_in_gated_set must NOT treat {id} as a wildcard — "
            "this would mask a gate-bypass bug",
        )

    def test_glob_star_matches_actual_id(self):
        self.assertTrue(
            _path_in_gated_set("/write-queue/abc/approve",
                                {"/write-queue/*/approve"})
        )

    def test_writeback_list_gated_as_exact(self):
        import bp_writeback
        g = set()
        gget = set()
        bp_writeback.register_endpoints(g, gget)
        self.assertTrue(_path_in_gated_set("/write-queue", gget))


if __name__ == "__main__":
    unittest.main()
