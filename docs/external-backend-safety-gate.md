# External Backend Safety Gate

## Purpose

External graph, vector, memory, and semantic-search backends remain optional and gated. The gate is not a permanent ban: it exists so an external project can move from static evidence, to sandboxed inspection, to sandboxed prototype, and only later to any private-data integration.

External projects must not be installed, cloned, imported, executed, or integrated until the project has a documented static review, promptfoo-backed risk review, and explicit orchestrator/user approval for that stage.

This gate covers candidates such as Cognee, Understand Anything, Graphify, Obsidian Skills, and CocoIndex-style graph or semantic retrieval backends.

## Current Allowed Work

Allowed before stage approval:

- Read the local SQLite `kb_candidates` and `kb_safety_reviews` rows.
- Generate a local safety matrix with `scripts/external_backend_safety_matrix.py`.
- Inspect public project metadata, raw files, docs, manifests, Dockerfiles, CI files, and release notes as static text only.
- Run project-owned promptfoo review prompts against collected static evidence.

Not allowed before stage approval:

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

## Graphify Code-Only Sandbox

After Graphify has passed the static/promptfoo stage and the user/orchestrator has approved sandboxed execution, use the project-owned wrapper instead of running Graphify directly:

```powershell
uv run --no-cache python -B scripts\run_graphify_sandbox.py `
  --graphify-project data\external_sandbox\graphify-<timestamp> `
  --source scripts
```

The wrapper copies the allowed source path into ignored `data/external_sandbox/`, clears common LLM/API credential environment variables, refuses private/generated roots, and runs only Graphify's code-only `update` command.

## Promotion Gates

1. Static inventory exists for every deferred backend candidate.
2. Public-source evidence is current and cites primary project sources where possible.
3. promptfoo review covers license, maintenance, install/postinstall risk, dependency risk, runtime permissions, network behavior, credential handling, browser/profile behavior, prompt-injection and data-exfiltration risk, Windows operational risk, and fit for this SQLite-to-Markdown KB.
4. SQLite has a `kb_safety_reviews` row for each candidate and a decision row documenting whether the baseline architecture changes.
5. After a candidate passes the static/promptfoo gate, sandboxed GitHub checkout is allowed under ignored `data/external_sandbox/` for deeper inspection, with no private corpus, no credentials, no browser profile, and no candidate code execution unless the next gate explicitly approves execution.
6. After sandboxed inspection, a separate sandbox prototype plan may approve install/run of one candidate against synthetic fixture data only.
7. Private WhatsApp exports, private SQLite data, generated private KB pages, credentials, browser profiles, cookies, and storage state remain out of scope until a later explicit private-data integration gate.

## Expected Outcome

The default expectation remains conservative: keep the repo-owned SQLite-backed Markdown KB as the source of truth, use local FTS and deterministic intent search first, and treat external graph/vector systems as comparison targets until they pass the relevant gate. Passing a gate should enable the next controlled stage; it should not be interpreted as "never use external GitHub."
