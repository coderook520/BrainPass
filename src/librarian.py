#!/usr/bin/env python3
"""
BrainPass Librarian — Agent Memory System

HTTP service that searches a local Obsidian vault and compiles relevant
notes into a citeable answer via your configured LLM provider.

Search engine: BM25 chunk-based scoring with optional frontmatter metadata,
recency/frequency signals, and configurable stopwords.

Supported providers: groq, openai, anthropic, local (OpenAI-compatible).
Stdlib only — no pip install needed.
"""

import fcntl
import json
import math
import os
import sys
import time
import re
import signal
import urllib.request
from dataclasses import dataclass
from datetime import date as _date_cls
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

# Optional: NotebookLM notebook URL for deeper semantic search.
NOTEBOOKLM_URL = os.environ.get("NOTEBOOKLM_URL", "").strip()

# Identity files
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


# ─── SEARCH TUNING (with range clamping) ────────────────────────────
def _clamp_env(name, default, lo, hi, as_type=float):
    try:
        val = as_type(os.environ.get(name, str(default)))
        val = max(lo, min(hi, val))
    except (ValueError, TypeError):
        val = as_type(default)
        print(f"[warn] invalid {name}, using default {default}", file=sys.stderr)
    return val


BM25_K1 = _clamp_env("BM25_K1", 1.5, 0.5, 3.0)
BM25_B = _clamp_env("BM25_B", 0.75, 0.0, 1.0)
CHUNK_SIZE = _clamp_env("CHUNK_SIZE", 300, 50, 2000, int)
CHUNK_MIN = _clamp_env("CHUNK_MIN", 50, 10, 500, int)
CHUNK_MAX = _clamp_env("CHUNK_MAX", 600, 200, 5000, int)
INDEX_TTL = _clamp_env("INDEX_TTL", 60, 5, 3600, int)
BM25_MIN_SCORE = _clamp_env("BM25_MIN_SCORE", 0.1, 0.0, 50.0)
TAG_BOOST = _clamp_env("TAG_BOOST", 2.0, 0.0, 3.0)
RECENCY_HALF_LIFE = _clamp_env("RECENCY_HALF_LIFE", 30.0, 1.0, 365.0)
FREQUENCY_BOOST_MAX = _clamp_env("FREQUENCY_BOOST_MAX", 1.0, 0.0, 5.0)
MAX_CHUNKS = _clamp_env("MAX_CHUNKS", 10000, 100, 100000, int)

# Cross-validation: CHUNK_MIN <= CHUNK_SIZE <= CHUNK_MAX
if CHUNK_MIN > CHUNK_SIZE or CHUNK_SIZE > CHUNK_MAX:
    print("[warn] CHUNK_MIN/SIZE/MAX inconsistent, resetting to defaults", file=sys.stderr)
    CHUNK_MIN, CHUNK_SIZE, CHUNK_MAX = 50, 300, 600

# Access log: hardcoded under vault path (not user-configurable)
_ACCESS_LOG_DIR = VAULT_PATH / ".brainpass"
_ACCESS_LOG_FILE = _ACCESS_LOG_DIR / "access.json"


# ─── STOPWORDS ──────────────────────────────────────────────────────
_DEFAULT_STOPWORDS: frozenset = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren", "arent", "as", "at", "be", "because",
    "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cannot", "could", "couldn", "couldnt", "d", "did", "didn",
    "didnt", "do", "does", "doesn", "doesnt", "doing", "don", "dont",
    "down", "during", "each", "few", "for", "from", "further", "get",
    "got", "had", "hadn", "hadnt", "has", "hasn", "hasnt", "have",
    "haven", "havent", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "isn", "isnt", "it", "its", "itself", "just", "ll", "m", "me",
    "might", "mightn", "more", "most", "mustn", "mustnt", "my", "myself",
    "need", "needn", "no", "nor", "not", "now", "o", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "re", "s", "same", "shan", "shant", "she", "should",
    "shouldn", "shouldnt", "so", "some", "such", "t", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "ve", "very", "was", "wasn", "wasnt", "we", "were",
    "weren", "werent", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "won", "wont", "would", "wouldn",
    "wouldnt", "y", "you", "your", "yours", "yourself", "yourselves",
})


