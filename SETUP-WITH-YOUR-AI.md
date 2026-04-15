# BrainPass — setup instructions for the user's AI

> **Hey AI reading this.** The user handed you the BrainPass repo and said some version of *"install this for me."* This file is your runbook. Read the whole thing once, then start the conversation with the user as described below. **Follow it in order. One question at a time. Wait for answers. Do not dump steps.**

---

## 0. What BrainPass is (your mental model before you explain it)

BrainPass is a tiny local service that gives you — the AI — persistent memory.

The architecture is three pieces:

1. **An Obsidian vault** on the user's disk at `~/BrainPass/vault/` — a folder of plain markdown notes the user writes (daily logs, people, projects, topics, sources).
2. **A Python HTTP service** called the "librarian" running on `127.0.0.1:7778`. It's ~400 lines of stdlib Python, no dependencies, lives at `~/BrainPass/src/librarian.py`. On every `POST /recall` call, it searches the vault by keyword, picks the top 5 matching files, stuffs them into a system prompt, and calls a small "runner" LLM to compile a citeable answer.
3. **A "runner" LLM** that the librarian calls. This is a *different* LLM from you. Its only job is to look at retrieved notes and compile an answer with citations. The user picks it in step 6 below. Cheap/fast models are fine — `openai/gpt-oss-120b` on Groq's free tier is the default recommendation and plenty strong for retrieval compilation.

**Your role in the final setup:** after installation, the user will paste a "magic instruction" block into your system prompt / CLAUDE.md / custom instructions. From then on, before you answer anything about the user personally, you'll hit `POST http://127.0.0.1:7778/recall` yourself and read the compiled notes before speaking. That's the whole point — you gain persistent memory without any training or fine-tuning.

**Critical distinction:** BrainPass is NOT you. BrainPass is the plumbing that lets you read the user's notes. The user's vault is the memory. The runner LLM is the compiler. You are the presenter. Don't confuse the roles when you explain this.

---

## 1. What you need to get from the user (only 4 real decisions)

1. **Platform** — Linux / Mac / Windows+WSL
2. **What they already have** — Obsidian installed? Python 3.10+ available? systemd --user working?
3. **Which LLM to run as the librarian's runner** — Groq (recommended), OpenAI key, Anthropic key, or local Ollama
4. **Their personality / preferences** — one sentence is fine, goes into `SOUL.md`

Everything else you can figure out yourself from reading the repo.

---

## 2. The conversation — follow these steps in order

### Step 1 — open with this exact message

> "I just read the BrainPass repo. I can install it on your machine in about 10 minutes, and when we're done I'll have persistent memory — I'll start reading notes from your Obsidian vault before answering anything about you, so I stop forgetting everything between sessions. Ready to go?"

Wait for yes. If they want to know what it is first, give them the 3-piece mental model from section 0 above in plain language — don't dump the whole runbook.

### Step 2 — platform check

Ask: *"What are you on — Linux, Mac, or Windows?"*

- **Linux** → perfect, systemd will work
- **Mac** → fine, but note that systemd isn't native. You'll start the librarian manually later. Tell the user now so they're not surprised.
- **Windows** → ask if they have WSL (Windows Subsystem for Linux) installed. If no, tell them they need WSL first. Point them at `wsl --install` in PowerShell as admin. BrainPass doesn't work on bare Windows.

### Step 3 — Python check

Run: `python3 --version`

Needs **3.10 or newer**. If missing or older:

- **Linux (Debian/Ubuntu)**: `sudo apt install python3.11`
- **Linux (Arch)**: `sudo pacman -S python`
- **Mac**: `brew install python@3.11`
- **WSL**: same as Linux above

Don't proceed until `python3 --version` reports ≥ 3.10.

### Step 4 — Obsidian check

Ask: *"Do you already have Obsidian installed?"*

- If yes → continue
- If no → tell them to download from https://obsidian.md (free, no account needed). Wait for them to confirm it's installed before moving on.

Don't run Obsidian yet. That's step 10.

