#!/usr/bin/env bash
# BrainPass — end-to-end smoke test.
#
# Creates a temp HOME, installs BrainPass into it, boots the librarian on a
# scratch port, hits /health and /status, and shuts it down. No API key
# required — /recall will return gracefully because the vault is empty of the
# query terms.

set -euo pipefail

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TMP_HOME="$(mktemp -d /tmp/brainpass-test-XXXXXX)"
PORT=17778

cleanup() {
    if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi
    rm -rf "$TMP_HOME"
}
trap cleanup EXIT

echo "[test] temp HOME: $TMP_HOME"
echo "[test] port: $PORT"

# Run installer with HOME overridden so nothing touches the user's real dirs
HOME="$TMP_HOME" bash "$REPO_ROOT/install.sh" > "$TMP_HOME/install.log" 2>&1 || {
    echo "[fail] install.sh exited non-zero"
    cat "$TMP_HOME/install.log"
    exit 1
}
echo "[ok] install.sh ran clean"

# Assert files exist
for f in \
    "$TMP_HOME/BrainPass/src/librarian.py" \
    "$TMP_HOME/BrainPass/config/.env" \
    "$TMP_HOME/BrainPass/config/identity/SOUL.md" \
    "$TMP_HOME/BrainPass/config/identity/MEMORY.md" \
    "$TMP_HOME/BrainPass/vault/daily/WELCOME.md" \
    "$TMP_HOME/.config/systemd/user/brainpass-librarian.service"
do
    if [ ! -f "$f" ]; then
        echo "[fail] missing expected file: $f"
        exit 1
    fi
done
echo "[ok] all expected files present"

# Boot librarian directly (not via systemd — we may be in a container)
HOME="$TMP_HOME" \
LIBRARIAN_PORT="$PORT" \
VAULT_PATH="$TMP_HOME/BrainPass/vault" \
LLM_PROVIDER=groq \
GROQ_API_KEY=fake \
python3 "$TMP_HOME/BrainPass/src/librarian.py" serve &
PID=$!

# Wait for it to bind
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf "http://127.0.0.1:$PORT/health" > /dev/null 2>&1; then
        break
    fi
    sleep 0.3
done

if ! curl -sf "http://127.0.0.1:$PORT/health" > /dev/null; then
    echo "[fail] librarian never came up on port $PORT"
    exit 1
fi
echo "[ok] /health → 200"

STATUS=$(curl -sf "http://127.0.0.1:$PORT/status")
echo "$STATUS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok', d
assert d['llm_provider'] == 'groq', d
assert d['keys_configured'] == 1, d
print('[ok] /status →', json.dumps({k: d[k] for k in ('status','llm_provider','llm_model','files_indexed')}))
"

# /recall with a query that won't match the empty vault
RECALL=$(curl -sf -X POST "http://127.0.0.1:$PORT/recall" \
    -H 'Content-Type: application/json' \
    -d '{"message": "what did I do yesterday", "topic": "nonexistent-topic-xyz"}')

echo "$RECALL" | python3 -c "
import sys, json
d = json.load(sys.stdin)
# either no files found, or skipped (too short/etc). Both are graceful.
assert 'error' not in d or d.get('files_searched') == 0, d
print('[ok] /recall → graceful:', d.get('topic','?'))
"

# Shut down the groq instance before spinning up the anthropic one
kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
PID=""

# ─── Anthropic branch coverage ───────────────────────────────────────
PORT2=17779
HOME="$TMP_HOME" \
LIBRARIAN_PORT="$PORT2" \
VAULT_PATH="$TMP_HOME/BrainPass/vault" \
LLM_PROVIDER=anthropic \
ANTHROPIC_API_KEY=fake \
python3 "$TMP_HOME/BrainPass/src/librarian.py" serve &
PID=$!

for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf "http://127.0.0.1:$PORT2/health" > /dev/null 2>&1; then
        break
    fi
    sleep 0.3
done

if ! curl -sf "http://127.0.0.1:$PORT2/health" > /dev/null; then
    echo "[fail] librarian (anthropic branch) never came up on port $PORT2"
    exit 1
fi

STATUS2=$(curl -sf "http://127.0.0.1:$PORT2/status")
echo "$STATUS2" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok', d
assert d['llm_provider'] == 'anthropic', d
assert d['llm_model'].startswith('claude-'), d
assert d['keys_configured'] == 1, d
print('[ok] /status (anthropic) →', json.dumps({k: d[k] for k in ('llm_provider','llm_model','keys_configured')}))
"

echo
echo "[PASS] all smoke tests green (groq + anthropic branches)"
