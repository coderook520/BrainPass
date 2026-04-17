"""bp_temporal — decay math + changed walker."""
from __future__ import annotations
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_temporal.decay import decay_score, apply_decay
from bp_temporal import changed as temporal_changed


class DecayMathTest(unittest.TestCase):
    def test_age_zero_equals_one(self):
        now = time.time()
        self.assertAlmostEqual(decay_score(now, now, 30), 1.0, places=5)

    def test_half_life_equals_half(self):
        now = time.time()
        earlier = now - 30 * 86400
        self.assertAlmostEqual(decay_score(earlier, now, 30), 0.5, places=4)

    def test_two_half_lives_equals_quarter(self):
        now = time.time()
        earlier = now - 60 * 86400
        self.assertAlmostEqual(decay_score(earlier, now, 30), 0.25, places=4)

    def test_future_mtime_capped_at_one(self):
        # Age is clamped to >=0, so future files don't go above 1.0
        now = time.time()
        future = now + 86400
        self.assertAlmostEqual(decay_score(future, now, 30), 1.0, places=5)

    def test_apply_decay_reranks(self):
        now = time.time()
        mtimes = {"old.md": now - 60 * 86400, "new.md": now}
        ranked = [("old.md", 1.0), ("new.md", 0.5)]  # old scores higher by RRF
        result = apply_decay(
            ranked, mtime_lookup=lambda p: mtimes[p],
            half_life_days=30, now_unix=now,
        )
        # After decay: old = 1.0 * 0.25 = 0.25; new = 0.5 * 1.0 = 0.5
        self.assertEqual(result[0][0], "new.md")


class ChangedWalkerTest(unittest.TestCase):
    def test_walker_handles_missing_vault(self):
        original = os.environ.get("VAULT_PATH")
        os.environ["VAULT_PATH"] = "/nonexistent/path/for/test"
        try:
            self.assertEqual(temporal_changed.walk_changed(0), [])
        finally:
            if original is None:
                del os.environ["VAULT_PATH"]
            else:
                os.environ["VAULT_PATH"] = original

    def test_walker_returns_recent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create two files
            os.makedirs(os.path.join(tmp, "daily"))
            p = os.path.join(tmp, "daily", "recent.md")
            with open(p, "w") as f:
                f.write("# recent note\ncontent")
            os.environ["VAULT_PATH"] = tmp
            try:
                out = temporal_changed.walk_changed(0)
                self.assertEqual(len(out), 1)
                self.assertEqual(out[0]["path"], "daily/recent.md")
            finally:
                del os.environ["VAULT_PATH"]

    def test_walker_filters_by_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "old.md")
            with open(p, "w") as f:
                f.write("old")
            # Set mtime to 10 days ago
            ten_days_ago = time.time() - 10 * 86400
            os.utime(p, (ten_days_ago, ten_days_ago))
            os.environ["VAULT_PATH"] = tmp
            try:
                # since = 5 days ago → old file NOT included
                since = time.time() - 5 * 86400
                out = temporal_changed.walk_changed(since)
                self.assertEqual(len(out), 0)
            finally:
                del os.environ["VAULT_PATH"]


if __name__ == "__main__":
    unittest.main()