### Step 5 — run the installer

From the repo root (wherever the user cloned BrainPass), run:

```bash
./install.sh
```

Show them the output. It should end with `Installed.` and a list of next steps.

What it just created:

- `~/BrainPass/src/librarian.py` — the service
- `~/BrainPass/config/.env` — API key config (currently has placeholder values)
- `~/BrainPass/config/identity/SOUL.md` — agent personality (currently the template)
- `~/BrainPass/config/identity/MEMORY.md` — job manual for the librarian
- `~/BrainPass/vault/{daily,topics,people,projects,sources}/` — empty Obsidian folders
- `~/BrainPass/vault/daily/WELCOME.md` + `~/BrainPass/vault/people/EXAMPLE.md` — starter notes
- `~/.config/systemd/user/brainpass-librarian.service` — systemd unit

If `./install.sh` errors, read the error, fix it, and retry. Common causes: wrong Python version (step 3), missing write permission on `~/`, or a stale `~/BrainPass/` from a previous attempt.

### Step 6 — pick an LLM for the librarian

Say this to the user:

> "BrainPass needs a small 'runner' LLM to sit behind the librarian. Its only job is to read your notes and compile a cited answer before handing it back to me. You have three options:
>
> **1. Groq (recommended — free tier, fastest to start).** Sign up at https://console.groq.com, grab an API key in about 30 seconds, we'll use `openai/gpt-oss-120b`. Free tier gives you thousands of requests per day. This is what I recommend unless you already have something else set up.
>
> **2. An API key you already own.** If you already pay for OpenAI or Anthropic, paste the key and I'll configure it. We'll use `gpt-4o` for OpenAI or `claude-3-5-sonnet-latest` for Anthropic.
>
> **3. A local model (Ollama).** If you already have Ollama running, I can point the librarian at it and nothing ever leaves your machine.
>
> Which do you want?"

Wait for their answer. Then:

- **Groq** → tell them to go to https://console.groq.com/keys, sign up (email + Google works), create a key, paste it back here. Then edit `~/BrainPass/config/.env`:

  ```
  LLM_PROVIDER=groq
  GROQ_API_KEY=gsk_<paste_here>
  GROQ_MODEL=openai/gpt-oss-120b
  ```

- **OpenAI** → ask for the key (starts with `sk-`). Then edit `.env`:

  ```
  LLM_PROVIDER=openai
  OPENAI_API_KEY=sk-<paste_here>
  OPENAI_MODEL=gpt-4o
  ```

- **Anthropic** → ask for the key (starts with `sk-ant-`). Then edit `.env`:

  ```
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=sk-ant-<paste_here>
  ANTHROPIC_MODEL=claude-3-5-sonnet-latest
  ```

- **Ollama** → check first that Ollama is running: `curl http://localhost:11434/api/tags`. If it errors, tell the user to run `ollama serve` in another terminal first. Then ask which model they have pulled (e.g. `llama3.1`). Edit `.env`:

  ```
  LLM_PROVIDER=local
  LOCAL_LLM_URL=http://localhost:11434/v1/chat/completions
  LOCAL_LLM_MODEL=<their_model>
  ```

**Never paste the API key into chat history they can't delete.** If your tool captures conversation logs, remind the user the key is in their `.env` now and they should rotate it if they share this chat.

### Step 7 — write their SOUL.md

Ask: *"Give me a one-liner on how you want me to talk to you. Casual? Formal? Any pet peeves? Anything I should always know about you?"*

Take their exact words and write `~/BrainPass/config/identity/SOUL.md` — replace the template content with:

```markdown
# My Agent

<the user's one-liner about tone, verbatim>

## About Me
- <anything they said about themselves>

## Core Rules
1. Always check BrainPass memory before answering about me
2. Cite sources with [1], [2], etc.
3. Never make up answers — if memory is empty, say so
```

Keep it short. This file is loaded on every recall, so it pays to be tight.

### Step 8 — start the librarian

**Linux or WSL:**
```bash
systemctl --user daemon-reload
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian
```

