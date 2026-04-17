<div align="center">

# 🧠 Easiest install. Just hand it to your AI and watch him take care of the rest.

<br>

<img src="https://img.shields.io/badge/BrainPass-8B5CF6?style=for-the-badge&logo=obsidian&logoColor=white&labelColor=1E1B4B" alt="BrainPass" height="44">

### your AI finally remembers shit.

**works with any AI. Claude, GPT, Gemini, Llama, Mistral, Ollama, LM Studio — if it speaks text, BrainPass gives it memory.**

<br>

<img src="https://img.shields.io/badge/v3-self--feeding_brain-EC4899?style=for-the-badge&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/88_tests-passing-10B981?style=for-the-badge&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/auth--gated-default_ON-F59E0B?style=for-the-badge&labelColor=1E1B4B">

<br><br>

<img src="https://img.shields.io/badge/Claude-CC785C?style=flat-square&logo=anthropic&logoColor=white">
<img src="https://img.shields.io/badge/GPT-412991?style=flat-square&logo=openai&logoColor=white">
<img src="https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white">
<img src="https://img.shields.io/badge/Llama-0467DF?style=flat-square&logo=meta&logoColor=white">
<img src="https://img.shields.io/badge/Mistral-FF7000?style=flat-square">
<img src="https://img.shields.io/badge/Ollama-000000?style=flat-square">
<img src="https://img.shields.io/badge/LM_Studio-6C47FF?style=flat-square">
<img src="https://img.shields.io/badge/any_OpenAI--compatible-gray?style=flat-square">

</div>

---

## TL;DR

> Your AI is a **goldfish**. Every new chat it forgets you exist. BrainPass is the librarian who hands it a briefing packet 50ms before it opens its mouth.
>
> - **Your notes live on your disk.** Plain markdown in `~/BrainPass/vault/`. No cloud. No vendor lock-in.
> - **Any AI, anytime.** Swap Claude for GPT for Llama without losing your notes.
> - **Fires automatically.** A hook runs on every message so your AI never forgets to check.
> - **5 search engines + 4 self-feeding features.** It doesn't just *read* your vault — it *grows* it while you use it.
> - **Gated by default.** Only answers when an AI CLI is actively running under your user. Cron jobs, test loops, supply-chain surprises → `403`. Your API key stops bleeding when you walk away.
> - **Installs in 10 minutes.** Free with Groq. Works offline with Ollama. `~/BrainPass` is yours.

```bash
git clone https://github.com/coderook520/BrainPass.git && cd BrainPass && ./install.sh
```

---

## the goldfish problem

Every LLM — Claude, GPT, Kimi, Llama — resets to zero the second you close the tab. You could spend three hours explaining your business, walk away, come back, and it's a stranger.

You can't fix that. Weights are frozen. Context windows are finite. Anyone selling you "AI memory" is selling you a compressed summary on their servers.

What you *can* fix is making the forgetting **irrelevant**.

### Marcus and Sarah

Picture a boardroom. Marcus is brilliant but has no memory — if you pause for breath, he forgets who you are.

Put **Sarah** next to him. Three superpowers:

1. Access to the filing cabinet in the corner (your Obsidian vault)
2. She reads 10,000 documents in 50 milliseconds
3. She doesn't wait to be asked

You start talking. Sarah dashes to the cabinet, pulls the Johnson folder, grabs Tuesday's notes, snags yesterday's Slack thread, slaps a briefing on Marcus's desk before he opens his mouth.

> **Marcus:** *(flipping the packet)* "Right — you're 80% done on mobile breakpoint, Sarah Chen needs it Friday EOD, she prefers Slack, and she sounded stressed Tuesday. Want me to unstick the nav?"

Marcus didn't remember anything. He's still a goldfish. But Sarah fed him every detail 0.05 seconds before he needed it, and from your side it feels like talking to someone who's been in every meeting.

**That's BrainPass.**

- **You** are the person in the room
- **Marcus** is whatever LLM you're pointed at (swap anytime)
- **Sarah** is the librarian running on `127.0.0.1:7778`
- **The filing cabinet** is your Obsidian vault — markdown files on your disk

---

## how it works

```
you → "what am I supposed to finish by Friday?"
       │
       ▼  (UserPromptSubmit hook fires BEFORE your AI sees the message)
brainpass-inject.sh → POST localhost:7778/recall
                            │
                            ▼
       BrainPass searches ~/BrainPass/vault/ in ~50ms
       (5 engines in parallel: BM25 + semantic + graph + dreams + predictions)
                            │
                            ▼
       finds: projects/johnson.md, daily/2026-04-12.md
                            │
                            ▼
       compiles a cited briefing with your runner LLM
                            │
                            ▼
your AI ← sees your message + the briefing, reads both, answers
```

