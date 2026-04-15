#!/usr/bin/env python3
"""
BrainPass Librarian — Agent Memory System
Powered by Obsidian + NotebookLM + Your Choice of LLM

This is the sanitized, open-source version of Gia's memory system.
Customize for your agent and LLM provider.
"""

import json
import os
import sys
import time
import re
import signal
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# ─── CONFIGURATION ───────────────────────────────────────────────────
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")

# API Keys — primary + fallbacks
API_KEYS = [
    os.environ.get("GROQ_API_KEY", ""),
    os.environ.get("GROQ_API_KEY_2", ""),
    os.environ.get("GROQ_API_KEY_3", ""),
]
API_KEYS = [k for k in API_KEYS if k]

# Model configuration
if LLM_PROVIDER == "groq":
    LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
    LLM_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    LLM_FALLBACK = os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")
elif LLM_PROVIDER == "openai":
    LLM_URL = "https://api.openai.com/v1/chat/completions"
    LLM_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4")
    LLM_FALLBACK = os.environ.get("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo")
elif LLM_PROVIDER == "anthropic":
    LLM_URL = "https://api.anthropic.com/v1/messages"
    LLM_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    LLM_FALLBACK = os.environ.get("ANTHROPIC_FALLBACK_MODEL", "claude-3-sonnet-20240229")
elif LLM_PROVIDER == "local":
    LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1/chat/completions")
    LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "llama2")
    LLM_FALLBACK = LLM_MODEL

# Paths
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "~/BrainPass/vault")).expanduser()
CACHE_FILE = Path(os.environ.get("CACHE_PATH", "/tmp/brainpass-topic.txt"))

# Identity files
IDENTITY_DIR = Path(__file__).parent.parent / "config" / "identity"
SOUL_FILE = IDENTITY_DIR / "SOUL.md"
MEMORY_FILE = IDENTITY_DIR / "MEMORY.md"

# Server
SERVE_PORT = int(os.environ.get("LIBRARIAN_PORT", 7778))

# Agent identity
AGENT_NAME = os.environ.get("AGENT_NAME", "Assistant")
AGENT_ROLE = os.environ.get("AGENT_ROLE", "Helpful AI")


# ─── IDENTITY LOADING ────────────────────────────────────────────────
_SOUL_CACHE = {"text": "", "mtime": 0.0}
_SOUL_FALLBACK = f"You are {AGENT_NAME}. {AGENT_ROLE}. You search memory files and return relevant context."


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
    except:
        return ""


# ─── FILE SEARCH ─────────────────────────────────────────────────────
_brain_count_cache = {"count": 0, "last_check": 0}

def count_brain_files():
    global _brain_count_cache
    import time
    now = time.time()
    if now - _brain_count_cache["last_check"] < 300:
        return _brain_count_cache["count"]
    
    count = 0
    if VAULT_PATH.exists():
        count = len(list(VAULT_PATH.rglob("*.md")))
    
    _brain_count_cache = {"count": count, "last_check": now}
    return count


def search_files(query, max_results=5):
    results = []
    query_lower = query.lower()
    
    if not VAULT_PATH.exists():
        return results
    
    for file_path in VAULT_PATH.rglob("*.md"):
        try:
            content = file_path.read_text(errors="ignore")
            score = 0
            query_words = query_lower.split()
            content_lower = content.lower()
            
            for word in query_words:
                if len(word) > 2:
                    score += content_lower.count(word)
            
            if score > 0:
                results.append({
                    "file": str(file_path.relative_to(VAULT_PATH)),
                    "score": score,
                    "preview": content[:500] + "..." if len(content) > 500 else content
                })
        except Exception:
            continue
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


# ─── LLM API ─────────────────────────────────────────────────────────
def call_llm(messages, max_tokens=2000):
    if not API_KEYS:
        return json.dumps({"error": "No API keys configured"})
    
    last_error = ""
    
    for api_key in API_KEYS:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BrainPass/1.0"
        }
        
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        try:
            import urllib.request
            req = urllib.request.Request(
                LLM_URL,
                data=json.dumps(payload).encode(),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                time.sleep(1)
                continue
    
    return json.dumps({"error": f"All keys failed. Last: {last_error}"})


# ─── RECALL ENGINE ───────────────────────────────────────────────────
def recall(raw_message, topic_hint=""):
    topic = topic_hint or raw_message[:100]
    
    # Skip short messages
    skip_patterns = [
        r"^(ok|okay|cool|nice|yeah|yes|no|hi|hey|hello|bye|thanks?)$",
        r"^http[s]?://",
        r"^[\s]*$",
        r"^/\w+$",
    ]
    if any(re.match(p, raw_message.strip(), re.I) for p in skip_patterns):
        return {"result": "", "topic": topic, "skipped": True}
    if len(raw_message.strip()) < 10:
        return {"result": "", "topic": topic, "skipped": True}
    
    # Search files
    search_results = search_files(topic, max_results=5)
    
    if not search_results:
        return {"result": "", "topic": topic, "files_searched": 0}
    
    # Build context
    context = ""
    for i, result in enumerate(search_results, 1):
        context += f"\n--- Source {i}: {result['file']} ---\n{result['preview']}\n"
    
    # Call LLM
    soul = load_soul()
    memory = load_memory_manual()
    
    messages = [
        {"role": "system", "content": f"{soul}\n\nJob Manual:\n{memory}"},
        {"role": "user", "content": f"""Given this user message and sources, extract relevant information:

USER MESSAGE: {raw_message}

SEARCH TOPIC: {topic}

SOURCES:{context}

Return concise facts, citing sources [1], [2], etc."""}
    ]
    
    llm_response = call_llm(messages)
    
    # Save to topic file
    try:
        CACHE_FILE.write_text(llm_response)
    except:
        pass
    
    return {
        "result": llm_response,
        "topic": topic,
        "files_searched": len(search_results),
        "sources": [r["file"] for r in search_results]
    }


# ─── HTTP SERVER ─────────────────────────────────────────────────────
class LibrarianHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        parsed = parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
        path = self.path.split("?")[0]
        
        if path == "/health":
            self._send_json({"status": "ok", "port": SERVE_PORT})
        elif path == "/status":
            self._send_json({
                "status": "ok",
                "vault_path": str(VAULT_PATH),
                "port": SERVE_PORT,
                "llm_provider": LLM_PROVIDER,
                "keys_configured": len(API_KEYS),
                "files_indexed": count_brain_files()
            })
        elif path == "/query":
            query = parsed.get("q", [""])[0]
            result = recall(query, topic_hint=query)
            self._send_json(result)
        else:
            self._send_json({"error": "unknown endpoint"}, status=404)
    
    def do_POST(self):
        path = self.path.split("?")[0]
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length else "{}"
        
        try:
            data = json.loads(body)
        except:
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
    server = HTTPServer(("127.0.0.1", SERVE_PORT), LibrarianHandler)
    print(f"BrainPass Librarian serving on port {SERVE_PORT}", file=sys.stderr)
    
    def graceful_exit(signum, frame):
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGINT, graceful_exit)
    
    server.serve_forever()


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
            "keys": len(API_KEYS)
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
