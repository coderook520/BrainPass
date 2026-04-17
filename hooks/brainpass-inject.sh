#!/usr/bin/env bash
# BrainPass auto-trigger hook — UserPromptSubmit for Claude Code, Cursor, etc.
#
# Installs as a "UserPromptSubmit" hook in your AI tool. Every time you send a
# message, this fires FIRST: grab your prompt, hit the BrainPass librarian with
# a human-session token, and inject the compiled note context back into the
# conversation before your AI answers.
#
# Without this hook your AI only reads notes when it remembers to call /recall.
# With this hook it reads notes on every single message.
#
# Input (stdin, JSON from the AI tool):
#   {"prompt": "<user text>", ...}
# Output (stdout → injected into the conversation):
#   "BRAINPASS: <compiled context + citations>"
#
# Safe on failure: if the librarian is down OR the gate says no active human
# session, the hook silently exits 0 so the user's message still goes through.

set -euo pipefail

LIBRARIAN_URL="${BRAINPASS_URL:-http://127.0.0.1:7778}"
TIMEOUT="${BRAINPASS_TIMEOUT:-8}"

# Source the gate library — looks for it relative to this script, then falls
# back to the standard install location at ~/BrainPass/lib/.
_BP_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$_BP_HOOK_DIR/../lib/brainpass-gate.sh" ]; then
    source "$_BP_HOOK_DIR/../lib/brainpass-gate.sh"
elif [ -f "$HOME/BrainPass/lib/brainpass-gate.sh" ]; then
    source "$HOME/BrainPass/lib/brainpass-gate.sh"
else
    # No gate library found → behave as if the gate is disabled
    bp_require_human_session() { return 0; }
    bp_get_human_token() { echo ""; }
fi

# Read stdin (whatever the tool gives us)
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# Extract the user prompt. Try common field names used by different tools.
PROMPT=""
if command -v jq >/dev/null 2>&1; then
    PROMPT="$(printf '%s' "$INPUT" | jq -r '
        .prompt // .user_prompt // .message //
        (.messages | if type == "array" then .[-1].content else empty end) //
        empty
    ' 2>/dev/null || true)"
fi
if [ -z "$PROMPT" ]; then PROMPT="$INPUT"; fi

# Trim and sanity-check — skip empty or trivial messages
PROMPT="$(printf '%s' "$PROMPT" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[ -z "$PROMPT" ] && exit 0
[ "${#PROMPT}" -lt 10 ] && exit 0
case "$PROMPT" in /*) exit 0 ;; esac

# Gate check — UserPromptSubmit IS interactive, so the tracker will have a
# fresh flag. If for any reason it's down or missing, skip this hook entirely
# rather than stalling the user's message.
if ! bp_require_human_session 2>/dev/null; then
    exit 0
fi
TOKEN="$(bp_get_human_token 2>/dev/null || echo "")"
# If the gate is disabled at the library level, TOKEN may be empty — that's
# fine, we fall through and call the librarian without the header.

# Fire-and-forget health probe so we fail fast when the librarian is down
if ! curl -s -m 2 -o /dev/null "$LIBRARIAN_URL/health" 2>/dev/null; then
    exit 0
fi

# Build request body
if command -v jq >/dev/null 2>&1; then
    BODY="$(jq -n --arg m "$PROMPT" --arg t "$PROMPT" '{message: $m, topic: $t}')"
else
    ESC="$(printf '%s' "$PROMPT" | tr -d '\000-\037' | sed 's/\\/\\\\/g; s/"/\\"/g')"
    BODY="{\"message\":\"$ESC\",\"topic\":\"$ESC\"}"
fi

# Call the librarian — add the gate header if we have a token
if [ -n "$TOKEN" ]; then
    RESPONSE="$(curl -s -m "$TIMEOUT" -X POST "$LIBRARIAN_URL/recall" \
        -H 'Content-Type: application/json' \
        -H "X-Human-Session-Token: $TOKEN" \
        -d "$BODY" 2>/dev/null || true)"
else
    RESPONSE="$(curl -s -m "$TIMEOUT" -X POST "$LIBRARIAN_URL/recall" \
        -H 'Content-Type: application/json' \
        -d "$BODY" 2>/dev/null || true)"
fi

[ -z "$RESPONSE" ] && exit 0

# Parse the response — need both result and sources
if command -v jq >/dev/null 2>&1; then
    RESULT="$(printf '%s' "$RESPONSE" | jq -r '.result // empty' 2>/dev/null || true)"
    SOURCES="$(printf '%s' "$RESPONSE" | jq -r '.sources // [] | join(", ")' 2>/dev/null || true)"
    SKIPPED="$(printf '%s' "$RESPONSE" | jq -r '.skipped // false' 2>/dev/null || echo false)"
    NOTEBOOKLM="$(printf '%s' "$RESPONSE" | jq -r '.notebooklm_url // empty' 2>/dev/null || true)"
else
    RESULT="$RESPONSE"; SOURCES=""; SKIPPED="false"; NOTEBOOKLM=""
fi

[ "$SKIPPED" = "true" ] && exit 0
[ -z "$RESULT" ] && exit 0

# Output — whatever we print here is injected into the conversation before the AI responds
printf 'BRAINPASS memory for this message:\n%s\n' "$RESULT"
[ -n "$SOURCES" ] && printf '\nSources: %s\n' "$SOURCES"
[ -n "$NOTEBOOKLM" ] && printf '\nDeeper semantic search available at: %s\n' "$NOTEBOOKLM"

exit 0
