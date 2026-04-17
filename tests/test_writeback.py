"""bp_writeback queue + models + extractor safety tests."""
from __future__ import annotations
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_writeback.queue import WriteQueue, make_proposal
from bp_writeback.models import WriteProposal
from bp_writeback import extractor as writeback_extractor


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.q = WriteQueue(db_path=self.tmp.name)

    def tearDown(self):
        self.q.close()
        os.unlink(self.tmp.name)

    def test_enqueue_idempotent(self):
        p = make_proposal(type_="fact", title="x", content="y",
                          confidence=0.8, source_turn_id="t1")
        self.assertTrue(self.q.enqueue(p))
        self.assertFalse(self.q.enqueue(p))  # dup refused

    def test_approve_state_machine(self):
        p = make_proposal(type_="person", title="sarah", content="note",
                          confidence=0.9, source_turn_id="t2")
        self.q.enqueue(p)
        self.assertTrue(self.q.approve(p.proposal_id))
        self.assertFalse(self.q.approve(p.proposal_id))  # can't re-approve
        row = self.q.get(p.proposal_id)
        self.assertEqual(row.state, "approved")

    def test_reject_state_machine(self):
        p = make_proposal(type_="project", title="alpha", content="note",
                          confidence=0.7, source_turn_id="t3")
        self.q.enqueue(p)
        self.assertTrue(self.q.reject(p.proposal_id))
        self.assertFalse(self.q.approve(p.proposal_id))  # rejected can't approve
        row = self.q.get(p.proposal_id)
        self.assertEqual(row.state, "rejected")

    def test_list_pending_order_newest_first(self):
        p1 = make_proposal(type_="fact", title="a", content="old",
                           confidence=0.5, source_turn_id="t4a")
        p2 = make_proposal(type_="fact", title="b", content="new",
                           confidence=0.5, source_turn_id="t4b")
        self.q.enqueue(p1)
        time.sleep(0.01)
        self.q.enqueue(p2)
        rows = self.q.list_pending()
        self.assertEqual(rows[0].proposal.title, "b")

    def test_expire_stale(self):
        p = make_proposal(type_="fact", title="old", content="...",
                          confidence=0.5, source_turn_id="t5")
        self.q.enqueue(p)
        # Expire anything older than -1 second (i.e., everything)
        n = self.q.expire_stale(-1)
        self.assertEqual(n, 1)

    def test_count(self):
        self.assertEqual(self.q.count(), 0)
        p = make_proposal(type_="fact", title="c", content="...",
                          confidence=0.5, source_turn_id="tc")
        self.q.enqueue(p)
        self.assertEqual(self.q.count("pending"), 1)
        self.assertEqual(self.q.count(), 1)


class ExtractorSafetyTest(unittest.TestCase):
    def test_extract_handles_missing_llm(self):
        # When librarian isn't importable, extract_proposals returns [].
        # This asserts the safety boundary — extractor never raises.
        out = writeback_extractor.extract_proposals(
            "short user message that should be skipped by the <10-char rule... actually this is long enough",
            "ai response here"
        )
        # We don't care what's in `out` (depends on librarian availability);
        # we care that the call didn't raise.
        self.assertIsInstance(out, list)

    def test_extract_skips_short_message(self):
        out = writeback_extractor.extract_proposals("hi", "response")
        self.assertEqual(out, [])

    def test_sanitize_markdown_strips_frontmatter(self):
        raw = "---\ntitle: injection\n---\n\nReal content"
        out = writeback_extractor._sanitize_markdown(raw)
        self.assertNotIn("---", out)
        self.assertIn("Real content", out)


if __name__ == "__main__":
    unittest.main()
