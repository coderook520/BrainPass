# Brain v3 — The Self-Feeding Brain

**What v3 adds:** four features that close the loop between you, your AI, your vault, and the open web.

| Feature | What it does |
|---|---|
| Write-back | AI responses get parsed for save-worthy facts. Proposals queue up. One-tap approve → it's in the vault forever. |
| Temporal awareness | Recent notes outrank old ones (exponential decay). `/changed` surfaces what moved. `/timeline?topic=X` shows the chronological fact evolution. |
| Self-teaching vault | Every recall logs which notes were surfaced. Over time you know your *hot* notes (constantly retrieved) vs. *dead* notes (never touched). |
| Auto-research | **Default ON.** When the vault returns fewer than 2 hits, the librarian fetches from Wikipedia, arXiv, DuckDuckGo (+ optional open web), synthesizes with LLM, and enqueues the findings via write-back. Next time you ask, it's already in your vault. |

Combined, these turn BrainPass from a read-only memory system into a **self-feeding brain**: the vault grows on revealed preference (topics you actually ask about) without you typing a note.

## Flow (default mode)

```
you → "what's the deal with vector databases?"
        │
        ▼
  /recall → vault search (50ms)
        │
        ├─→ vault returned 0 notes
        │     │
        │     ▼
        │   auto-research fires (3s inline budget)
        │   ├─ fetches Wikipedia summary + arXiv abstracts + DDG instant answer
        │   ├─ sanitizes (HTML-strip + injection-pattern redact + envelope-wrap)
        │   ├─ synthesizes a cited answer
        │   └─ enqueues a note-draft for your approval
        │
        ▼
  your AI receives:
    - vault compile (if any)
    - auto_research answer + citations
    - cost snapshot (today, this week)
  your AI responds to you

meanwhile in the background:
  - analytics records what got surfaced (scrubbed for credentials + PII)
  - writeback extractor parses the conversation turn for save-worthy facts

you:  bp-write review
      → approve the auto-research draft + any extracted facts
      → they're in your vault now. Next time the topic comes up, zero research cost.
```

## Security story

Every new surface is locked down:

| Risk | Defense |
|---|---|
| Prompt injection via fetched pages | HTML parsing + injection-pattern redaction + unforgeable XML envelope (body is `html.escape`-ed so `<` and `>` cannot close the envelope regardless of payload) |
| SSRF to localhost / 10.x / 192.168.x / IPv6 ULA | CIDR blocklist via `ipaddress.ip_network`; **all** getaddrinfo records must be non-private (closes multi-A DNS rebinding); post-connect `getpeername()` verification |
| Cost DoS via unbounded research | Hard 3s inline budget + 30s total deadline (monotonic clock); optional `BP_AUTORESEARCH_HARD_CAP_USD` |
| Future exceptions crashing /recall | All research exceptions caught; shape-stable error dict returned; /recall never raises from research |
| Credential/PII leakage in logs | `scrub_keys.scrub_str` before every write; optional `BP_PII_SCRUB_FILE` with ownership + structural ReDoS pre-filter |
| Parser-differential path bypass | Single `normalize_request_path` (unquote + posixpath.normpath; any discrepancy → 400). Gate, router, fall-through all use it. |
| Unbounded executor queue OOM | `MAX_QUEUE_DEPTH=10`, returns "backpressured" on saturation |
| Disk-full JSONL appends | `safe_append_jsonl` with 100MB free-space pre-check + rate-limited warnings |
| Writeback sanitizer injection | Front-matter injection stripped, atomic `.tmp` + rename with O_NOFOLLOW |

## Configuration

All defaults are sane. Change any of these in `config/.env`:

```bash
# Write-back
BP_WRITEBACK_ENABLED=true
BP_WRITE_MODE=confirm            # confirm | auto | suggest | off
BP_WRITE_CONFIDENCE_AUTO=0.85
BP_WRITE_QUEUE_TTL_DAYS=14

# Temporal
BP_TEMPORAL_ENABLED=true
BP_TEMPORAL_HALF_LIFE_DAYS=30

# Analytics
BP_ANALYTICS_ENABLED=true
BP_PII_SCRUB_FILE=                # optional: path to regex list (mode 0600, owned by you)

# Auto-research
BP_AUTORESEARCH_ENABLED=true      # master switch (DEFAULT ON)
BP_AUTORESEARCH_MODE=smart        # smart | always | off | explicit
BP_AUTORESEARCH_THRESHOLD=2       # min vault hits to suppress research
BP_AUTORESEARCH_WHITELIST_ONLY=false
BP_AUTORESEARCH_WHITELIST=wikipedia.org,arxiv.org,duckduckgo.com
BP_AUTORESEARCH_INLINE_BUDGET_SECONDS=3.0
BP_AUTORESEARCH_TIMEOUT_TOTAL=30
BP_AUTORESEARCH_WARN_DAILY_USD=5.00
BP_AUTORESEARCH_HARD_CAP_USD=     # unset = uncapped
```

## New endpoints (all gated by the PR #1 human-session gate)

| Method | Path | Feature |
|---|---|---|
| GET  | `/write-queue` | list pending write-back proposals |
| POST | `/write-queue/{id}/approve` | commit proposal to vault |
| POST | `/write-queue/{id}/reject` | discard proposal |
| GET  | `/changed?since=<iso>` | files modified since timestamp |
| GET  | `/timeline?topic=<slug>` | chronological fact evolution for topic |
| GET  | `/analytics/hot-notes?days=N` | most-retrieved notes |
| GET  | `/analytics/dead-notes?days=N` | notes never retrieved in window |
| GET  | `/analytics/query-patterns?days=N` | common query topic words |

## New CLIs (in `bin/`)

- `bp-write review` — interactive walk through pending write-back proposals
- `bp-write list` — JSON list of pending proposals
- `bp-write purge [days]` — expire stale pending proposals
- `bp-analytics report` — one-shot "how's my brain doing" summary
- `bp-analytics {hot,dead,patterns} [days]` — individual views
- `bp-research status` — is research enabled, ready, what's today's cost?
- `bp-research cost` — JSON of 24h + 7d totals
- `bp-research run <query>` — manual research trigger (forces explicit fire)

## Disable any module individually

```bash
BP_WRITEBACK_ENABLED=false
BP_TEMPORAL_ENABLED=false
BP_ANALYTICS_ENABLED=false
BP_AUTORESEARCH_ENABLED=false
```

Each module is an independent optional import in `librarian.py`. If one is off, the others still work. If one crashes at load time, the librarian logs a warning and continues without that feature.

## Soft-required dependency

`beautifulsoup4` is soft-required for auto-research (clean HTML parsing). If absent, `module_ready()` returns False and auto-research stays disabled. `install.sh` attempts `pip install --user beautifulsoup4` opportunistically.

## Testing

```bash
cd ~/BrainPass
python3 -m unittest discover -s tests -v
```

Expected: 84 tests, all pass. Coverage includes the four CRITICAL defenses from the Phase 1 + Phase 2 design review:
- Envelope unforgeability (prompt injection)
- SSRF CIDR blocklist + IP rejection
- Future exception containment (/recall never raises from research)
- Path normalization (traversal / double-slash / percent-encode rejected)

See `docs/gate.md` for the PR #1 auth gate that protects all v3 endpoints.
