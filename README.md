<div align="center">

<img src="https://img.shields.io/badge/BrainPass-8B5CF6?style=for-the-badge&logo=obsidian&logoColor=white&labelColor=1E1B4B" alt="BrainPass" height="44">

### your AI finally remembers shit.

<br>

<img src="https://img.shields.io/badge/ships-today-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/setup-10_minutes-8B5CF6?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/runs_on-your_laptop-6366F1?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/cost-$0_to_start-3B82F6?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/python-3.10+-1E40AF?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/license-MIT-0EA5E9?style=flat-square&labelColor=1E1B4B">

</div>

---

## tl;dr

Your AI forgets you exist every time you close the tab. BrainPass gives it a notebook — markdown files on your own disk, searched in 50ms, handed to whatever LLM you're using with your question stapled to the top. Your AI stops hallucinating and starts citing. You stop explaining your life every morning.

- **10 minutes** to install. **$0** if you use Groq's free tier.
- Works with **Claude, GPT, Kimi, Llama, local models** — we don't care which.
- Your notes live in **a folder you own**. No cloud. No lock-in. No middleman.

<p align="center"><code>notes + search + your LLM = memory that survives</code></p>

---

## easiest install — hand it to your AI

You don't have to read this README. Clone the repo, open the folder in whatever AI coding tool you use — Claude Code, Cursor, Warp, Windsurf, Aider, Continue, whatever — and say:

> **"Read `SETUP-WITH-YOUR-AI.md` and set this up for me."**

Your AI will read the runbook, walk you through a 10-minute conversation, ask which LLM you want running behind the librarian (it'll recommend Groq's free tier), grab an API key from you, run the installer, start the service, wire itself into BrainPass, write your first note with you, and prove recall works. You answer like five questions total and hit enter.

If you'd rather install it manually — or you don't have an AI tool to hand the repo to — the rest of this README is the human version.

---

## how it actually works

