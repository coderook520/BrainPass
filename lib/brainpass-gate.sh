#!/usr/bin/env bash
# brainpass-gate.sh — source this in any script that should skip cleanly
# when there's no active human session driving the AI CLI.
#
# Usage:
#   source /path/to/brainpass/lib/brainpass-gate.sh
#   bp_require_human_session || exit 0
#
# Return codes from bp_require_human_session:
#   0 — human session active, proceed
#   1 — no human session (silently skip)
#   2 — tracker down (skip + log)

bp_require_human_session() {
    local run_dir uid flag sock age now
    uid=$(id -u)
    run_dir="${XDG_RUNTIME_DIR:-/run/user/$uid}"
    flag="$run_dir/bp-human-session.active"
    sock="$run_dir/bp-human-session.sock"
    if [ ! -S "$sock" ]; then
        return 2
    fi
    if [ ! -f "$flag" ]; then
        return 1
    fi
    now=$(date +%s)
    age=$(( now - $(stat -c %Y "$flag" 2>/dev/null || echo 0) ))
    if [ "$age" -ge 60 ]; then
        return 1
    fi
    return 0
}

bp_get_human_token() {
    local run_dir sock
    run_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    sock="$run_dir/bp-human-session.sock"
    [ -S "$sock" ] || { echo ""; return 2; }
    printf 'GETTOKEN\n' | socat -t 2 - "UNIX-CONNECT:$sock" 2>/dev/null | head -1
}

# Convenience one-shot — source, then:  bp_skip_if_no_human "my-script-name"
bp_skip_if_no_human() {
    local tag="${1:-gated-script}" log_dir
    if bp_require_human_session; then
        return 0
    fi
    log_dir="$HOME/.local/state/brainpass"
    mkdir -p "$log_dir" 2>/dev/null || true
    printf '[%s] %s skipped\n' "$(date -Iseconds)" "$tag" \
        >> "$log_dir/skipped.log" 2>/dev/null || true
    exit 0
}
