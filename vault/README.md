# Vault Structure

## Folders

- **daily/** — session logs, daily entries
- **topics/** — curated knowledge, concepts
- **people/** — important people in your life
- **projects/** — active work and goals
- **sources/** — external sources (articles, videos, PDFs)

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

- [[related-topic]]
- [[person-name]]
```

## Linking

Use Obsidian wikilinks `[[File Name]]` to connect notes. Obsidian will render
the graph view and backlinks. The Librarian itself uses **keyword search** over
file contents — it doesn't follow wikilinks, but well-linked notes tend to
contain the right keywords anyway, so they get found.