You write notes in Obsidian (or literally any text editor — it's just markdown). A tiny Python service sits on `localhost:7778` and waits. When your AI has a question about you, it hits that service. The service searches your notes, grabs what's relevant, stuffs it into your LLM with your question, and hands back the answer. With citations.

```
you → "what am I supposed to finish by Friday?"
       │
       ▼
your AI → POST localhost:7778/recall
              │
              ▼
       BrainPass searches ~/BrainPass/vault/ in ~50ms
              │
              ▼
       finds: projects/johnson.md, daily/2026-04-12.md
              │
              ▼
       feeds them to your LLM with your question
              │
              ▼
you ← "wireframes — mobile breakpoint still open. Sarah needs
       them Friday EOD per projects/johnson.md."
```

That's it. No vector DB. No LangChain. No $20/month SaaS middleman. Just a librarian and a stack of notes.

---

## the stack

<div align="center">

<img src="https://img.shields.io/badge/Obsidian-8B5CF6?style=flat-square&logo=obsidian&logoColor=white">
<img src="https://img.shields.io/badge/NotebookLM-6366F1?style=flat-square&logo=google&logoColor=white">
<img src="https://img.shields.io/badge/Python_3.10+-3B82F6?style=flat-square&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Your_LLM-EC4899?style=flat-square">

</div>

| piece | what it is | why |
|---|---|---|
| **Obsidian** | free markdown notebook | your notes, your disk, your links |
| **NotebookLM** *(optional)* | Google's smart search | free tier, lazy setup, good recall |
| **Librarian** | ~300 lines of Python | the thing that actually does the work |
| **Your LLM** | Claude / GPT / Kimi / Llama / whatever | swap it anytime, notes don't care |

Boring tech on purpose. Every part of this stack has been stable for years. No bleeding edge. No "wait for v2". It runs today, on your laptop, with whatever you already have.

---

## install

### 1. clone & run the installer

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
./install.sh
```

You now have `~/BrainPass/` with a vault, a config folder, a systemd service, and a fresh `.env` template.

### 2. drop in an API key

Open `~/BrainPass/config/.env` and pick one provider. Groq has a free tier and is fastest to get going:

```bash
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

Or swap in `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / point at your local Ollama — same file.

### 3. give your agent a personality

Open `~/BrainPass/config/identity/SOUL.md`. This is the forever-system-prompt your AI will read on every call. Make it yours:

```markdown
# my agent

You're my personal assistant. Speak casually. Check my notes
before answering anything about me or my projects. Cite sources.
If you don't find the answer in the notes, say so — don't guess.

## about me
- building a rust CLI called ripfire
- I hate long explanations unless I ask
- timezone: America/Chicago
- call me by my first name
```

### 4. open the vault in Obsidian

Launch Obsidian → **Open folder as vault** → pick `~/BrainPass/vault/`. You'll see `daily/`, `projects/`, `people/`, `topics/`, `sources/`. Make a note in any of them. Save.

### 5. start the librarian

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian
curl http://127.0.0.1:7778/status
```

Should come back `{"status": "ok", ...}`. Done. The librarian is alive.

---

## the one step everyone skips

> [!IMPORTANT]
> **If you skip this step, BrainPass does nothing.** Installing it isn't enough. Your LLM has no idea the librarian exists until you tell it. This is the #1 reason people think BrainPass is broken.

Paste this block into your AI's system prompt / custom instructions / `CLAUDE.md` / whatever the personality slot is called in the tool you're using:

```
You have access to a memory system called BrainPass running at
http://127.0.0.1:7778. It contains my notes, preferences, projects,
and past conversations as markdown files.

BEFORE answering any question about me, my work, my preferences, or
anything we've discussed before, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<my question>", "topic": "<main topic>"}

Read the returned notes and answer using them as source of truth.
Always cite which file(s) you pulled from. If BrainPass returns
nothing relevant, say "I checked your notes and didn't find anything
about that." Never make up answers.

When I tell you something worth remembering, suggest which file it
should land in (daily/, projects/, people/, topics/).
```

### where to paste it

| tool | where |
|---|---|
| **Claude Code** | `CLAUDE.md` at your repo root, or `~/.claude/CLAUDE.md` globally |
| **Claude Desktop** | Settings → Project Instructions |
| **ChatGPT** | Settings → Custom Instructions → "How should ChatGPT respond?" |
| **Ollama / Open WebUI** | System Prompt field in chat settings |
| **LangChain / AutoGen / CrewAI** | System message + register `/recall` as a tool |

---

## writing notes that don't suck

BrainPass is only as smart as what you feed it. Five rules:

1. **one idea per file** — `projects/ripfire-cli.md`, not `projects.md`
2. **name files like you'd search** — future you types "sarah", future you wants `people/sarah.md` to exist
3. **date your daily notes** — `daily/2026-04-15.md`. Non-negotiable.
4. **link aggressively** — `[[ripfire-cli]]` in a daily note. Obsidian builds the graph for free.
5. **write short** — your LLM is not your therapist. Facts. Dates. Names. Done.

Example of a note that earns its keep (`people/sarah.md`):

```markdown
# Sarah Chen
- PM on ripfire project
- only works Tue/Thu
- Slack > email, always
- met at DesignCamp 2025
- birthday: Mar 3
- [[ripfire-cli]] for project context
```

---

## troubleshooting

<details>
<summary><b>librarian won't start</b></summary>

```bash
journalctl --user -u brainpass-librarian -n 50
```
99% of the time: missing API key in `~/BrainPass/config/.env`. Second most common: wrong `LLM_PROVIDER` / `LLM_MODEL` combo.
</details>

<details>
<summary><b>my AI isn't using BrainPass</b></summary>

Did you paste the magic instruction into your AI's system prompt? Probably not. Do it.
</details>

<details>
<summary><b>vault shows 0 files</b></summary>

You haven't written any notes. Open Obsidian, make a note, save. Try again.
</details>

<details>
<summary><b>it's slow</b></summary>

It's not BrainPass — search is ~50ms. It's your LLM's response time. Try a smaller / faster model, or Groq's free tier.
</details>

<details>
<summary><b>I want to switch LLMs</b></summary>

Edit `~/BrainPass/config/.env`, swap `LLM_PROVIDER` and `LLM_MODEL`, restart: `systemctl --user restart brainpass-librarian`. Your notes stay. Your AI doesn't forget.
</details>

---

## security

Your data is yours. That's not a marketing line, it's the architecture:

- **No credentials in this repo.** `.env` is gitignored. Fresh clones have zero secrets.
- **Vault lives on your disk.** Markdown files in `~/BrainPass/vault/`. Doesn't leave unless you send it.
- **Librarian binds to `127.0.0.1` only.** Not reachable from the internet unless you change that on purpose.
- **NotebookLM is opt-in.** Google only sees your notes if you upload them yourself.

If you can read the files in `~/BrainPass/`, you can audit every byte your AI has access to. No black box.

---

## architecture, for the curious

```
┌─────────────────────────────────────────┐
│             your LLM                    │
│    (Claude / GPT / Kimi / local)        │
└──────────────────┬──────────────────────┘
                   │ POST /recall
                   ▼
┌─────────────────────────────────────────┐
│        BrainPass Librarian              │
│      (Python HTTP on :7778)             │
│  • parses query                         │
│  • searches vault (keyword / FTS5)      │
│  • returns ranked note snippets         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│        your Obsidian vault              │
│      (markdown in ~/BrainPass/)         │
│  daily/  projects/  people/             │
│  topics/  sources/                      │
└─────────────────────────────────────────┘
```

The whole thing is ~300 lines of Python. No magic. Just good plumbing.

---

## who this is for

- devs tired of re-explaining their stack every new chat
- builders who want their AI to actually know the project
- anyone who's watched an LLM hallucinate their own preferences back at them
- people who trust their own disk more than someone else's cloud

---

<div align="center">

### star it. fork it. break it. ship your own brain.

<br>

<img src="https://img.shields.io/badge/MIT-license-0EA5E9?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/PRs-welcome-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/made_for-people_tired_of_repeating_themselves-8B5CF6?style=flat-square&labelColor=1E1B4B">

<br><br>

*boring tech on purpose. no LangChain, no vector DB rituals, no SaaS tax. just notes and a librarian.*

</div>