No LangChain. No $20/month SaaS middleman. Just a librarian, a stack of notes, and a ~100-line shell hook that fires on every message so your AI never has to remember to check.

---

## what's in the box

### 5 search engines (v2.1)

| # | engine | what it does |
|---|---|---|
| 1 | **BM25** | classic keyword — fast, zero deps, always on |
| 2 | **Semantic** *(optional)* | ChromaDB vectors — finds notes that *mean* the same thing |
| 3 | **Knowledge Graph** | SQLite graph of people/projects/concepts |
| 4 | **Dream Engine** | speculative connections generated while idle (sandboxed in `.dreams/`) |
| 5 | **Predictive Pre-fetch** | Markov chain learns what you ask next, fetches it before you type |

Results from 1-3 merge via **Reciprocal Rank Fusion** (same algorithm Google uses). A note hit by all three ranks higher than one hit by keywords alone.

**Conflict detection.** When your notes contradict each other (different dates, different claims), BrainPass flags it instead of silently picking one.

### 4 self-feeding features (v3, all default on)

| feature | what it does |
|---|---|
| **Write-back** | Your AI's responses get parsed for save-worthy facts. Proposals queue up. `bp-write review` walks them with one-tap approve. Vault grows without you typing notes. |
| **Temporal awareness** | Recent notes outrank old ones (30-day exp decay). `/changed?since=<iso>` surfaces what moved this week. `/timeline?topic=X` shows cross-time fact evolution — catches "you said Rust 6 months ago, Go last Tuesday." |
| **Self-teaching vault** | Every recall logs (scrubbed) which notes were surfaced. `bp-analytics report` shows **hot notes** (retrieved constantly) and **dead notes** (never touched in 90d). The vault improves from being used. |
| **Auto-research** | When your vault has nothing on a topic (< 2 hits), the librarian fetches Wikipedia + arXiv + DuckDuckGo, synthesizes with your LLM, and queues the findings via write-back. **Solves the cold-start problem.** Next time you ask, it's already in your vault. |

The loop: empty vault → ask → auto-research → approve → next time you ask, zero research cost. Your vault grows on **revealed preference** — topics you actually care about.

### why this beats "AI memory" features

ChatGPT and friends sell "memory" that's a compressed summary on their servers. Loses nuance. Can't audit. Can't edit. Policy change tomorrow, it's gone.

BrainPass doesn't summarize — it **retrieves**. The full note. The exact thread. The complete spec. Fresh, every time.

You own the cabinet. You switch AIs whenever. You delete anything. You audit every byte. It's your disk.

---

## 10-minute install

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
./install.sh
```

You now have `~/BrainPass/` with a vault, config folder, systemd service, and a gate daemon auto-enabled.

### 1. drop in an API key

Edit `~/BrainPass/config/.env`. **Groq has a free tier and is fastest:**

```bash
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

Or swap in `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / point at local Ollama — same file.

### 2. give your agent a personality

Edit `~/BrainPass/config/identity/SOUL.md`:

```markdown
# my agent
You're my personal assistant. Speak casually. Check my notes
before answering anything about me or my projects. Cite sources.
If you don't find the answer in the notes, say so — don't guess.

## about me
- building a rust CLI called ripfire
- I hate long explanations unless I ask
- timezone: America/Chicago
```

### 3. open the vault in Obsidian

**Open folder as vault** → pick `~/BrainPass/vault/`. You'll see `daily/`, `projects/`, `people/`, `topics/`, `sources/`. Make a note in any of them. Save.

### 4. start it

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian
curl http://127.0.0.1:7778/status
```

Should come back `{"status": "ok", ...}`. Done.

### 5. the one step everyone skips

> [!IMPORTANT]
> **If you skip this step, BrainPass does nothing.** Your LLM has no idea the librarian exists until you tell it.

Paste this into your AI's system prompt / custom instructions / `CLAUDE.md`:

```
You have access to a memory system called BrainPass at
http://127.0.0.1:7778. It contains my notes, preferences, projects,
and past conversations as markdown files.

BEFORE answering any question about me, my work, my preferences, or
anything we've discussed before, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<my question>", "topic": "<main topic>"}

Read the returned notes and answer using them as source of truth.
Always cite which file(s) you pulled from. If BrainPass returns
nothing relevant, say "I checked your notes and didn't find anything."
Never make up answers.
```

