<div align="center">

<img src="https://img.shields.io/badge/version-1.0.0-8B5CF6?style=flat-square" alt="version">
<img src="https://img.shields.io/badge/license-MIT-6366F1?style=flat-square" alt="license">
<img src="https://img.shields.io/badge/python-3.10+-3B82F6?style=flat-square" alt="python">

</div>

<h1 align="center">
  <img src="https://img.shields.io/badge/Brain-8B5CF6?style=for-the-badge" alt="Brain"><img src="https://img.shields.io/badge/Pass-6366F1?style=for-the-badge" alt="Pass"> 🧠⚡
</h1>

<p align="center">
  <strong>Your AI finally remembers shit.</strong>
</p>

<p align="center">
  <em>The open-source memory layer that turns any LLM into something with actual continuity.</em>
</p>

---

## ⚡ TL;DR — What's This?

<div align="center">

| 🧠 **Obsidian** | 🔍 **NotebookLM** | 🤖 **Any LLM** |
|:---:|:---:|:---:|
| Your notes | Smart search | The brain |

</div>

Every AI chat starts from zero. You explain your project. You explain it again. You explain it a third time. **BrainPass fixes that.**

Your AI can now:
- ✅ Remember stuff across every conversation  
- ✅ Cite sources (no more hallucinations)  
- ✅ Actually learn who you are  

<div align="center">

**⏱️ 10 min setup** · **💰 $0 with free tiers** · **🔒 Your data stays local**

</div>

---

## 😤 The Problem (In 30 Seconds)

You know when you're deep in a project with Claude or ChatGPT, you've explained your entire architecture, your constraints, your preferences... and then you open a new chat and **poof** — it's all gone?

That's not a feature. That's a bug.

Current AI has **no memory**. BrainPass gives it one. A real one. Stored in markdown files you own, can edit, can audit, can take anywhere.

---

## 🔮 How It Works (The Cool Part)

Instead of training or fine-tuning (expensive, slow, overkill), BrainPass uses **Retrieval-Augmented Generation** (RAG) — but make it simple.

```
You ask: "What was I supposed to finish by Friday?"
         │
         ▼
Your AI hits: POST http://127.0.0.1:7778/recall
         │
         ▼
BrainPass searches your Obsidian vault in ~50ms
         │
         ▼
Returns relevant notes to your AI with full context
         │
         ▼
Your AI answers using YOUR notes, citing the source files
```

**Result:** No more "as an AI language model..." — you get "According to your notes from Tuesday..."

---

## 🛠️ The Stack (Keep It Boring)

We intentionally used boring, stable, already-exists tech:

| Component | What It Does | Why We Picked It |
|-----------|--------------|------------------|
| **Obsidian** | Markdown note-taking | Free, local-first, links between notes |
| **NotebookLM** (optional) | Google's RAG over your files | Free tier, smart search, easy setup |
| **Python 3.10+** | The librarian service | Everyone has it, runs anywhere |
| **Your LLM** | The brain that talks to you | Claude, GPT, Kimi, Ollama — we don't care |

No vector databases to configure. No Docker rituals. No $20/month SaaS middleman.

---

## 🚀 Installation — 10 Minutes, Zero Decisions

### 📥 Step 1: Get the Code

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
```

### ⚙️ Step 2: Run the Setup Script

```bash
./install.sh
```

This creates `~/BrainPass/` with:
- `vault/` — your Obsidian notes folder
- `config/.env` — API keys (template)
- `config/identity/SOUL.md` — your agent's personality

### 🔑 Step 3: Add Your API Key

Edit `~/BrainPass/config/.env`:

```bash
# Pick ONE provider (we recommend Groq for free tier)
GROQ_API_KEY=gsk_your_key_here
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
```

**Free tier options:**
- **Groq** — `console.groq.com` (fast, generous free tier)
- **OpenRouter** — `openrouter.ai` (pay-per-use, cheap)

### 🎭 Step 4: Set Up Your Agent's Personality

Edit `~/BrainPass/config/identity/SOUL.md`:

```markdown
# My Agent

You're my personal assistant. Speak casually. Always check my notes 
before answering questions about me or my projects. Cite sources.

## About Me
- I'm building [your project]
- I prefer short answers
- My timezone is America/Chicago
- Call me by my name
```

This file tells your AI how to behave. It's the "system prompt" that persists forever.

### 🚀 Step 5: Start the Librarian

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian  # auto-start on boot
```

Verify it's running:
```bash
curl http://127.0.0.1:7778/status
# Should show: {"status": "ok", "vault_files": 0}
```

### 📝 Step 6: Open Your Vault in Obsidian

1. Launch Obsidian
2. "Open folder as vault" → select `~/BrainPass/vault/`
3. Write your first note in `daily/YYYY-MM-DD.md`

Done. Your AI now has memory.

---

## ⚠️ Tell Your AI About BrainPass (CRITICAL STEP)

**This is the #1 reason BrainPass "doesn't work" for people.** You have to actually tell your AI the librarian exists.

Add this to your AI's system prompt or custom instructions:

```
You have access to a memory system called BrainPass running at 
http://127.0.0.1:7778. It contains my notes, preferences, and project 
information in markdown files.

BEFORE answering any question about me, my work, my preferences, or 
anything we've discussed previously, you MUST query BrainPass:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<user's question>", "topic": "<main topic>"}

Read the returned notes and answer using them as your source of truth. 
Always cite which file(s) you referenced. If BrainPass returns nothing 
relevant, say "I checked your notes and didn't find anything about that."

When I tell you something worth remembering, suggest which file to save 
it to (daily/, projects/, people/, topics/).
```

### 🎯 Where to Put This:

