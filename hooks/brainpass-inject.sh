#!/usr/bin/env bash
# BrainPass auto-trigger hook — UserPromptSubmit for Claude Code, Cursor, etc.
#
# Installs as a "UserPromptSubmit" hook in your AI coding tool. Every time
# you send a message, this fires FIRST: it grabs your prompt, hits the
# BrainPass librarian, and injects the compiled note context back into the
# conversation before your AI answers.
#
# This is the piece that makes BrainPass automatic instead of pull-based.
# Without this hook, your AI only reads notes when it remembers to call
# /recall. With this hook, it reads notes on every single message.
#
# Input (stdin, JSON from the AI tool):
#   {"prompt": "<user text>", ...}
# Output (stdout → injected into the conversation):
#   "BRAINPASS: <compiled context + citations>"
#
# Safe on failure: if the librarian is down, the hook silently exits 0 so
# the user's message still goes through normally.

set -euo pipefail

LIBRARIAN_URL="${BRAINPASS_URL:-http://127.0.0.1:7778}"
TIMEOUT="${BRAINPASS_TIMEOUT:-8}"

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

# Fallback: if jq isn't here or the JSON shape is unknown, treat stdin as plain text
if [ -z "$PROMPT" ]; then
    PROMPT="$INPUT"
fi

# Trim and sanity-check — skip empty or trivial messages
PROMPT="$(printf '%s' "$PROMPT" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[ -z "$PROMPT" ] && exit 0
[ "${#PROMPT}" -lt 10 ] && exit 0

# Skip command-style messages (/help, /reset, etc.)
case "$PROMPT" in
    /*) exit 0 ;;
esac

# Fire-and-forget health probe so we fail fast when the librarian is down
if ! curl -s -m 2 -o /dev/null "$LIBRARIAN_URL/health" 2>/dev/null; then
    exit 0
fi

# Build request body
if command -v jq >/dev/null 2>&1; then
    BODY="$(jq -n --arg m "$PROMPT" --arg t "$PROMPT" '{message: $m, topic: $t}')"
else
    # minimal JSON escaping fallback — strip control chars and quote
    ESC="$(printf '%s' "$PROMPT" | tr -d '\000-\037' | sed 's/\\/\\\\/g; s/"/\\"/g')"
    BODY="{\"message\":\"$ESC\",\"topic\":\"$ESC\"}"
fi

# Call the librarian's recall endpoint
RESPONSE="$(curl -s -m "$TIMEOUT" -X POST "$LIBRARIAN_URL/recall" \
    -H 'Content-Type: application/json' \
    -d "$BODY" 2>/dev/null || true)"

[ -z "$RESPONSE" ] && exit 0

# Parse the response — need both result and sources
if command -v jq >/dev/null 2>&1; then
    RESULT="$(printf '%s' "$RESPONSE" | jq -r '.result // empty' 2>/dev/null || true)"
    SOURCES="$(printf '%s' "$RESPONSE" | jq -r '.sources // [] | join(", ")' 2>/dev/null || true)"
    SKIPPED="$(printf '%s' "$RESPONSE" | jq -r '.skipped // false' 2>/dev/null || echo false)"
    NOTEBOOKLM="$(printf '%s' "$RESPONSE" | jq -r '.notebooklm_url // empty' 2>/dev/null || true)"
else
    RESULT="$RESPONSE"
    SOURCES=""
    SKIPPED="false"
    NOTEBOOKLM=""
fi

[ "$SKIPPED" = "true" ] && exit 0
[ -z "$RESULT" ] && exit 0

# Output — whatever we print here is injected into the conversation before the AI responds
printf 'BRAINPASS memory for this message:\n%s\n' "$RESULT"
[ -n "$SOURCES" ] && printf '\nSources: %s\n' "$SOURCES"
[ -n "$NOTEBOOKLM" ] && printf '\nDeeper semantic search available at: %s\n' "$NOTEBOOKLM"

exit 0