| tool | where to paste |
|---|---|
| **Claude Code** | `CLAUDE.md` at repo root, or `~/.claude/CLAUDE.md` globally |
| **Claude Desktop** | Settings → Project Instructions |
| **ChatGPT** | Settings → Custom Instructions |
| **Cursor / Windsurf / Aider** | `.cursorrules` / system prompt |
| **Ollama / Open WebUI** | System Prompt field |

For Claude Code / Cursor / etc. that support hooks, the `hooks/brainpass-inject.sh` hook fires **automatically** on every message. No system prompt trust required.

---

## writing notes that don't suck

BrainPass is only as smart as what you feed it. Five rules:

1. **One idea per file.** `projects/ripfire-cli.md`, not `projects.md`.
2. **Name files like you'd search.** Future you types "sarah" → `people/sarah.md` better exist.
3. **Date daily notes.** `daily/2026-04-15.md`. Non-negotiable.
4. **Link aggressively.** `[[ripfire-cli]]` in a daily note. Obsidian builds the graph for free.
5. **Write short.** Your LLM is not your therapist. Facts. Dates. Names. Done.

Example (`people/sarah.md`):

```markdown
# Sarah Chen
- PM on ripfire project
- only works Tue/Thu
- Slack > email, always
- met at DesignCamp 2025
- birthday: Mar 3
- [[ripfire-cli]] for project context
```

With **write-back on** you don't even have to write most of these — when you tell your AI "Sarah's birthday is March 3," the extractor proposes `people/sarah.md` with that fact, you hit approve in `bp-write review`, it's in the vault.

---

## security — your data is yours

