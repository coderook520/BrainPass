#!/usr/bin/env bash
# BrainPass Installation Script
#
# Installs BrainPass to ~/BrainPass/ from the cloned repo:
#   - copies src/ and docs/ (always — so you can upgrade via `git pull && ./install.sh`)
#   - copies config/ (only on first install — preserves your edits)
#   - creates a fresh vault skeleton (only if the vault is empty)
#   - creates the .env and SOUL.md live files from templates
#   - writes a systemd --user service so the librarian auto-starts
#
# Safe to re-run. Idempotent on user data.

set -euo pipefail

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="$HOME/BrainPass"

echo "BrainPass Installer"
echo "==================="
echo "source: $REPO_ROOT"
echo "target: $INSTALL_DIR"
echo

# ─── Python check ────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.10 or newer." >&2
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    FOUND=$(python3 --version 2>&1)
    echo "ERROR: Python 3.10+ required. Found: $FOUND" >&2
    exit 1
fi
echo "[ok] $(python3 --version)"

# ─── Target dirs ─────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
mkdir -p "$HOME/.config/systemd/user"

# ─── Copy source (always, so upgrades work) ──────────────────────────
if [ "$REPO_ROOT" != "$INSTALL_DIR" ]; then
    echo "[..] copying src/"
    rm -rf "$INSTALL_DIR/src"
    cp -r "$REPO_ROOT/src" "$INSTALL_DIR/src"
else
    echo "[ok] src/ already in place (repo == install dir)"
fi
chmod +x "$INSTALL_DIR/src/librarian.py"

if [ "$REPO_ROOT" != "$INSTALL_DIR" ]; then
    if [ -d "$REPO_ROOT/docs" ]; then
        echo "[..] copying docs/"
        rm -rf "$INSTALL_DIR/docs"
        cp -r "$REPO_ROOT/docs" "$INSTALL_DIR/docs"
    fi

    if [ -d "$REPO_ROOT/hooks" ]; then
        echo "[..] copying hooks/"
        rm -rf "$INSTALL_DIR/hooks"
        cp -r "$REPO_ROOT/hooks" "$INSTALL_DIR/hooks"
        chmod +x "$INSTALL_DIR/hooks/"*.sh 2>/dev/null || true
    fi
else
    echo "[ok] docs/ and hooks/ already in place (repo == install dir)"
fi

# ─── Copy config (preserve user edits) ───────────────────────────────
if [ ! -d "$INSTALL_DIR/config" ]; then
    echo "[..] copying config/ (first install)"
    cp -r "$REPO_ROOT/config" "$INSTALL_DIR/config"
else
    echo "[ok] config/ already present — keeping your edits"
    if [ "$REPO_ROOT" != "$INSTALL_DIR" ]; then
        cp "$REPO_ROOT/config/.env.example" "$INSTALL_DIR/config/.env.example"
        cp "$REPO_ROOT/config/identity/SOUL.md.template" "$INSTALL_DIR/config/identity/SOUL.md.template"
        cp "$REPO_ROOT/config/identity/MEMORY.md.template" "$INSTALL_DIR/config/identity/MEMORY.md.template"
    fi
fi

# ─── Live .env from template ─────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/config/.env" ]; then
    cp "$INSTALL_DIR/config/.env.example" "$INSTALL_DIR/config/.env"
    echo "[ok] created config/.env — EDIT IT with your API key"
fi

# ─── Live SOUL.md and MEMORY.md from templates ───────────────────────
if [ ! -f "$INSTALL_DIR/config/identity/SOUL.md" ]; then
    cp "$INSTALL_DIR/config/identity/SOUL.md.template" "$INSTALL_DIR/config/identity/SOUL.md"
    echo "[ok] created config/identity/SOUL.md — edit to set your agent's personality"
fi
if [ ! -f "$INSTALL_DIR/config/identity/MEMORY.md" ]; then
    cp "$INSTALL_DIR/config/identity/MEMORY.md.template" "$INSTALL_DIR/config/identity/MEMORY.md"
    echo "[ok] created config/identity/MEMORY.md"
fi

# ─── Vault skeleton ──────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR/vault"/{daily,topics,people,projects,sources}

# If the vault is fresh, seed it with two starter notes so Obsidian opens to something real
if [ ! -f "$INSTALL_DIR/vault/daily/WELCOME.md" ] && [ -f "$REPO_ROOT/vault/daily/EXAMPLE.md" ]; then
    cp "$REPO_ROOT/vault/daily/EXAMPLE.md" "$INSTALL_DIR/vault/daily/WELCOME.md"