**Claude Code / Claude Desktop:**
- Claude Code: Put it in your repo's `CLAUDE.md` or `.claude/CLAUDE.md`
- Claude Desktop: Settings → Project Instructions

**ChatGPT:**
- Settings → Custom Instructions → "How would you like ChatGPT to respond?"

**Open WebUI / Ollama:**
- System Prompt field in chat settings

**Any agent framework (LangChain, AutoGen, etc.):**
- Add `http://127.0.0.1:7778/recall` as a tool your agent can call
- Include the magic instruction in the system message

---

## 📝 Writing Notes That Actually Help

BrainPass is only as good as what you put in it. Quick tips:

1. **Use daily notes:** `daily/2026-04-15.md` — dump thoughts, decisions, what you learned
2. **Link between notes:** `[[johnson-project]]` — Obsidian makes this easy
3. **One idea per file:** Don't write novels. Split into `johnson-timeline.md`, `johnson-contacts.md`, etc.
4. **Write for search:** Name files what you'd actually search for
5. **Include metadata:** Dates, who said what, decisions made

**Example good note** (`people/sarah.md`):
```markdown
# Sarah Chen

- PM on Johnson wireframes project
- Available Tue/Thu only
- Prefers Slack > email
- Met at DesignCamp 2025
- Married to Dave (also PM)
- [[johnson-project]] for context
```

---

## 👁️ What Your AI Sees

When BrainPass finds relevant notes, your AI gets something like this:

```
Relevant notes from your vault:

--- From: daily/2026-04-14.md ---
Had call with Sarah about Johnson wireframes. She needs them by 
Friday EOD. She's stressed about the timeline.

--- From: projects/johnson.md ---
Wireframes: 80% done. Need to finish mobile breakpoint. 
Deadline: Friday Apr 18.

--- From: people/sarah.md ---
- PM on Johnson wireframes
- Available Tue/Thu only
- Prefers Slack
```

Your AI reads this and answers: *"According to your notes, the Johnson wireframes are 80% done with the mobile breakpoint remaining. Sarah (who prefers Slack) needs them by Friday EOD and seemed stressed about the timeline in yesterday's call."*

That's the magic. Real context. Real answers.

---

## 💡 Real Use Cases (Why Devs Actually Want This)

**Building a product:**
- Store architecture decisions in `decisions/`
- Link to API docs in `sources/`
- Track user feedback in `feedback/`
- AI remembers why you chose Postgres over Mongo

**Managing a team:**
- `people/` folder with everyone's preferences, quirks, timezones
- `meetings/` with notes from every 1:1
- AI knows who hates morning meetings, who's the expert on X

**Learning something new:**
- `topics/rust.md` with concepts you're learning
- `sources/` with articles and tutorials
- AI builds on what you've already studied

**Content creation:**
- `ideas/` for half-baked thoughts
- `drafts/` for in-progress work
- `published/` for finished pieces
- AI knows your style, your past work, your audience

---

## 🔧 Troubleshooting (Because Something Always Breaks)

**"Librarian won't start"**
```bash
journalctl --user -u brainpass-librarian -n 50
# Probably: missing API key in config/.env
```

**"My AI isn't using BrainPass"**
- Did you paste the magic instruction into your AI's system prompt?
- This is the #1 fix. Do it.

**"Vault shows 0 files"**
- You haven't written any notes yet. Open Obsidian, make a note, save it.

**"It's slow"**
- Groq free tier is fast. If using local models, try a smaller one.

**"I want to switch LLMs"**
- Edit `config/.env`, change provider/model, restart: `systemctl --user restart brainpass-librarian`
- Your notes don't move. Your AI doesn't forget.

---

## 🔒 Security (Your Data Is Yours)

<div align="center">

| ✅ No credentials in repo | ✅ Local markdown files | ✅ Localhost only |
|:---:|:---:|:---:|
| `.env` gitignored | Never leaves your machine | `127.0.0.1:7778` |

</div>

- ✅ No credentials in this repo — `.credentials` and `.env` are gitignored
- ✅ Your vault is local markdown — doesn't leave your machine
- ✅ Librarian binds to `127.0.0.1` (localhost) — not internet-accessible
- ✅ NotebookLM is optional — Google only sees vault if you enable it
- ✅ You can audit everything — it's just text files

---

## 🏗️ Architecture (For the Curious)

```
┌─────────────────────────────────────────┐
│           Your LLM                    │
│   (Claude, GPT, Kimi, Local)          │
└──────────────┬──────────────────────────┘
               │ POST /recall
               ▼
┌─────────────────────────────────────────┐
│      BrainPass Librarian                │
│   (Python HTTP server on :7778)         │
│   - Receives queries from LLM           │
│   - Searches vault (keyword/FTS5)       │
│   - Returns relevant note snippets        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Your Obsidian Vault                │
│   (Markdown files in ~/BrainPass/)      │
│   - daily/ — dated logs                 │
│   - projects/ — active work             │
│   - people/ — contacts, preferences     │
│   - topics/ — knowledge bases           │
│   - sources/ — references, articles     │
└─────────────────────────────────────────┘
```

The whole thing is ~300 lines of Python. No magic. Just good plumbing.

---

## 🤝 Contributing

This is the sanitized, open-source version of a memory system that's been running in production for months.

Fork it. Break it. Improve it. Ship your own version.

MIT License. Build your own brain.

---

## 🔗 Links

- **Repo:** https://github.com/coderook520/BrainPass
- **Issues:** https://github.com/coderook520/BrainPass/issues
- **Obsidian:** https://obsidian.md
- **NotebookLM:** https://notebooklm.google.com
- **Groq:** https://console.groq.com (free tier)

---

<div align="center">

*Made by developers who were tired of explaining the same shit to their AI every single day.*

### 🧠⚡ Give your AI a memory.

</div>