#!/usr/bin/env python3
"""
BrainPass Librarian — Agent Memory System

HTTP service that searches a local Obsidian vault and compiles relevant
notes into a citeable answer via your configured LLM provider.

Supported providers: groq, openai, anthropic, local (OpenAI-compatible).
Stdlib only — no pip install needed.
"""

import json
import os
import sys
import time
import re
import signal
import urllib.request
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs


# ─── CONFIGURATION ───────────────────────────────────────────────────
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower().strip()


def _load_api_keys(provider):
    """Return the list of non-empty API keys for the configured provider."""
    if provider == "groq":
        candidates = [
            os.environ.get("GROQ_API_KEY", ""),
            os.environ.get("GROQ_API_KEY_2", ""),
            os.environ.get("GROQ_API_KEY_3", ""),
        ]
    elif provider == "openai":
        candidates = [os.environ.get("OPENAI_API_KEY", "")]
    elif provider == "anthropic":
        candidates = [os.environ.get("ANTHROPIC_API_KEY", "")]
    elif provider == "local":
        # Local endpoints often don't need a key; allow one if set
        candidates = [os.environ.get("LOCAL_LLM_API_KEY", "not-needed")]
    else:
        candidates = []
    return [k for k in candidates if k]


API_KEYS = _load_api_keys(LLM_PROVIDER)

# Model + endpoint per provider
if LLM_PROVIDER == "groq":
    LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
    LLM_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    LLM_FALLBACK = os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")
elif LLM_PROVIDER == "openai":
    LLM_URL = "https://api.openai.com/v1/chat/completions"
    LLM_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
    LLM_FALLBACK = os.environ.get("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
elif LLM_PROVIDER == "anthropic":
    LLM_URL = "https://api.anthropic.com/v1/messages"
    LLM_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    LLM_FALLBACK = os.environ.get("ANTHROPIC_FALLBACK_MODEL", "claude-3-5-haiku-latest")
elif LLM_PROVIDER == "local":
    LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1/chat/completions")
    LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "llama3.1")
    LLM_FALLBACK = LLM_MODEL
else:
    print(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}", file=sys.stderr)
    print("Valid options: groq, openai, anthropic, local", file=sys.stderr)
    sys.exit(1)

# Paths
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "~/BrainPass/vault")).expanduser()
CACHE_FILE = Path(os.environ.get("CACHE_PATH", "/tmp/brainpass-topic.txt"))

# Identity files — resolve from config relative to this script's parent.
# Respect ~/BrainPass/config/identity/ first (installed location), fall back
# to the repo-relative config/ so dev runs still work.
_SCRIPT_DIR = Path(__file__).resolve().parent
_INSTALLED_IDENTITY = Path("~/BrainPass/config/identity").expanduser()
_REPO_IDENTITY = _SCRIPT_DIR.parent / "config" / "identity"
IDENTITY_DIR = _INSTALLED_IDENTITY if _INSTALLED_IDENTITY.exists() else _REPO_IDENTITY
SOUL_FILE = IDENTITY_DIR / "SOUL.md"
MEMORY_FILE = IDENTITY_DIR / "MEMORY.md"

# Server
SERVE_PORT = int(os.environ.get("LIBRARIAN_PORT", 7778))

# Agent identity defaults (used only when SOUL.md is absent)
AGENT_NAME = os.environ.get("AGENT_NAME", "Assistant")
AGENT_ROLE = os.environ.get("AGENT_ROLE", "Helpful AI")


# ─── IDENTITY LOADING ────────────────────────────────────────────────
_SOUL_CACHE = {"text": "", "mtime": 0.0}
_SOUL_FALLBACK = (
    f"You are {AGENT_NAME}. {AGENT_ROLE}. "
    "You search memory files and return relevant context with citations."
)


def load_soul():
    try:
        mtime = SOUL_FILE.stat().st_mtime
    except Exception:
        return _SOUL_CACHE["text"] or _SOUL_FALLBACK

    if mtime != _SOUL_CACHE["mtime"]:
        try:
            _SOUL_CACHE["text"] = SOUL_FILE.read_text(errors="ignore")
            _SOUL_CACHE["mtime"] = mtime
        except Exception:
            if not _SOUL_CACHE["text"]:
                return _SOUL_FALLBACK
    return _SOUL_CACHE["text"] or _SOUL_FALLBACK


def load_memory_manual():
    try:
        return MEMORY_FILE.read_text(errors="ignore")
    except Exception:
        return ""


# ─── FILE SEARCH ─────────────────────────────────────────────────────
_brain_count_cache = {"count": 0, "last_check": 0.0}


def count_brain_files():
    global _brain_count_cache
    now = time.time()
    if now - _brain_count_cache["last_check"] < 300:
        return _brain_count_cache["count"]

    count = len(list(VAULT_PATH.rglob("*.md"))) if VAULT_PATH.exists() else 0
    _brain_count_cache = {"count": count, "last_check": now}
    return count