fi
if [ ! -f "$INSTALL_DIR/vault/people/EXAMPLE.md" ] && [ -f "$REPO_ROOT/vault/people/EXAMPLE.md" ]; then
    cp "$REPO_ROOT/vault/people/EXAMPLE.md" "$INSTALL_DIR/vault/people/EXAMPLE.md"
fi

# ─── Gate package (bin/, lib/, systemd/) ─────────────────────────────
# The human-session gate stops autonomous callers (cron, buggy loops,
# agent frameworks, supply-chain surprises) from draining your LLM budget.
# Default ON. Set BP_GATE_DISABLED=1 in config/.env to disable (not recommended).
if [ "$REPO_ROOT" != "$INSTALL_DIR" ]; then
    for dir in bin lib systemd tests; do
        if [ -d "$REPO_ROOT/$dir" ]; then
            echo "[..] copying $dir/"
            rm -rf "$INSTALL_DIR/$dir"
            cp -r "$REPO_ROOT/$dir" "$INSTALL_DIR/$dir"
        fi
    done
    chmod +x "$INSTALL_DIR/bin/"* 2>/dev/null || true
fi

# Tracker systemd unit — install the service file, auto-start if available
TRACKER_UNIT="$HOME/.config/systemd/user/human-session-tracker.service"
if [ -f "$INSTALL_DIR/systemd/human-session-tracker.service" ]; then
    sed "s|%h/.local/brainpass/bin/human-session-tracker|$INSTALL_DIR/bin/human-session-tracker|g" \
        "$INSTALL_DIR/systemd/human-session-tracker.service" > "$TRACKER_UNIT"
    echo "[ok] wrote $TRACKER_UNIT"
    if command -v socat >/dev/null 2>&1; then
        echo "[ok] socat present (required for bp-call-librarian)"
    else
        echo "[warn] socat not installed — bp-call-librarian won't work until you install it"
        echo "       (Debian/Ubuntu: sudo apt install socat  |  Arch: sudo pacman -S socat)"
    fi
fi

# ─── systemd --user service ──────────────────────────────────────────
SERVICE_FILE="$HOME/.config/systemd/user/brainpass-librarian.service"
PYTHON_BIN="$(command -v python3)"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=BrainPass Librarian — Agent Memory Service
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
EnvironmentFile=%h/BrainPass/config/.env
ExecStart=$PYTHON_BIN %h/BrainPass/src/librarian.py serve
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

echo "[ok] wrote $SERVICE_FILE"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
    # Enable + start the tracker (the gate depends on it being up)
    if [ -f "$TRACKER_UNIT" ]; then
        systemctl --user enable --now human-session-tracker.service 2>/dev/null \
            && echo "[ok] human-session-tracker started" \
            || echo "[warn] could not auto-start tracker — run: systemctl --user start human-session-tracker"
    fi
else
    echo "[warn] systemctl not found — service file written but not registered"
fi

# ─── Summary ─────────────────────────────────────────────────────────
cat <<EOF

Installed.

Next:
  1. Edit ~/BrainPass/config/.env — set your API key and LLM_PROVIDER
  2. Edit ~/BrainPass/config/identity/SOUL.md — your agent's personality
  3. Start it:
       systemctl --user start brainpass-librarian
       systemctl --user enable brainpass-librarian
  4. Verify:
       curl http://127.0.0.1:7778/status
  5. Wire the auto-inject hook into your AI tool:
       ~/BrainPass/hooks/brainpass-inject.sh
     (See SETUP-WITH-YOUR-AI.md Step 11.5 — this is the piece that
      makes BrainPass fire on every message automatically instead of
      only when your AI remembers to call it.)
  5a. Gate status (default ON — blocks autonomous LLM burn):
       python3 -m unittest discover -s ~/BrainPass/tests -v   # 19 tests
       See ~/BrainPass/docs/gate.md for architecture + disable instructions.
  6. Optional: upload ~/BrainPass/vault/ to https://notebooklm.google.com
     as a new notebook for deeper semantic search, then set
     NOTEBOOKLM_URL in ~/BrainPass/config/.env to the notebook URL.

Obsidian: Open folder as vault → ~/BrainPass/vault/
EOF