def _load_stopwords() -> frozenset:
    sw_file = os.environ.get("STOPWORDS_FILE", "").strip()
    if not sw_file:
        return _DEFAULT_STOPWORDS
    p = Path(sw_file).expanduser()
    try:
        if not p.is_file() or p.stat().st_size > 1_000_000:
            print(f"[warn] STOPWORDS_FILE invalid or too large, using defaults", file=sys.stderr)
            return _DEFAULT_STOPWORDS
        words = {w.strip().lower() for w in p.read_text(errors="ignore").splitlines() if w.strip()}
        return frozenset(words) if words else _DEFAULT_STOPWORDS
    except Exception:
        return _DEFAULT_STOPWORDS


STOPWORDS = _load_stopwords()

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list:
    """Lowercase, extract alphanumeric tokens, filter stopwords."""
    return [w for w in _TOKEN_RE.findall(text.lower()) if w not in STOPWORDS]


# ─── FRONTMATTER PARSING ────────────────────────────────────────────
_FRONTMATTER_MAX = 4096  # bytes — skip frontmatter if closing --- is beyond this


def _is_number(s: str) -> bool:
    if not s or s.lower() in ("inf", "-inf", "nan", "infinity", "-infinity"):
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def parse_frontmatter(content: str):
    """Extract YAML frontmatter if present. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content

    end = content.find("\n---", 3)
    if end == -1 or end > _FRONTMATTER_MAX:
        return {}, content

    front = content[3:end].strip()
    body = content[end + 4:].lstrip("\n")
    meta = {}

    for line in front.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"").lower() for v in value[1:-1].split(",")]
            meta[key] = [i for i in items if i and len(i) <= 50]
        elif _is_number(value):
            meta[key] = float(value)
        else:
            meta[key] = value

    # Clamp importance
    if "importance" in meta:
        if not isinstance(meta["importance"], (int, float)):
            meta["importance"] = 1.0
        else:
            if meta["importance"] > 1.5:
                print(f"[warn] high importance={meta['importance']} in frontmatter", file=sys.stderr)
            meta["importance"] = max(0.1, min(2.0, meta["importance"]))

    return meta, body


# ─── CHUNKING ────────────────────────────────────────────────────────
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def chunk_file(content: str, target_size: int = None):
    """Split content into chunks of roughly target_size words."""
    if target_size is None:
        target_size = CHUNK_SIZE

    paragraphs = re.split(r'\n\s*\n', content)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [content] if len(content.split()) >= 10 else []

    # Phase 1: split oversized paragraphs on sentence boundaries
    blocks = []
    for para in paragraphs:
        words = para.split()
        if len(words) > CHUNK_MAX:
            sentences = _SENTENCE_RE.split(para)
            current = []
            current_len = 0
            for sent in sentences:
                sent_len = len(sent.split())
                if current_len + sent_len > target_size and current:
                    blocks.append(" ".join(current))
                    current = [sent]
                    current_len = sent_len
                else:
                    current.append(sent)
                    current_len += sent_len
            if current:
                blocks.append(" ".join(current))
        else:
            blocks.append(para)

    # Phase 2: merge small consecutive blocks up to target_size
    chunks = []
    current_chunk = []
    current_len = 0
    for block in blocks:
        block_len = len(block.split())
        if current_len + block_len > target_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [block]
            current_len = block_len
        else:
            current_chunk.append(block)
            current_len += block_len
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Phase 3: discard trivial chunks
    return [c for c in chunks if len(c.split()) >= 10]


# ─── ACCESS LOG (frequency tracking) ────────────────────────────────
def _ensure_access_dir():
    try:
        os.makedirs(str(_ACCESS_LOG_DIR), mode=0o700, exist_ok=True)
    except Exception:
        pass


def _load_access_log() -> dict:
    try:
        if not _ACCESS_LOG_FILE.exists():
            return {}
        st = os.lstat(str(_ACCESS_LOG_FILE))
        if st.st_size > 1_000_000:
            return {}
        if not os.path.isfile(str(_ACCESS_LOG_FILE)):
            return {}
        data = json.loads(_ACCESS_LOG_FILE.read_text())
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _save_access_log(log: dict) -> None:
    _ensure_access_dir()
    try:
        st = os.lstat(str(_ACCESS_LOG_FILE))
        import stat as _stat
        if _stat.S_ISLNK(st.st_mode):
            return
    except FileNotFoundError:
        pass
    except Exception:
        return

    try:
        fd = os.open(str(_ACCESS_LOG_FILE),
                      os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
                      0o600)
    except Exception:
        return

    try:
        # Non-blocking lock with retry
        locked = False
        for _ in range(10):
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except BlockingIOError:
                time.sleep(0.2)
        if not locked:
            return

        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps(log).encode())
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


def _touch_access(file_path: str) -> None:
    log = _load_access_log()
    entry = log.get(file_path, {"count": 0, "last_accessed": 0.0})
    entry["count"] = entry.get("count", 0) + 1
    entry["last_accessed"] = time.time()
    log[file_path] = entry
    _save_access_log(log)


# ─── BM25 CHUNK INDEX ───────────────────────────────────────────────
@dataclass
class ChunkInfo:
    """One indexed chunk."""
    file_path: str
    chunk_idx: int
    text: str
    tokens: list
    token_count: int
    meta: dict


class ChunkIndex:
    def __init__(self, vault_path, ttl=INDEX_TTL):
        self.vault_path = vault_path
        self.ttl = ttl
        self._chunks = []
        self._inverted = {}
        self._idf = {}
        self._avgdl = 0.0
        self._built_at = 0.0
        self._doc_count = 0

    @property
    def doc_count(self):
        return self._doc_count

    @property
    def index_age(self):
        return round(time.time() - self._built_at, 1) if self._built_at else None

    @property
    def is_fresh(self):
        return self._built_at > 0 and (time.time() - self._built_at) <= self.ttl

    def _ensure_fresh(self):
        if not self.is_fresh:
            self.build()

    def build(self):
        """Full index rebuild. Scans all .md files, chunks, tokenizes."""
        chunks = []

        if not self.vault_path.exists():
            self._chunks = []
            self._inverted = {}
            self._idf = {}
            self._avgdl = 0.0
            self._built_at = time.time()
            self._doc_count = 0
            return

        for file_path in self.vault_path.rglob("*.md"):
            try:
                content = file_path.read_text(errors="ignore")
            except Exception:
                continue

            rel_path = str(file_path.relative_to(self.vault_path))
            meta, body = parse_frontmatter(content)
            file_chunks = chunk_file(body)

            for idx, chunk_text in enumerate(file_chunks):
                tokens = tokenize(chunk_text)
                if not tokens:
                    continue
                chunks.append(ChunkInfo(
                    file_path=rel_path,
                    chunk_idx=idx,
                    text=chunk_text,
                    tokens=tokens,
                    token_count=len(tokens),
                    meta=meta,
                ))

                if len(chunks) >= MAX_CHUNKS:
                    print(f"[warn] MAX_CHUNKS={MAX_CHUNKS} reached, skipping remaining files",
                          file=sys.stderr)
                    break
            if len(chunks) >= MAX_CHUNKS:
                break

        # Build inverted index
        inverted = {}
        total_tokens = 0

        for ci, chunk in enumerate(chunks):
            total_tokens += chunk.token_count
            tf_map = {}
            for token in chunk.tokens:
                tf_map[token] = tf_map.get(token, 0) + 1
            for token, freq in tf_map.items():
                if token not in inverted:
                    inverted[token] = []
                inverted[token].append((ci, freq))

        N = len(chunks)
        idf = {}
        for token, postings in inverted.items():
            df = len(postings)
            idf[token] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        avgdl = total_tokens / N if N > 0 else 0.0

        self._chunks = chunks
        self._inverted = inverted
        self._idf = idf
        self._avgdl = avgdl
        self._built_at = time.time()
        self._doc_count = N

    def search(self, query: str, max_results: int = 5) -> list:
        """BM25 search. Returns list of {"file", "score", "preview"}."""
        self._ensure_fresh()

        query_tokens = tokenize(query)
        if not query_tokens or not self._chunks:
            return []

        access_log = _load_access_log()

        # Build per-chunk TF for query terms only
        candidates = set()
        chunk_tf = {}
        for qt in query_tokens:
            if qt in self._inverted:
                for ci, freq in self._inverted[qt]:
                    candidates.add(ci)
                    if ci not in chunk_tf:
                        chunk_tf[ci] = {}
                    chunk_tf[ci][qt] = freq

        scored = []

        for ci in candidates:
            chunk = self._chunks[ci]

            # BM25 base score
            bm25 = 0.0
            dl = chunk.token_count
            for qt in query_tokens:
                tf = chunk_tf.get(ci, {}).get(qt, 0)
                if tf == 0:
                    continue
                idf_val = self._idf.get(qt, 0.0)
                numerator = tf * (BM25_K1 + 1.0)
                denominator = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / self._avgdl) if self._avgdl > 0 else tf + BM25_K1
                bm25 += idf_val * numerator / denominator

            if bm25 < BM25_MIN_SCORE:
                continue

            # Importance multiplier
            importance = chunk.meta.get("importance", 1.0)
            if not isinstance(importance, (int, float)):
                importance = 1.0
            score = bm25 * max(importance, 0.1)

            # Tag boost
            tags = chunk.meta.get("tags", [])
            if isinstance(tags, list):
                tags_lower = {t for t in tags if isinstance(t, str)}
                if tags_lower & set(query_tokens):
                    score += TAG_BOOST

            # Recency boost
            date_str = chunk.meta.get("created") or chunk.meta.get("date") or ""
            if isinstance(date_str, str) and date_str:
                try:
                    parts = date_str.split("-")
                    created = _date_cls(int(parts[0]), int(parts[1]), int(parts[2]))
                    today = _date_cls.today()
                    days_ago = (today - created).days
                    recency = 1.0 / (1.0 + max(days_ago, 0) / RECENCY_HALF_LIFE)
                    score += recency
                except Exception:
                    pass

            # Frequency boost
            access_entry = access_log.get(chunk.file_path, {})
            access_count = access_entry.get("count", 0)
            if isinstance(access_count, (int, float)):
                score += min(access_count * 0.1, FREQUENCY_BOOST_MAX)

            scored.append((score, ci))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_files = set()

        for score, ci in scored[:max_results]:
            chunk = self._chunks[ci]
            preview = chunk.text
            if len(preview) > 800:
                preview = preview[:800] + "..."
            results.append({
                "file": chunk.file_path,
                "score": round(score, 4),
                "preview": preview,
            })
            if chunk.file_path not in seen_files:
                seen_files.add(chunk.file_path)
                _touch_access(chunk.file_path)

        return results


_INDEX = ChunkIndex(vault_path=VAULT_PATH, ttl=INDEX_TTL)


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


# ─── FILE SEARCH (BM25 delegate) ────────────────────────────────────
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
    """Search vault using BM25 over chunked documents."""
    return _INDEX.search(query, max_results=max_results)


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
        return {
            "result": "",
            "topic": topic,
            "files_searched": 0,
            "notebooklm_url": NOTEBOOKLM_URL or None,
            "score_method": "bm25-chunked",
        }

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
        "notebooklm_url": NOTEBOOKLM_URL or None,
        "score_method": "bm25-chunked",
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
                "chunks_indexed": _INDEX.doc_count,
                "index_age_seconds": _INDEX.index_age,
                "index_ttl": INDEX_TTL,
                "search_engine": "bm25-chunked",
                "bm25_k1": BM25_K1,
                "bm25_b": BM25_B,
                "chunk_size": CHUNK_SIZE,
                "notebooklm_url": NOTEBOOKLM_URL or None,
                "auto_inject_hook": "hooks/brainpass-inject.sh",
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
    print(f"  search=bm25-chunked k1={BM25_K1} b={BM25_B} chunk={CHUNK_SIZE}", file=sys.stderr)

    def graceful_exit(signum, frame):
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
            "search_engine": "bm25-chunked",
            "chunks": _INDEX.doc_count,
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
