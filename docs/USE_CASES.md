# BrainPass: Use Cases & Applications

## What Is BrainPass?

BrainPass gives **any AI agent persistent memory**. Your agent remembers conversations, cites sources, and maintains continuity across sessions — using Obsidian, NotebookLM, and your choice of LLM.

---

## Core Use Cases

### 1. Personal AI Assistant with Memory

**Problem:** ChatGPT, Claude, Gemini forget everything when the tab closes.

**BrainPass Solution:**
- Your agent remembers your preferences, history, and context
- Cites exactly which conversation something was mentioned in
- Maintains personality and relationship continuity

**Example:**
```
You: "Remind me what my sister's birthday gift idea was"
Agent: "According to your notes from March 10th [1], you planned to get 
sheila@email.com a custom photo book of her dogs."
```

### 2. Knowledge Management for Professionals

**Who:** Developers, writers, researchers, consultants

**Use:**
- Code snippets and solutions
- Client meeting notes with citations
- Project research with source tracking
- Decision logs with reasoning preserved

**Vault Structure:**
```
vault/
├── clients/
│   ├── acme-corp.md
│   └── globex-industries.md
├── projects/
│   ├── migration-2026.md
│   └── new-feature-x.md
├── research/
│   ├── rust-vs-go.md
│   └── payment-processors.md
└── decisions/
    ├── why-postgres-over-mysql.md
    └── architecture-v2.md
```

### 3. Creative Writing & Worldbuilding

**Who:** Authors, game designers, RPG masters

**Use:**
- Character profiles that evolve
- Lore that stays consistent
- Plot threads tracked across sessions
- Dialogue style preserved

**Example:**
```
User: "What was my protagonist's motivation again?"
Agent: "From your character sheet [1], Maya Chen is driven by 
her father's unsolved murder. Last session you added she 
discovered the detective was involved."
```

### 4. Second Brain / Zettelkasten

**Who:** Knowledge workers, students, lifelong learners

**Use:**
- Reading notes with citations
- Idea connections (zettelkasten style)
- Concept mapping
- Retrievable learning

**Workflow:**
1. Read article → Add to `sources/`
2. Agent extracts key points with citation
3. Link to related concepts
4. Later: "What did I read about neural networks?"

### 5. Business Intelligence

**Who:** Founders, product managers, analysts

**Use:**
- Competitive intelligence
- Market research archives
- User interview synthesis
- Metric explanations

**Example:**
```
User: "Why did we choose Stripe over Square?"
Agent: "According to your decision log from January [1], 
Stripe was chosen for better international support 
and API documentation. Square was 30% cheaper but 
lacked multi-currency features you needed."
```

### 6. Healthcare & Personal Tracking

**Who:** Patients, caregivers, biohackers

**Use:**
- Symptom logs with patterns
- Medication tracking
- Doctor visit summaries
- Experiment results

**Privacy Note:** Local-first means your health data never leaves your machine.

### 7. Education & Tutoring

**Who:** Students, tutors, self-learners

**Use:**
- Study notes organized by subject
- Practice problem tracking
- Concept mastery tracking
- Revision schedules

### 8. Software Development

**Who:** Developers, DevOps, SREs

**Use:**
- Bug tracking with context
- Incident post-mortems
- Architecture decision records (ADRs)
- Snippet libraries

**Integration:**
- Link to GitHub issues
- Reference PR numbers
- Track deployment decisions

---

## Advanced Applications

### Multi-Agent Teams

Multiple agents sharing one vault:
- **Research Agent** → Finds information
- **Writing Agent** → Drafts documents  
- **Review Agent** → Checks for consistency
- All cite the same sources

### Family Knowledge Base

Shared vault for household:
- Maintenance logs
- Recipe collection with modifications
- Kid milestones and stories
- Important document references

### Compliance & Auditing

Industries requiring documentation:
- Financial decision logs
- Legal research trails
- Regulatory compliance notes
- Immutable local audit trail

---

## Integration Examples

### With Claude Code

Add to `.claude/CLAUDE.md`:
```markdown
## Memory System

Before responding, query local memory:
```bash
RECALL=$(curl -s -X POST http://127.0.0.1:7778/recall \
  -H 'Content-Type: application/json' \
  -d '{"message":"{{USER_MESSAGE}}","topic":"none"}')
```
```

### With Custom GPTs

Use OpenAI's function calling:
```python
def query_memory(query: str):
    """Query BrainPass for relevant context"""
    return requests.post(
        "http://127.0.0.1:7778/recall",
        json={"message": query, "topic": query}
    ).json()
```

### With Obsidian Plugins

Community plugins can:
- Auto-sync vault changes
- Trigger recalls on note open
- Visualize knowledge graph

---

## Success Patterns

### Do:
- ✅ Write daily logs with dates
- ✅ Use consistent file naming
- ✅ Link related notes with `[[wikilinks]]`
- ✅ Tag important concepts
- ✅ Review and curate weekly

### Don't:
- ❌ Dump raw data without context
- ❌ Use vague filenames
- ❌ Forget to cite sources
- ❌ Let vault become unorganized
- ❌ Skip the recall step

---

## Real-World Examples

### Example 1: Developer Portfolio

**User:** Job hunting, needs to remember all projects

**Setup:**
- `projects/` folder with one file per project
- Tech stack tags
- Challenge → Solution format
- Links to GitHub repos

**Result:** Can instantly recall "What did I build with React in 2025?"

### Example 2: Therapy Journey

**User:** Tracking mental health progress

**Setup:**
- `daily/` with mood + events
- `insights/` for breakthroughs
- `techniques/` that worked

**Result:** Patterns emerge, agent provides context-aware support

### Example 3: Startup Founder

**User:** Pitching investors, needs consistent story

**Setup:**
- `pitches/` with versions
- `metrics/` updated weekly
- `feedback/` from each meeting

**Result:** Never contradicts previous statements, cites traction numbers

---

## Getting Started

1. **Install** BrainPass (see INSTALL.md)
2. **Create** your first daily note
3. **Query** your agent with context
4. **Iterate** — add structure as needed

**Remember:** Your vault grows with you. Start simple.

---

## Community Ideas

Users have extended BrainPass for:
- Habit tracking with streaks
- Book/movie review databases
- Investment journaling
- Travel planning with research
- Language learning progress
- Recipe modification tracking

**What's your use case?**

---

*Built with love. Share your story.*