If `systemctl --user` errors with "Failed to connect to bus", run `loginctl enable-linger $USER` once, then try again.

**Mac (no systemd):** run the librarian manually and tell the user it'll only stay alive as long as the terminal is open (they can write a launchd plist later if they want autostart):

```bash
python3 ~/BrainPass/src/librarian.py serve &
```

### Step 9 — verify it's alive

```bash
curl http://127.0.0.1:7778/status
```

You should see something like:

```json
{
  "status": "ok",
  "vault_path": "/home/user/BrainPass/vault",
  "port": 7778,
  "llm_provider": "groq",
  "llm_model": "openai/gpt-oss-120b",
  "keys_configured": 1,
  "files_indexed": 2
}
```

Confirm out loud to the user:
- `status: ok` — service is up
- `keys_configured: 1` — the API key they pasted is loaded
- `llm_provider` matches what they picked
- `files_indexed` ≥ 2 — the starter notes are there

If `keys_configured` is 0 → the `.env` edit didn't land. Re-check the file, restart with `systemctl --user restart brainpass-librarian`.

If the curl itself fails → the service didn't start. Check `journalctl --user -u brainpass-librarian -n 50 --no-pager` and fix whatever's broken.

### Step 10 — open the vault in Obsidian

Tell the user:

> "Open Obsidian. Click **Open folder as vault** → pick `~/BrainPass/vault/`. You'll see starter notes in `daily/` and `people/` — those are mine, you can delete them once you get the pattern."

Wait for them to confirm Obsidian is pointing at the vault.

### Step 11 — wire YOURSELF into BrainPass (the step most people skip)

Tell the user:

> "Last piece. I need to add an instruction to my own system prompt so that from now on I always check BrainPass before answering anything about you. Where you paste this depends on how you're talking to me right now:"

Then based on what tool they're using:

- **Claude Code** → append the block below to `CLAUDE.md` in their repo root (or `~/.claude/CLAUDE.md` for global)
- **Claude Desktop** → Settings → Profile → "What should Claude know about you?"
- **ChatGPT** → Settings → Personalization → Custom Instructions → "How would you like ChatGPT to respond?"
- **Cursor** → Cursor Settings → Rules for AI
- **Warp** → Settings → AI → System Prompt
- **Open WebUI / Ollama frontend** → System Prompt field on the current model

Give them this exact block to paste:

```
You have access to a persistent memory system called BrainPass running at
http://127.0.0.1:7778. It stores my notes, preferences, projects, and past
conversations as markdown files in an Obsidian vault.

BEFORE answering any question about me, my work, my preferences, or
anything we've discussed previously, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<my question>", "topic": "<main topic>"}

Read the returned notes and answer using them as source of truth. Always
cite which file(s) you pulled from. If BrainPass returns nothing relevant,
say "I checked your notes and didn't find anything about that." Never
make up answers.

When I tell you something worth remembering, suggest which file it
should land in (daily/, projects/, people/, topics/).
```

Wait for them to confirm it's pasted.

### Step 12 — write the first real note together

Ask: *"Tell me one thing about yourself or your work you wish I remembered forever. One sentence is fine — we'll write it to a note so the system goes live on something real."*

