# Vault Structure

## Folders

- **daily/** — Session logs, daily entries
- **topics/** — Curated knowledge, concepts
- **people/** — Important people in your life
- **projects/** — Active work and goals
- **sources/** — External sources (articles, videos, PDFs)

## File Format

All files are Markdown with optional YAML frontmatter:

```markdown
---
date: 2026-04-15
type: daily-log
tags: [memory, important]
---

# Title

Content here...

## Links

- [[Related Topic]]
- [[Person Name]]
```

## Linking

Use Obsidian wikilinks `[[File Name]]` to connect notes.
The Librarian follows these links when searching.
