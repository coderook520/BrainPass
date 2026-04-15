# BrainPass — Use Cases

BrainPass gives any AI agent a persistent memory. Here's who actually benefits,
with real vault layouts you can copy.

---

## 1. Developer with too many side projects

**Problem:** You've got five repos, three stacks, two deployment targets, and
every new chat starts with "let me explain my setup again."

**Vault layout:**
```
vault/
├── projects/
│   ├── ripfire-cli.md          ← rust CLI, arch notes, open bugs
│   ├── brainpass.md            ← this repo, TODO list
│   └── auth-service.md         ← work project, the annoying one
├── decisions/
│   ├── why-postgres-over-mongo.md
│   └── why-we-ditched-langchain.md
└── snippets/
    ├── fish-functions.md
    └── docker-incantations.md
```

**Payoff:** Your AI stops asking what stack you're on. It remembers that you
chose Postgres over Mongo and why, so it doesn't suggest switching three
months later.

---

## 2. Writer / worldbuilder

**Problem:** 80k-word novel, 30 characters, ten intersecting plot threads, and
your AI keeps contradicting itself about who knows what.

**Vault layout:**
```
vault/
├── characters/
│   ├── maya-chen.md            ← backstory, arc, current state
│   ├── the-detective.md
│   └── maya's-father.md
├── lore/
│   ├── the-city.md
│   └── the-cult.md
└── chapters/
    ├── ch01.md
    └── ch02.md
```

**Payoff:** When you ask "what did Maya know about the detective in chapter 7?"
your AI answers from your actual character sheet instead of hallucinating a new
version of the timeline.

---

## 3. Second brain / knowledge worker

**Problem:** You read 20 articles a week and forget most of them by Monday.

**Vault layout:**
```
vault/
├── sources/
│   ├── 2026-04-14-nn-scaling-laws.md
│   └── 2026-04-12-transformer-inference.md
├── topics/
│   ├── neural-networks.md
│   └── inference-optimization.md
└── daily/
    └── 2026-04-15.md           ← today's thoughts, linked to sources
```

**Payoff:** Six months from now, "what did I read about inference
optimization?" returns actual citations with file paths, not vibes.

---

## 4. Founder / product manager

**Problem:** Pitching investors, negotiating with vendors, making architecture
calls — and nobody can remember which decision was made for which reason.

**Vault layout:**
```
vault/
├── pitches/
│   ├── seed-deck-v3.md
│   └── investor-faq.md
├── decisions/
│   ├── stripe-over-square.md   ← the why, the tradeoff, the date
│   └── aws-over-gcp.md
├── metrics/
│   └── 2026-04-mrr.md
└── meetings/
    └── 2026-04-10-sequoia.md
```

**Payoff:** Investor asks "why Stripe?" and your AI answers in your voice
using the exact tradeoffs you wrote down three months ago. You never
contradict yourself across pitches.

---

## Quick wins for any vault

- **Write daily logs.** `daily/YYYY-MM-DD.md`. Even two sentences. Future
  you will thank you.
- **Use consistent file names.** Searching "sarah" should always find
  `people/sarah.md`.
- **Link aggressively.** `[[ripfire-cli]]` in a daily note. Obsidian builds
  the graph; your AI gets more signal.
- **Never delete. Archive.** Move stale notes to `_archive/` so the librarian
  can still surface them if needed.

## What NOT to put in your vault

- Raw API keys, passwords, 2FA secrets — it's a text file, not a password
  manager.
- Health or financial data you wouldn't be comfortable with your LLM provider
  seeing. The librarian sends relevant snippets to your chosen LLM on every
  recall.
- Anything under an NDA that forbids cloud LLM access. Run a local model for
  those vaults.

## Integration with tools

### Claude Code

Put the magic instruction in your repo's `CLAUDE.md` or `~/.claude/CLAUDE.md`.
See `docs/AGENT_INTEGRATION.md`.

### ChatGPT

Settings → Custom Instructions → "How would you like ChatGPT to respond?" —
paste the magic instruction. ChatGPT can't hit `localhost` from their servers,
so this works best with a local ChatGPT-compatible client (Open WebUI,
LibreChat, etc.) that does.

### LangChain / AutoGen / CrewAI

Register `http://127.0.0.1:7778/recall` as a tool your agent can call. The
agent framework handles the HTTP call; you just tell your agent to use the
tool before answering anything personal.

---

BrainPass is only as smart as the notes you feed it. Start with five files.
Add one a day. In three months your AI will know you better than half your
coworkers.
