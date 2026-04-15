# BrainPass — Installation Guide

The README has the short version. This is the long one with every edge case.

## Prerequisites

- **Python 3.10 or newer** — `python3 --version` to check
- **Obsidian** — [obsidian.md](https://obsidian.md) (free)
- **An LLM API key** — Groq (free tier), OpenAI, Anthropic, or a local model
- **systemd --user** — standard on every modern Linux distro, and on macOS you
  can run the librarian under launchd or just start it in a terminal

## Install

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
./install.sh
```

That's it. The installer:

1. Verifies your Python version is ≥ 3.10
2. Creates `~/BrainPass/` and copies `src/`, `docs/`, and `config/` into it
3. Copies `config/.env.example` → `config/.env` (only if missing)
4. Copies `config/identity/SOUL.md.template` → `SOUL.md` (only if missing)
5. Copies `config/identity/MEMORY.md.template` → `MEMORY.md` (only if missing)
6. Creates the vault skeleton (`vault/{daily,topics,people,projects,sources}`)
7. Seeds two starter notes in the vault if it's fresh
8. Writes `~/.config/systemd/user/brainpass-librarian.service`
9. Reloads systemd --user

Safe to re-run. Your `.env` and `SOUL.md` are preserved; `src/` and `docs/` get
re-copied so `git pull && ./install.sh` is a valid upgrade flow.

## Configure

### 1. API key

Open `~/BrainPass/config/.env`. Pick one provider, paste the key:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
GROQ_MODEL=openai/gpt-oss-120b
```

Other provider blocks in the same file: `OPENAI_API_KEY` / `OPENAI_MODEL`,
`ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`, or `LOCAL_LLM_URL` / `LOCAL_LLM_MODEL`.
Set `LLM_PROVIDER` to match the block you filled in.

### 2. Agent personality

Edit `~/BrainPass/config/identity/SOUL.md`. This is the system prompt your
agent reads on every recall. Describe who it is, how it talks, and what it
should know about you.

## Start

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian  # auto-start on boot
```

## Verify

```bash
curl http://127.0.0.1:7778/status
```

Expected output:

```json
{
  "status": "ok",
  "vault_path": "/home/you/BrainPass/vault",
  "port": 7778,
  "llm_provider": "groq",
  "llm_model": "openai/gpt-oss-120b",
  "keys_configured": 1,
  "files_indexed": 2
}
```

## Connect Obsidian

1. Launch Obsidian
2. **Open folder as vault** → pick `~/BrainPass/vault/`
3. You'll see the starter notes in `daily/` and `people/`
4. Start writing. The librarian will find your notes automatically.

## Connect your AI

Installing isn't enough — you still have to tell your AI that BrainPass exists.
See `docs/AGENT_INTEGRATION.md` for the copy-paste system prompt and per-tool
placement.

## Troubleshooting

**Service won't start.** Check the logs:
```bash
journalctl --user -u brainpass-librarian -n 100 --no-pager
```
Most common cause: missing or empty `LLM_PROVIDER`-specific API key in `.env`.

**Port in use.** Change `LIBRARIAN_PORT` in `~/BrainPass/config/.env`, then
`systemctl --user restart brainpass-librarian`.

**`curl /status` says keys_configured: 0.** You set the wrong env var for the
provider you chose. Example: `LLM_PROVIDER=openai` but you filled `GROQ_API_KEY`.
Fix the `.env` and restart.

**Wrong Python.** If `python3 --version` shows < 3.10, install a newer Python
first. On Ubuntu: `sudo apt install python3.11`.

**macOS, no systemd.** Skip `systemctl` and run manually:
```bash
python3 ~/BrainPass/src/librarian.py serve
```
Or write a launchd plist in `~/Library/LaunchAgents/`.

## Uninstall

```bash
systemctl --user stop brainpass-librarian
systemctl --user disable brainpass-librarian
rm ~/.config/systemd/user/brainpass-librarian.service
systemctl --user daemon-reload
rm -rf ~/BrainPass
```

Your vault dies with that `rm -rf` — back it up first if you care.
