# Checkpoint 019: Graphify Sandbox Gate

Date: 2026-05-10

## Scope

- Corrected the external-backend policy: promptfoo/static review is a gate that can unlock staged external GitHub use, not a permanent ban.
- Reopened GitHub issue `#1` to track gated external backend progression.
- Advanced Graphify from static review to sandboxed checkout and synthetic/public-code execution only.

## Gate Inputs

- Existing promptfoo result: `data/safety_reviews/goal-006/promptfoo_outputs/reviews/graphify.json`
- Existing result: overall risk `medium`, fit `medium`, disposition `defer_inspiration_only`
- GitHub repo checked: `safishamsi/graphify`
- Default branch: `v7`
- License: MIT

## Commands Run

- `gh issue reopen 1 --repo ishan-1729/agentic-workflow-kb`
- `gh repo view safishamsi/graphify --json nameWithOwner,defaultBranchRef,licenseInfo,pushedAt,url`
- `git clone --depth 1 --branch v7 https://github.com/safishamsi/graphify.git data\external_sandbox\graphify-20260510-051020`
- Static inspection with `rg` over cloned source for install, credential, browser, deletion, subprocess, and network surfaces.
- `uv run --no-cache --project data\external_sandbox\graphify-20260510-051020 python -m graphify --help`
- `uv run --no-cache --project data\external_sandbox\graphify-20260510-051020 python -m graphify extract <tiny-code-sample> --out <sandbox> --no-cluster`
- `uv run --no-cache --project data\external_sandbox\graphify-20260510-051020 python -m graphify update <tiny-code-sample>`
- `uv run --no-cache --project data\external_sandbox\graphify-20260510-051020 python -m graphify update <copied-public-scripts-tree>`
- `uv run --no-cache python -B scripts\run_graphify_sandbox.py --graphify-project data\external_sandbox\graphify-20260510-051020 --source scripts`

## Results

- Sandboxed checkout succeeded under ignored `data/external_sandbox/`.
- `uv run --project` created an isolated `.venv` inside the sandboxed clone and installed Graphify plus dependencies there.
- `graphify --help` succeeded.
- `graphify extract` on a tiny code-only sample failed because the command requires an LLM API key even for this path.
- `graphify update` on the tiny code-only sample succeeded with no LLM/API key: 5 nodes, 5 edges, 2 communities, 0 token cost.
- `graphify update` on a copied public `scripts/` tree succeeded with no LLM/API key: 285 nodes, 669 edges, 13 communities, 0 token cost.
- Added `scripts/run_graphify_sandbox.py`, a project-owned wrapper that refuses private roots, copies allowed source into ignored sandbox storage, clears common LLM/API credential environment variables, and runs only Graphify's code-only `update` command.
- Wrapper run on `scripts/` succeeded with no LLM/API key: 295 nodes, 685 edges, 14 communities.
- The public-scripts graph report surfaced useful structure: core hubs included `run()`, `Page`, `collect_evidence()`, `build_pages()`, `run_ingest()`, `wikilink()`, `page_for_message()`, `classify_items()`, and `create_fixture()`.

## Safety Notes

- No private WhatsApp exports, private SQLite DB, generated private KB pages, browser profile, cookies, storage state, or credentials were given to Graphify.
- API-key environment variables were cleared for the sandbox execution.
- Graphify static inspection still shows medium-risk adoption surfaces: hook installers, uninstall/purge deletion paths, optional API-key backends, external LLM extraction, browser-visible HTML output, and credential-sensitive backend choices.
- The candidate is acceptable for sandboxed code-only `graphify update` against synthetic/public code copies. It is not yet approved for private corpus integration, hook installation, Graphify `install`, Graphify `extract` with LLM backends, or running against the repository root.

## Next Gate

If Graphify is pursued further, add a project-owned `.graphifyignore`/sandbox wrapper and run only against a copied public-safe tree first. Private KB/corpus usage requires a separate integration gate that explicitly excludes `imports/`, `data/`, generated private `kb/`, credentials, browser profiles, and hook installation.
