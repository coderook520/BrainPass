# Human Session Gate

**Default ON.** Stops autonomous callers from draining your LLM API budget.

## Why this exists

The BrainPass librarian listens on `127.0.0.1:7778` with **no authentication**. Any local process — a cron job, a test loop, an IDE autocomplete, an agent framework spawning background workers, or a supply-chain compromise — can hit `/recall` and drain your Groq/OpenAI/Anthropic budget.

Without the gate, your API key bleeds 24/7 whether you're at the keyboard or not.

With the gate, `/recall` only answers when an AI CLI (claude, cursor, gemini, windsurf, aider, etc.) is actively running under your user with a real TTY attached. Everything else gets `403`.

## Architecture

```
┌─────────────────────────┐        ┌───────────────────────────┐
│ You type in claude CLI  │        │ Cron / agent / loop fires │
│ (real TTY, visible to   │        │ POST to /recall           │
│  pgrep)                 │        │                           │
└────────────┬────────────┘        └────────────┬──────────────┘
             │                                  │
             ▼                                  ▼
   ┌──────────────────┐              ┌──────────────────────┐
   │ human-session-   │              │ librarian's gate     │
   │ tracker daemon   │              │ sees no valid token  │
   │ (pgrep every 10s)│              │ → 403                │
   └────────┬─────────┘              └──────────────────────┘
            │ touches
            ▼
  /run/user/$UID/bp-human-session.active   (mtime<60s = fresh)
  /run/user/$UID/bp-human-session.secret   (32 random bytes, per-boot)
  /run/user/$UID/bp-human-session.sock     (tracker serves HMAC tickets)
            │ "GETTOKEN\n" → ticket
            ▼
   ┌────────────────────────────────┐
   │ Hook curls /recall with        │
   │ X-Human-Session-Token: <ticket>│
   └────────┬───────────────────────┘
            │
            ▼
  ┌──────────────────────────────────────────┐
  │ HumanSessionGateMixin.do_POST / do_GET:  │
  │  1. open-path? → pass                    │
  │  2. gated-path + bad token → 403         │
  │  3. gated-path + valid token → pass      │
  │  → calls _do_POST_orig / _do_GET_orig    │
  └──────────────────────────────────────────┘
```

## Ticket format

- Payload: `<issuer_pid>:<issued_unix_ts>:<expires_unix_ts>`
- Token: `base64url(payload) + "." + sha256_hmac_hex`
- HMAC signed with a 32-byte secret regenerated on tracker start (per-boot)
- Default TTL: 30s. Clock skew tolerance: 2s.

A leaked ticket is useful for at most `TTL + server-side cache` ≈ 35s. After that it's invalid, and the secret rotates on every tracker restart.

## Files

| Path | Role |
|---|---|
| `src/bp_gate/gate_mixin.py` | The MRO mixin — core gate logic |
| `src/bp_gate/scrub_keys.py` | Credential scrubber for logs |
| `bin/human-session-tracker` | Notify daemon — watches for AI CLIs, issues tickets |
| `bin/bp-call-librarian` | Curl wrapper — fetches token, adds header |
| `lib/brainpass-gate.sh` | Bash helpers for scripts: `bp_require_human_session`, `bp_get_human_token` |
| `systemd/human-session-tracker.service` | Type=notify, WatchdogSec=30, StartLimitIntervalSec=0 (survives crash loops) |
| `hooks/brainpass-inject.sh` | Default hook — already gated |

## How the librarian picks up the gate

Two edits to `src/librarian.py` (both already committed in this branch):

1. **Import block** before `class LibrarianHandler`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
   if os.environ.get("BP_GATE_DISABLED") == "1":
       class HumanSessionGateMixin: pass
       GATED_POST = GATED_GET = OPEN_ALWAYS = set()
   else:
       from bp_gate.gate_mixin import HumanSessionGateMixin, GATED_POST, GATED_GET, OPEN_ALWAYS
       GATED_POST.update({"/recall"})
       GATED_GET.update({"/query", "/dreams", "/predictions"})
       OPEN_ALWAYS.update({"/health", "/status", "/clear-cache"})
   ```

2. **Class declaration + method rename:**
   ```python
   class LibrarianHandler(HumanSessionGateMixin, BaseHTTPRequestHandler):
       def _do_GET_orig(self): ...   # was do_GET
       def _do_POST_orig(self): ...  # was do_POST
   ```

The mixin's `do_POST`/`do_GET` run the gate check, then call the renamed originals only on pass.

## Which endpoints are gated

| Endpoint | Method | Gated? | Why |
|---|---|---|---|
| `/recall` | POST | **YES** | Calls your LLM — main burn surface |
| `/query` | GET | **YES** | Calls your LLM |
| `/dreams` | GET | **YES** | Calls your LLM |
| `/predictions` | GET | **YES** | Calls your LLM |
| `/health` | GET | no | Static status probe |
| `/status` | GET | no | Static status probe |
| `/clear-cache` | POST | no | Local filesystem op |

Non-gated endpoints ship empty-headed with no LLM call, so there's nothing to burn.

## Disable (not recommended)

Add to `config/.env`:
```
BP_GATE_DISABLED=1
```
Then `systemctl --user restart brainpass-librarian`.

The `BrainpassInjectHook` and `bp-call-librarian` still work with the gate disabled — they just pass requests through without a header.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `BP_GATE_DISABLED` | unset | Set to `1` to bypass the gate |
| `BP_INTERACTIVE_PROCS` | `claude\|cursor\|gemini\|windsurf\|aider\|continue\|cline\|cody\|copilot` | Regex of AI CLI process names to watch for |
| `BP_TICKET_TTL` | `30` | Ticket lifetime (seconds) |
| `BP_POLL_INTERVAL` | `10` | Tracker poll interval (seconds) |
| `BP_AUDIT_LOG` | `~/.local/state/brainpass/gate.jsonl` | Where gate decisions are logged |

## Observability

Every gate decision is logged as JSONL:
```bash
tail -f ~/.local/state/brainpass/gate.jsonl | jq '.'
```

Example record:
```json
{
  "ts": "2026-04-17T17:50:55Z",
  "event": "gate_decision",
  "human_session_verified": false,
  "method": "POST",
  "path": "/recall",
  "caller_addr": "127.0.0.1"
}
```

## Verification

Run the 19-test suite:
```bash
python3 -m unittest discover -s tests -v
```

Manually probe a blocked request:
```bash
# Background (no token) — MUST return 403
curl -sS -o /dev/null -w '%{http_code}\n' \
    -X POST http://127.0.0.1:7778/recall \
    -H 'Content-Type: application/json' \
    -d '{"message":"test"}'
```

With a valid token via the wrapper:
```bash
bp-call-librarian http://127.0.0.1:7778/recall \
    -X POST -H 'Content-Type: application/json' \
    -d '{"message":"test"}'
```

## Troubleshooting

**"human-session tracker offline" (503):**
Tracker isn't running. `systemctl --user status human-session-tracker`, then `systemctl --user start human-session-tracker`.

**"invalid human-session token" (403):**
Either you sent no token, or the token was HMAC-signed by a different secret (e.g. tracker restarted between ticket issue and request). Get a fresh token with `bp-call-librarian`.

**"no fresh human session" (403):**
Tracker can't find an AI CLI process with a TTY. Add your CLI's name to `BP_INTERACTIVE_PROCS` regex and restart the tracker.

**Hook doesn't fire at all:**
Check `~/.local/state/brainpass/gate.jsonl` for records — if empty, the hook isn't reaching the librarian. Verify `BRAINPASS_URL` in the hook matches where your librarian listens.
