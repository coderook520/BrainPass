"""HumanSessionGateMixin — gates stdlib http.server handlers on human-session presence.

Usage (two edits to your librarian.py):

    from bp_gate.gate_mixin import HumanSessionGateMixin, GATED_POST, GATED_GET, OPEN_ALWAYS
    GATED_POST.update({"/recall"})               # endpoints that spend LLM budget
    GATED_GET.update({"/query", "/dreams"})       # GETs that spend LLM budget
    OPEN_ALWAYS.update({"/health", "/status"})   # probes, never gated

    class LibrarianHandler(HumanSessionGateMixin, BaseHTTPRequestHandler):
        def _do_POST_orig(self):   # <-- rename your original do_POST to this
            ...
        def _do_GET_orig(self):    # <-- rename your original do_GET to this
            ...

The mixin intercepts do_POST/do_GET, checks for a valid HMAC-signed
human-session token, and either proxies to _do_POST_orig/_do_GET_orig
or returns 403.
"""
import base64
import hmac
import hashlib
import json
import os
import socket
import syslog
import time
from collections import OrderedDict
from threading import Lock
from urllib.parse import urlparse

UID = os.getuid()
RUN_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{UID}")
SECRET_PATH = f"{RUN_DIR}/bp-human-session.secret"
FLAG_PATH = f"{RUN_DIR}/bp-human-session.active"
SOCK_PATH = f"{RUN_DIR}/bp-human-session.sock"

# Audit log — default under $HOME, override via BP_AUDIT_LOG
_AUDIT_LOG = os.environ.get(
    "BP_AUDIT_LOG",
    os.path.expanduser("~/.local/state/brainpass/gate.jsonl"),
)

# Populated by the librarian's import block. Don't set them here.
GATED_POST: set = set()
GATED_GET: set = set()
OPEN_ALWAYS: set = {"/health", "/status"}

# Process-local LRU keyed by (secret_mtime, token) — secret rotation auto-invalidates cache
_CACHE: "OrderedDict[tuple, float]" = OrderedDict()
_LOCK = Lock()
_CACHE_TTL = 5.0
_MAXSIZE = 256
FLAG_MAX_AGE = 60.0
CLOCK_SKEW_TOLERANCE = 2.0


def _secret_version():
    try:
        return os.stat(SECRET_PATH).st_mtime_ns
    except FileNotFoundError:
        return None


def _read_secret():
    try:
        fd = os.open(SECRET_PATH, os.O_RDONLY | os.O_NOFOLLOW)
    except (FileNotFoundError, OSError):
        return None
    try:
        return os.read(fd, 256)
    finally:
        os.close(fd)


def _flag_fresh():
    try:
        age = time.time() - os.stat(FLAG_PATH).st_mtime
        return age < FLAG_MAX_AGE
    except FileNotFoundError:
        return False


def _tracker_alive():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(SOCK_PATH)
        return True
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
        return False


def _verify_token(token):
    """Verify HMAC + embedded expiry window.

    Token format: base64url(payload) + "." + sha256_hmac_hex
    Payload: "<issuer_pid>:<issued_ts>:<expires_ts>"
    """
    if not isinstance(token, str) or len(token) > 512 or "." not in token:
        return False
    secret = _read_secret()
    if not secret:
        return False
    try:
        payload_b64, sig_hex = token.rsplit(".", 1)
    except ValueError:
        return False
    if len(sig_hex) != 64:
        return False
    expected = hmac.new(secret, payload_b64.encode("ascii", "replace"),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_hex):
        return False
    try:
        pad = "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64 + pad).decode("ascii", "replace")
        parts = payload.split(":")
        if len(parts) != 3:
            return False
        issued_ts = int(parts[1])
        expires_ts = int(parts[2])
    except (ValueError, UnicodeDecodeError, TypeError):
        return False
    now = int(time.time())
    if now + CLOCK_SKEW_TOLERANCE < issued_ts:
        return False
    if now > expires_ts:
        return False
    return True


def _audit_gate_decision(verified, path, method, caller_addr=None):
    """Emit structured JSONL of every gate decision. Never raises."""
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "gate_decision",
            "human_session_verified": bool(verified),
            "method": method,
            "path": path,
            "caller_addr": caller_addr or "",
        }
        line = (json.dumps(rec) + "\n").encode()
        os.makedirs(os.path.dirname(_AUDIT_LOG), mode=0o700, exist_ok=True)
        with open(_AUDIT_LOG, "ab") as f:
            f.write(line)
    except OSError as e:
        try:
            syslog.syslog(syslog.LOG_WARNING, f"bp-gate-audit: {e}")
        except OSError:
            pass
    except Exception:
        pass


def _is_open_path(path):
    if path in OPEN_ALWAYS:
        return True
    return any(path == p or path.startswith(p + "/") for p in OPEN_ALWAYS)


def _is_gated_path(method, path):
    gated = GATED_POST if method == "POST" else GATED_GET
    if path in gated:
        return True
    return any(path == g or path.startswith(g + "/") for g in gated)


class HumanSessionGateMixin:
    """Mixin for BaseHTTPRequestHandler subclasses. MUST be leftmost in bases.

    The librarian's original do_POST / do_GET MUST be renamed to
    _do_POST_orig / _do_GET_orig so MRO resolves this mixin's versions
    first (gate check) and the renamed originals run only after the gate
    returns True.
    """

    def _gate_pre_dispatch(self, method, path):
        """Return True to allow request; False if an error response was sent."""
        if _is_open_path(path):
            return True
        if not _is_gated_path(method, path):
            return True
        caller = getattr(self, "client_address", (None,))[0] if hasattr(self, "client_address") else None
        if not _tracker_alive():
            _audit_gate_decision(False, path, method, caller)
            self.send_error(503, "human-session tracker offline")
            return False
        token = self.headers.get("X-Human-Session-Token", "")
        sv = _secret_version()
        if sv is None:
            _audit_gate_decision(False, path, method, caller)
            self.send_error(503, "secret unavailable")
            return False
        cache_key = (sv, token)
        now = time.time()
        with _LOCK:
            cached_at = _CACHE.get(cache_key)
            if cached_at is not None and (now - cached_at) < _CACHE_TTL:
                _CACHE.move_to_end(cache_key)
                return True
        if not _verify_token(token):
            _audit_gate_decision(False, path, method, caller)
            self.send_error(403, "invalid human-session token")
            return False
        if not _flag_fresh():
            _audit_gate_decision(False, path, method, caller)
            self.send_error(403, "no fresh human session")
            return False
        with _LOCK:
            _CACHE[cache_key] = now
            _CACHE.move_to_end(cache_key)
            while len(_CACHE) > _MAXSIZE:
                _CACHE.popitem(last=False)
        _audit_gate_decision(True, path, method, caller)
        return True

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._gate_pre_dispatch("POST", path):
            return
        self._do_POST_orig()

    def do_GET(self):
        path = urlparse(self.path).path
        if not self._gate_pre_dispatch("GET", path):
            return
        self._do_GET_orig()