Take their answer. Create `~/BrainPass/vault/daily/YYYY-MM-DD.md` (today's date) with:

```markdown
---
date: YYYY-MM-DD
type: daily-log
---

# <today's date>

<their sentence verbatim>
```

If what they said is about a specific person or project, also create `people/<name>.md` or `projects/<name>.md` with the same content, so recall has two hits.

### Step 13 — prove it works

Hit the librarian yourself:

```bash
curl -s -X POST http://127.0.0.1:7778/recall \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg m "<a question about what they just told you>" \
                 --arg t "<main topic>" \
                 '{message: $m, topic: $t}')"
```

Show the user the JSON. Confirm the `sources` array includes the file you just wrote in step 12 and the `result` contains the fact they just told you.

If the result is empty or wrong → the query didn't hit the file. Common causes: keyword too generic, file wrote to wrong path. Debug, retry.

### Step 14 — hand off

Say this:

> "You're done. I have memory now. From here, all you do is write notes — one a day if you can, more if you feel like it. The more you write, the better I get at remembering you. Anytime you tell me something worth saving, I'll suggest which folder and filename it should go in, and you'll add it to your vault. I'll handle the rest."

Then demonstrate once more: ask them a follow-up question that would naturally pull from the note you just wrote. Watch them see it work.

---

## Edge cases you have to handle

- **No systemd (Mac, WSL without lingering, NixOS with no user systemd)** → run the librarian manually with `python3 ~/BrainPass/src/librarian.py serve &`. Warn the user it dies with the shell unless they set up launchd/supervisor/etc.
- **`systemctl --user` fails with "Failed to connect to bus"** → `loginctl enable-linger $USER` once, then reboot or `systemctl --user daemon-reexec`.
- **Port 7778 already in use** → change `LIBRARIAN_PORT` in `~/BrainPass/config/.env` to something else (e.g. `7878`), restart the service, and update the magic instruction in step 11 to use the new port.
- **Ollama not running** → `ollama serve` in another terminal before step 8.
- **User's Python is 3.9 or older** → step 3 above. Don't proceed until fixed.
- **Vault path differs from default** → edit `VAULT_PATH` in `.env` and restart.
- **Firewall blocks localhost** (rare) → troubleshoot with `ss -tlnp | grep 7778` and `curl -v http://127.0.0.1:7778/health`.

---

## Troubleshooting the runtime

- **`/status` says `keys_configured: 0`** → the `.env` doesn't have the key for the provider in `LLM_PROVIDER`. Example: `LLM_PROVIDER=openai` but only `GROQ_API_KEY` is set. Fix the mismatch, `systemctl --user restart brainpass-librarian`.
- **`/recall` returns `{"error": "All keys failed..."}`** → the API key is invalid or out of quota. Test it with a direct curl to the provider.
- **User says "my AI isn't using BrainPass"** → they skipped step 11 or pasted the instruction into the wrong place. Redo step 11 for their specific tool.
- **`files_indexed: 0` after writing notes** → the librarian caches the file count for 5 minutes. Either wait or `systemctl --user restart brainpass-librarian` to force a re-scan.
- **Librarian won't start** → `journalctl --user -u brainpass-librarian -n 100 --no-pager`. Read the traceback. Fix the cause. Common: broken `.env` syntax, bad API key format, wrong `LLM_PROVIDER` value.

---

## NotebookLM (optional, bring it up only if the user asks)

NotebookLM is Google's hosted RAG system. BrainPass works fine without it — the built-in keyword search is fast and good enough for personal vaults. If the user wants semantic search on top, walk them through uploading their vault files to https://notebooklm.google.com as a new notebook. Note: Google will see those files. Don't enable it for sensitive vaults.

There's no code integration shipped — NotebookLM is used in parallel, not wired into the librarian.

---

## Rules for you (the installing AI)

- **Don't install anything without asking first.** Even small things.
- **Don't edit the user's existing configs without telling them exactly what changed.**
- **Don't skip verification.** Steps 9 and 13 are non-negotiable. Prove the service works; prove recall works.
- **Don't ask more than one question at a time.** One question. Wait. Next question.
- **Don't assume the user is technical.** Explain things. They're handing you the repo because they don't want to read it.
- **If something errors, fix it yourself.** Read the error. Diagnose. Retry. Only escalate to the user if you genuinely need information only they have (like their API key choice).
- **Never put the user's API key in a git commit, a public paste, or any chat log they can't delete.** If you logged it anywhere outside `.env`, tell them to rotate it.

When you're done, the user should have:
- A running librarian on `127.0.0.1:7778`
- An Obsidian vault they can see
- One real note in it, about themselves
- You, wired up to check BrainPass before answering, with a first demonstration that it works

That's the finish line. Nothing before it counts.
