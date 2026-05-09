# External Backend Safety Gate

## Purpose

External graph, vector, memory, and semantic-search backends remain optional and gated. They must not be installed, cloned, imported, executed, or integrated until the project has a documented static review, promptfoo-backed risk review, and explicit orchestrator/user approval.

This gate covers candidates such as Cognee, Understand Anything, Graphify, Obsidian Skills, and CocoIndex-style graph or semantic retrieval backends.

## Current Allowed Work

Allowed before approval:

- Read the local SQLite `kb_candidates` and `kb_safety_reviews` rows.
- Generate a local safety matrix with `scripts/external_backend_safety_matrix.py`.
- Inspect public project metadata, raw files, docs, manifests, Dockerfiles, CI files, and release notes as static text only.
- Run project-owned promptfoo review prompts against collected static evidence.

Not allowed before approval:

- Installing, cloning, importing, executing, or running external GitHub projects.
- Running candidate Dockerfiles, scripts, CLIs, examples, postinstall hooks, or package managers inside candidate source trees.
- Giving candidate tools access to private WhatsApp exports, the SQLite DB, generated KB pages, browser profiles, cookies, credentials, or storage state.
- Using credentialed browser/profile scraping or undocumented service endpoints.

## Inventory Command

```powershell
uv run --no-cache python -B scripts\external_backend_safety_matrix.py `
  --json-output data\safety_reviews\external_backend_matrix.json `
  --markdown-output data\safety_reviews\external_backend_matrix.md
```

The script opens SQLite read-only and writes only local report artifacts under ignored `data/` paths.

## Promotion Gates

1. Static inventory exists for every deferred backend candidate.
2. Public-source evidence is current and cites primary project sources where possible.
3. promptfoo review covers license, maintenance, install/postinstall risk, dependency risk, runtime permissions, network behavior, credential handling, browser/profile behavior, prompt-injection and data-exfiltration risk, Windows operational risk, and fit for this SQLite-to-Markdown KB.
4. SQLite has a `kb_safety_reviews` row for each candidate and a decision row documenting whether the baseline architecture changes.
5. Only after approval, create a separate sandbox prototype plan with no private corpus access by default.

## Expected Outcome

The default expectation remains conservative: keep the repo-owned SQLite-backed Markdown KB as the source of truth, use local FTS and deterministic intent search first, and treat external graph/vector systems as comparison targets until they pass the gate.
