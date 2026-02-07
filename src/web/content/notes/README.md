# Notes Content Folder

Add your articles here as Markdown files.

## How to Add a New Note

1. Copy `_template.md` to a new file (e.g., `my-first-post.md`)
2. Edit the frontmatter (the stuff between `---` markers)
3. Write your content in Markdown
4. Set `published: true` when ready to go live

## Frontmatter Fields

```yaml
---
title: Your Post Title          # Required
slug: url-friendly-slug         # Optional (defaults to filename)
excerpt: Short description      # Shows on listing page
date: February 7, 2026          # Display date
author: Michael Vicenzino       # Author name
published: true                 # Set to true to publish
---
```

## File Naming

- Use lowercase with hyphens: `my-great-post.md`
- Files starting with `_` are ignored (like `_template.md`)
- The slug in frontmatter overrides the filename for URLs

## Markdown Features

- **Bold** and *italic*
- [Links](https://example.com)
- Lists (bulleted and numbered)
- Headers (## H2, ### H3, etc.)
- Code blocks with ``` 
- Blockquotes with >
- Images: `![alt text](url)`

## Tips

- Keep excerpts under 160 characters
- Use consistent date format (Month Day, Year)
- Commit and push to deploy changes
