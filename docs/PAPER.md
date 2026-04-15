# BrainPass: Technical Paper
## A Reproducible Agent Memory System Using Obsidian, NotebookLM, and Configurable LLMs

### Abstract

BrainPass provides AI agents with persistent, citeable memory using local-first infrastructure. By combining structured markdown vaults (Obsidian), semantic retrieval (NotebookLM), and configurable LLM providers (Groq, OpenAI, Anthropic, or local), agents gain the ability to recall prior context, cite exact sources, and maintain continuity across sessions. This paper presents the architecture, implementation, and deployment of BrainPass as an open-source system for agent developers and AI researchers.

### 1. Introduction

**Problem:** Large language models (LLMs) operate statelessly. Each session begins cold, lacking awareness of prior conversations, user preferences, or accumulated knowledge. While context windows have expanded, they remain finite and expensive.

**Solution:** BrainPass externalizes agent memory into a structured, searchable vault that persists across sessions. Memory becomes:
- **Retrievable** — Semantic search surfaces relevant context
- **Citeable** — Every recall references exact sources
- **Inspectable** — Plaintext markdown enables audit and version control
- **Portable** — Users choose their LLM provider

### 2. Architecture

#### 2.1 System Overview

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   User      │────▶│  BrainPass      │────▶│  Obsidian Vault │
│   Input     │     │  Librarian      │     │  (Markdown)     │
└─────────────┘     │  (Port 7778)    │     └─────────────────┘
                    │                 │              │
                    │  ┌───────────┐  │              ▼
                    │  │  File     │  │     ┌─────────────────┐
                    │  │  Search   │  │     │  NotebookLM     │
                    │  └───────────┘  │     │  (Optional)     │
                    │        │         │     └─────────────────┘
                    │        ▼         │
                    │  ┌───────────┐   │
                    │  │  LLM      │   │
                    │  │  Compile  │   │
                    │  └───────────┘   │
                    └─────────────────┘
```

#### 2.2 Components

**Librarian Service:** Python HTTP server exposing three endpoints:
- `POST /recall` — Primary endpoint accepting `{"message": "...", "topic": "..."}`
- `GET /query?q=...` — Simplified query interface
- `GET /status` — Health and configuration check

**Obsidian Vault:** Structured markdown with folders:
- `daily/` — Session logs (chronological)
- `topics/` — Curated knowledge (thematic)
- `people/` — Entity profiles
- `projects/` — Active work tracking
- `sources/` — External materials

**LLM Layer:** Provider-agnostic interface supporting:
- Groq (GPT-OSS-120B, Llama 3.3 70B)
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet, Claude 3.5 Haiku)
- Local models (Ollama, vLLM, any OpenAI-compatible endpoint)

### 3. Implementation

#### 3.1 File Search Algorithm

Simple keyword scoring enables fast local search without external dependencies:

```python
def search_files(query, max_results=5):
    results = []
    query_words = query.lower().split()
    
    for file_path in vault_path.rglob("*.md"):
        content = file_path.read_text()
        score = sum(content.lower().count(word) for word in query_words)
        if score > 0:
            results.append({"file": file_path, "score": score})
    
    return sorted(results, key=lambda x: x["score"], reverse=True)[:max_results]
```

#### 3.2 Recall Pipeline

1. **Skip Check** — Filter acknowledgments ("ok", "cool", URLs)
2. **Search** — Score vault files by keyword frequency
3. **Compile** — Construct prompt with sources and user message
4. **LLM Call** — Send to configured provider with identity context
5. **Cache** — Write result to `/tmp/brainpass-topic.txt` for injection

#### 3.3 Provider Abstraction

Environment-based configuration enables provider switching:

```bash
# ~/.env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

Headers and payloads adapt per provider (OpenAI-compatible vs. Anthropic format).

### 4. Security Model

BrainPass adopts a "local-first, credential-separated" security posture:

| Principle | Implementation |
|-----------|----------------|
| Local data | Vault stays on user's machine |
| No repo secrets | API keys in `.env` (gitignored) |
| Auditability | Plaintext markdown, no binary blobs |
| User control | Identity files (SOUL.md) customizable |

### 5. Usage Patterns

#### 5.1 Agent Integration

Agents call the Librarian before generating responses:

```bash
RECALL=$(curl -s -X POST http://127.0.0.1:7778/recall \
  -H 'Content-Type: application/json' \
  -d '{"message":"User question","topic":"none"}')
CONTEXT=$(echo "$RECALL" | jq -r '.result // empty')
```

#### 5.2 Session Bootstrap

Add to session-start to pre-load context:

```bash
LATEST=$(cat /tmp/brainpass-topic.txt 2>/dev/null || echo "current")
curl -s -X POST http://127.0.0.1:7778/recall \
  -d '{"message":"Session start","topic":"'$LATEST'"}'
```

### 6. Evaluation

**Performance:** Local keyword search over typical personal vaults (hundreds of files) completes in well under 100ms — the inner loop is `rglob` plus Python string counting. LLM compilation dominates end-to-end latency and adds 1-3s depending on provider and model.

**Recall Accuracy:** Citation accuracy depends on vault structure. Well-organized vaults with clear file names and links yield higher relevance.

**Limitations:** 
- Keyword search lacks semantic understanding (mitigated by NotebookLM integration option)
- Requires markdown discipline for optimal results
- LLM costs apply for compilation step

### 7. Future Work

- **Vector search** — Integrate Chroma/FAISS for semantic retrieval
- **Multi-agent** — Shared vaults for team memory
- **Web interface** — Browser-based vault management
- **Mobile sync** — Obsidian Mobile integration

### 8. Conclusion

BrainPass demonstrates that agent memory need not depend on proprietary systems. By combining open tools (Obsidian, Python HTTP services) with configurable LLM providers, users retain ownership of their data while enabling sophisticated recall capabilities.

The system is intentionally simple — complexity emerges from vault organization, not infrastructure. This simplicity enables reproducibility, auditability, and customization.

### References

1. coderook520. (2026). *BrainPass: A Local-First Agent Memory System*. GitHub: https://github.com/coderook520/BrainPass
2. OpenAI. (2024). *GPT-4 Technical Report*.
3. Anthropic. (2024). *Claude 3 Model Card*.
4. Groq. (2026). *GPT-OSS-120B on Groq Documentation*.

---

**Author:** coderook520  
**Date:** April 2026  
**License:** MIT