def search_files(query, max_results=5):
    results = []
    query_lower = query.lower()

    if not VAULT_PATH.exists():
        return results

    query_words = [w for w in query_lower.split() if len(w) > 2]
    if not query_words:
        return results

    for file_path in VAULT_PATH.rglob("*.md"):
        try:
            content = file_path.read_text(errors="ignore")
            content_lower = content.lower()
            score = sum(content_lower.count(word) for word in query_words)

            if score > 0:
                preview = content[:500] + "..." if len(content) > 500 else content
                results.append({
                    "file": str(file_path.relative_to(VAULT_PATH)),
                    "score": score,
                    "preview": preview,
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


# ─── LLM API ─────────────────────────────────────────────────────────
def _post_json(url, headers, payload, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _call_openai_compatible(api_key, messages, max_tokens):
    """Works for groq, openai, and local OpenAI-compatible endpoints."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "BrainPass/1.0",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    result = _post_json(LLM_URL, headers, payload)
    return result["choices"][0]["message"]["content"]


def _call_anthropic(api_key, messages, max_tokens):
    """Anthropic Messages API — separate system field, different headers."""
    system_content = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_content += (m.get("content", "") + "\n")
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "User-Agent": "BrainPass/1.0",
    }
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "system": system_content.strip(),
        "messages": user_messages,
    }
    result = _post_json(LLM_URL, headers, payload)
    # Anthropic returns {"content": [{"type": "text", "text": "..."}], ...}
    blocks = result.get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def call_llm(messages, max_tokens=2000):
    if not API_KEYS:
        return json.dumps({"error": f"No API keys configured for provider '{LLM_PROVIDER}'"})

    last_error = ""
    for api_key in API_KEYS:
        try:
            if LLM_PROVIDER == "anthropic":
                return _call_anthropic(api_key, messages, max_tokens)
            return _call_openai_compatible(api_key, messages, max_tokens)
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                time.sleep(1)
                continue

    return json.dumps({"error": f"All keys failed. Last: {last_error}"})


# ─── RECALL ENGINE ───────────────────────────────────────────────────
_SKIP_PATTERNS = [
    re.compile(r"^(ok|okay|cool|nice|yeah|yes|no|hi|hey|hello|bye|thanks?)$", re.I),
    re.compile(r"^https?://", re.I),
    re.compile(r"^\s*$"),
    re.compile(r"^/\w+$"),
]


def recall(raw_message, topic_hint=""):
    topic = topic_hint or raw_message[:100]
    stripped = raw_message.strip()

    if any(p.match(stripped) for p in _SKIP_PATTERNS) or len(stripped) < 10:
        return {"result": "", "topic": topic, "skipped": True}

    search_results = search_files(topic, max_results=5)

    if not search_results:
        return {"result": "", "topic": topic, "files_searched": 0}

    context = ""
    for i, result in enumerate(search_results, 1):
        context += f"\n--- Source {i}: {result['file']} ---\n{result['preview']}\n"

    soul = load_soul()
    memory = load_memory_manual()

    messages = [
        {"role": "system", "content": f"{soul}\n\nJob Manual:\n{memory}"},
        {"role": "user", "content": (
            f"Given this user message and sources, extract relevant information:\n\n"
            f"USER MESSAGE: {raw_message}\n\n"
            f"SEARCH TOPIC: {topic}\n\n"
            f"SOURCES:{context}\n\n"
            f"Return concise facts, citing sources [1], [2], etc."
        )},
    ]

    llm_response = call_llm(messages)

    try:
        CACHE_FILE.write_text(llm_response)
    except Exception:
        pass

    return {
        "result": llm_response,
        "topic": topic,
        "files_searched": len(search_results),
        "sources": [r["file"] for r in search_results],
    }


# ─── HTTP SERVER ─────────────────────────────────────────────────────
class LibrarianHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        path = self.path.split("?", 1)[0]

        if path == "/health":
            self._send_json({"status": "ok", "port": SERVE_PORT})
        elif path == "/status":
            self._send_json({
                "status": "ok",
                "vault_path": str(VAULT_PATH),
                "port": SERVE_PORT,
                "llm_provider": LLM_PROVIDER,
                "llm_model": LLM_MODEL,
                "keys_configured": len(API_KEYS),
                "files_indexed": count_brain_files(),
            })
        elif path == "/query":
            query = parsed.get("q", [""])[0]
            result = recall(query, topic_hint=query)
            self._send_json(result)
        else:
            self._send_json({"error": "unknown endpoint"}, status=404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/recall":
            message = data.get("message", "")
            topic = data.get("topic", "")
            result = recall(message, topic_hint=topic)
            self._send_json(result)
        else:
            self._send_json({"error": "unknown endpoint"}, status=404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())


def serve():
    import threading
    server = HTTPServer(("127.0.0.1", SERVE_PORT), LibrarianHandler)
    print(f"BrainPass Librarian serving on 127.0.0.1:{SERVE_PORT}", file=sys.stderr)
    print(f"  provider={LLM_PROVIDER} model={LLM_MODEL} keys={len(API_KEYS)}", file=sys.stderr)

    def graceful_exit(signum, frame):
        # server.shutdown() must run on a thread other than the one stuck
        # inside serve_forever(), otherwise it deadlocks per the Python docs.
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGINT, graceful_exit)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: librarian.py <serve|status>", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "serve":
        serve()
    elif cmd == "status":
        print(json.dumps({
            "vault_exists": VAULT_PATH.exists(),
            "soul_exists": SOUL_FILE.exists(),
            "memory_exists": MEMORY_FILE.exists(),
            "port": SERVE_PORT,
            "provider": LLM_PROVIDER,
            "model": LLM_MODEL,
            "keys": len(API_KEYS),
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