- **No credentials in this repo.** `.env` is gitignored. Fresh clones have zero secrets.
- **Vault lives on your disk.** Markdown files in `~/BrainPass/vault/`. Doesn't leave unless you send it.
- **Librarian binds to `127.0.0.1` only.** Not reachable from the internet.
- **Human-session gate default ON.** Autonomous callers (cron jobs, test loops, buggy agent frameworks, supply-chain compromise) get `403` — `/recall` only answers when an AI CLI is actively running under your user with a real TTY. Your API key stops bleeding when you walk away.
- **Auto-research is hardened against its own risks:** unforgeable XML envelope (prompt-injection-proof), CIDR-aware SSRF blocklist, resolve-all DNS (closes multi-A rebinding), 3s inline budget (won't stall your hook), cost-aware response footer (you see what you spent).
- **NotebookLM is opt-in.** Google only sees your notes if you upload them yourself.

If you can read files in `~/BrainPass/`, you can audit every byte your AI has access to.

Full architecture + threat model: [`docs/gate.md`](docs/gate.md) and [`docs/brain-v3.md`](docs/brain-v3.md).

---

## CLIs you get

| command | what it does |
|---|---|
| `bp-write review` | Walk pending write-back proposals (one-tap approve / reject / skip) |
| `bp-analytics report` | One-shot "how's my brain doing" (hot / dead / patterns) |
| `bp-research status` | Is auto-research enabled? What's today's cost? |
| `bp-call-librarian` | Curl wrapper that fetches a gate ticket automatically |

---

## API endpoints

| method | path | gated | what it does |
|---|---|---|---|
| GET  | `/health` | no | is the librarian alive? |
| GET  | `/status` | no | full system status |
| POST | `/recall` | **yes** | full 3-phase recall (vault + optional auto-research) |
| GET  | `/query?q=...` | **yes** | search + compile in one call |
| GET  | `/dreams?limit=N` | **yes** | browse sandboxed dream insights |
| GET  | `/predictions?topic=T` | **yes** | predicted next topics |
| GET  | `/changed?since=<iso>` | **yes** | recent vault changes |
| GET  | `/timeline?topic=X` | **yes** | chronological fact evolution |
| GET  | `/write-queue` | **yes** | pending write-back proposals |
| POST | `/write-queue/{id}/approve` | **yes** | commit proposal to vault |
| POST | `/write-queue/{id}/reject` | **yes** | discard proposal |
| GET  | `/analytics/hot-notes?days=N` | **yes** | most-retrieved notes |
| GET  | `/analytics/dead-notes?days=N` | **yes** | never-retrieved notes |
| GET  | `/analytics/query-patterns?days=N` | **yes** | common query topics |
| POST | `/clear-cache` | no | wipe session cache |

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

Did you paste the magic instruction into your AI's system prompt? Probably not. Or wire the `hooks/brainpass-inject.sh` hook into your tool. Do one of those.
</details>

<details>
<summary><b>every request returns 403</b></summary>

The human-session gate doesn't see an AI CLI running with a TTY. Check: `systemctl --user status human-session-tracker`. Start it if it's down. If you're using a CLI the tracker doesn't recognize, add it to `BP_INTERACTIVE_PROCS` regex in `.env`. Or set `BP_GATE_DISABLED=1` in `.env` to turn off the gate (not recommended — it's what stops autonomous API-key burn).
</details>

<details>
<summary><b>vault shows 0 files</b></summary>

You haven't written any notes. Open Obsidian, make a note, save. Try again. Or let auto-research handle cold-start — ask a question, approve the draft in `bp-write review`.
</details>

<details>
<summary><b>it's slow</b></summary>

Search is ~50ms. Inline research is capped at 3s. Anything above that is your LLM provider's response time. Try Groq's free tier (fastest) or a smaller model.
</details>

<details>
<summary><b>I want to switch LLMs</b></summary>

Edit `~/BrainPass/config/.env`, swap `LLM_PROVIDER` and `LLM_MODEL`, restart: `systemctl --user restart brainpass-librarian`. Your notes stay. Your AI doesn't forget.
</details>

<details>
<summary><b>upgrade to latest</b></summary>

```bash
cd ~/BrainPass && git pull && ./install.sh && systemctl --user restart brainpass-librarian
```
Idempotent. Preserves your config, vault, and analytics history.
</details>

---

## architecture

```
┌─────────────────────────────────────────────┐
│              your LLM                       │
│     (Claude / GPT / Kimi / local)           │
└──────────────────┬──────────────────────────┘
                   │ POST /recall (+ gate ticket)
                   ▼
┌─────────────────────────────────────────────┐
│  Human-Session Gate  (403 if no human)      │
├─────────────────────────────────────────────┤
│  BrainPass Librarian  (Python :7778)        │
│                                             │
│  ┌─────────┐ ┌──────────┐ ┌─────────────┐  │
│  │  BM25   │ │ Semantic │ │  Knowledge  │  │
│  │ keyword │ │ ChromaDB │ │    Graph    │  │
│  └────┬────┘ └────┬─────┘ └──────┬──────┘  │
│       └───────────┼──────────────┘          │
│                   ▼                         │
│            RRF Merge + Conflict Det         │
│                   │                         │
│  ┌──────┬────────┼────────┬──────────┐     │
│  ▼      ▼        ▼        ▼          ▼     │
│ Dream  Predict  Writeback Temporal Research │
│ (.dm)  (Markov) (queue)   (decay)  (web)   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    your Obsidian vault  (markdown files)    │
│ daily/ projects/ people/ topics/ sources/   │
└─────────────────────────────────────────────┘
```

---

## what makes BrainPass different

| feature | ChatGPT memory | Mem0 / MemGPT | BrainPass |
|---|---|---|---|
| your data stays local | no | depends | **yes, always** |
| works with any LLM | no | some | **all of them** |
| you can audit everything | no | kinda | **yes, it's markdown** |
| search engines | 1 (summary) | 1 (vector) | **5 + fusion merge** |
| conflict detection | no | no | **yes** |
| write-back from conversation | no | manual | **auto (with approval)** |
| auto-research on empty vault | no | no | **yes (default ON)** |
| temporal decay + staleness | no | no | **yes** |
| usage analytics (hot/dead) | no | no | **yes** |
| autonomous-burn protection | n/a | no | **yes (default ON gate)** |
| cost | $20/mo | varies | **$0 (Groq free tier)** |
| setup time | built-in | 30+ min | **10 min** |

---

## who this is for

- devs tired of re-explaining their stack every new chat
- builders who want their AI to actually know the project
- anyone who's watched an LLM hallucinate their own preferences back at them
- people who trust their own disk more than someone else's cloud
- anyone who wants their AI to get smarter the more they use it
- people who want AI memory without giving their data to a corporation

---

<div align="center">

### star it. fork it. break it. ship your own brain.

<br>

<img src="https://img.shields.io/badge/MIT-license-0EA5E9?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/PRs-welcome-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/made_for-people_tired_of_repeating_themselves-8B5CF6?style=flat-square&labelColor=1E1B4B">

<br><br>

*five engines. four self-feeding features. zero SaaS. your notes, your disk, your brain.*

</div>
