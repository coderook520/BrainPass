"""Unit tests for the human-session gate.

Run with: python3 -m unittest discover -s tests -v
"""
import base64
import hashlib
import hmac
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bp_gate.gate_mixin import (  # noqa: E402
    HumanSessionGateMixin, GATED_POST, GATED_GET, OPEN_ALWAYS,
)
import bp_gate.gate_mixin as gm  # noqa: E402
from bp_gate.scrub_keys import scrub, scrub_str  # noqa: E402


def _make_token(secret: bytes, issued_ts: int, expires_ts: int, pid: int = 1234) -> str:
    payload = f"{pid}:{issued_ts}:{expires_ts}"
    b64 = base64.urlsafe_b64encode(payload.encode()).decode("ascii").rstrip("=")
    sig = hmac.new(secret, b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


class FakeHandler:
    """Stand-in for BaseHTTPRequestHandler with a pre-renamed do_POST."""

    def __init__(self, path="/recall", token="", client_address=("127.0.0.1", 0)):
        self.path = path
        self.headers = {"X-Human-Session-Token": token} if token else {}
        self.client_address = client_address
        self.calls = []

    def send_error(self, code, msg=""):
        self.calls.append(("send_error", code, msg))

    def _do_POST_orig(self):
        self.calls.append(("orig_post",))

    def _do_GET_orig(self):
        self.calls.append(("orig_get",))


class Handler(HumanSessionGateMixin, FakeHandler):
    pass


class GateMixinTest(unittest.TestCase):
    """Asserts the gate blocks unauthenticated callers and runs original
    handlers only when the session is valid. Closes the MRO-ordering trap:
    the mixin's do_POST/do_GET MUST be chosen over a subclass's own
    methods; deploy-time rename of originals to _do_POST_orig makes that work.
    """

    def setUp(self):
        GATED_POST.clear(); GATED_POST.add("/recall")
        GATED_GET.clear()
        OPEN_ALWAYS.clear(); OPEN_ALWAYS.update({"/health", "/status"})
        # Snapshot module-level fns we're about to monkeypatch
        self._saved = {
            "_tracker_alive": gm._tracker_alive,
            "_secret_version": gm._secret_version,
            "_verify_token": gm._verify_token,
            "_flag_fresh": gm._flag_fresh,
            "_audit_gate_decision": gm._audit_gate_decision,
        }
        # Silence audit writes during tests
        gm._audit_gate_decision = lambda *a, **kw: None

    def tearDown(self):
        for name, fn in self._saved.items():
            setattr(gm, name, fn)

    def test_tracker_down_blocks_before_orig(self):
        h = Handler(path="/recall")
        gm._tracker_alive = lambda: False
        h.do_POST()
        self.assertIn(("send_error", 503, "human-session tracker offline"), h.calls)
        self.assertNotIn(("orig_post",), h.calls)

    def test_invalid_token_blocks(self):
        h = Handler(path="/recall", token="bogus")
        gm._tracker_alive = lambda: True
        gm._secret_version = lambda: 1
        gm._verify_token = lambda t: False
        h.do_POST()
        self.assertIn(("send_error", 403, "invalid human-session token"), h.calls)
        self.assertNotIn(("orig_post",), h.calls)

    def test_stale_flag_blocks(self):
        h = Handler(path="/recall", token="ok.signed")
        gm._tracker_alive = lambda: True
        gm._secret_version = lambda: 1
        gm._verify_token = lambda t: True
        gm._flag_fresh = lambda: False
        h.do_POST()
        self.assertIn(("send_error", 403, "no fresh human session"), h.calls)

    def test_valid_session_passes_to_orig(self):
        h = Handler(path="/recall", token="ok.signed")
        gm._tracker_alive = lambda: True
        gm._secret_version = lambda: 1
        gm._verify_token = lambda t: True
        gm._flag_fresh = lambda: True
        h.do_POST()
        self.assertIn(("orig_post",), h.calls)

    def test_open_path_bypasses_gate(self):
        h = Handler(path="/health")
        gm._tracker_alive = lambda: False
        h.do_GET()
        self.assertNotIn(("send_error", 503, "human-session tracker offline"), h.calls)
        self.assertIn(("orig_get",), h.calls)

    def test_ungated_path_passes_through(self):
        h = Handler(path="/unknown")
        gm._tracker_alive = lambda: False
        h.do_POST()
        self.assertIn(("orig_post",), h.calls)


class TtlEnforcementTest(unittest.TestCase):
    """Ticket format: base64(pid:issued:expires).hmac — the gate MUST
    decode the payload and reject tokens that are expired or issued in
    the future (beyond a small clock-skew tolerance).
    """

    def setUp(self):
        self.secret = os.urandom(32)
        self._saved_read_secret = gm._read_secret
        gm._read_secret = lambda: self.secret

    def tearDown(self):
        gm._read_secret = self._saved_read_secret

    def test_valid_window_accepted(self):
        now = int(time.time())
        self.assertTrue(gm._verify_token(_make_token(self.secret, now - 5, now + 25)))

    def test_expired_rejected(self):
        now = int(time.time())
        self.assertFalse(gm._verify_token(_make_token(self.secret, now - 600, now - 500)))

    def test_future_rejected(self):
        now = int(time.time())
        self.assertFalse(gm._verify_token(_make_token(self.secret, now + 600, now + 620)))

    def test_clock_skew_within_2s_accepted(self):
        now = int(time.time())
        self.assertTrue(gm._verify_token(_make_token(self.secret, now + 1, now + 30)))

    def test_malformed_payload_rejected(self):
        b64 = base64.urlsafe_b64encode(b"only-two:parts").decode("ascii").rstrip("=")
        sig = hmac.new(self.secret, b64.encode(), hashlib.sha256).hexdigest()
        self.assertFalse(gm._verify_token(f"{b64}.{sig}"))

    def test_hmac_mismatch_rejected(self):
        now = int(time.time())
        tok = _make_token(self.secret, now, now + 30)
        b64, _ = tok.rsplit(".", 1)
        self.assertFalse(gm._verify_token(f"{b64}.{'a'*64}"))


class ScrubKeysTest(unittest.TestCase):
    def test_groq(self):
        self.assertEqual(
            scrub_str("leaked gsk_abcdefghijklmnopqrstuvwxyz0123 bye"),
            "leaked gsk_REDACTED bye",
        )

    def test_xai(self):
        self.assertIn("xai-REDACTED", scrub_str("xai-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))

    def test_openai(self):
        self.assertIn("sk-REDACTED", scrub_str("sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ"))

    def test_anthropic(self):
        self.assertIn("sk-ant-REDACTED",
                      scrub_str("sk-ant-apiABCDEFGHIJKLMNOPQRSTUVWXYZ"))

    def test_bearer(self):
        self.assertIn("Bearer REDACTED",
                      scrub_str("Authorization: Bearer abcdefghij01234567890"))

    def test_short_keys_not_scrubbed(self):
        self.assertEqual(scrub_str("gsk_short"), "gsk_short")

    def test_multiple_in_one_string(self):
        s = "k1=gsk_aaaaaaaaaaaaaaaaaaaaaa k2=gsk_bbbbbbbbbbbbbbbbbbbbbb"
        out = scrub_str(s)
        self.assertEqual(out.count("gsk_REDACTED"), 2)


if __name__ == "__main__":
    unittest.main()
