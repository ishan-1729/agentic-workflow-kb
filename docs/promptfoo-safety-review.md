# Promptfoo Safety Review

## Purpose

Before any external Knowledge Base or agent-memory project is installed, cloned, executed, imported, or integrated, this project must run a promptfoo-backed safety review and write the result to SQLite and `learnings/`.

This review is a gate, not a guarantee. It is meant to catch obvious security, privacy, dependency, prompt-injection, and operational risks before implementation.

## Tooling State

As of 2026-05-09:

- `promptfoo` is not on PATH.
- The Codex app shell has Node, but not `npm` or `npx` on PATH.
- Official promptfoo docs list npm/npx/Homebrew install paths and require Node.js 20.20+ or 22.22+.
- If promptfoo is installed for this project, prefer a workspace-local setup under `.tools/` or another documented local folder. Do not silently install global tooling.
- Disable promptfoo telemetry for project runs with `PROMPTFOO_DISABLE_TELEMETRY=1`.

Sources:

- `https://www.promptfoo.dev/docs/installation/`
- `https://www.promptfoo.dev/docs/code-scanning/cli/`

## Scope

Review all KB-related candidates from `kb_candidates`, especially external projects marked:

- `deferred_promptfoo_required`
- `deferred_later_graph_memory`
- `deferred_later_graph_overlay`
- `deferred_later_semantic_search`
- `deferred_supporting_agent_interface`

The review must include, at minimum:

- Ars Contexta
- Pal
- LLM Wiki desktop app
- claude-obsidian
- Cognee
- Understand Anything
- OpenWolf
- Graphify
- Obsidian Skills
- CocoIndex-style graph/semantic backend

## Evidence Collection

Allowed before safety approval:

- Read public repository metadata, README, docs, package manifests, lockfiles, Dockerfiles, CI files, install scripts, and release notes.
- Download individual raw files or repository archives for static inspection only.
- Use internet lookup for current maintenance, license, release recency, issues, security posture, and expert commentary.
- Run promptfoo evaluations against locally written review prompts and extracted static evidence.

Not allowed before safety approval:

- Installing candidate projects.
- Running candidate project code.
- Importing candidate project modules.
- Executing candidate project scripts, Dockerfiles, postinstall hooks, examples, or CLIs.
- Using personal browser profiles, cookies, authenticated sessions, or private content.

## Review Dimensions

Each candidate should receive structured findings for:

- Repository identity and source URL.
- License and compatibility concerns.
- Maintenance/release health.
- Install surface and postinstall/script risk.
- Runtime permissions, file-system scope, network behavior, browser/profile behavior, credential handling.
- LLM/prompt-injection and data-exfiltration risks.
- Windows operational risk.
- Fit for this project's WhatsApp-to-SQLite-to-Markdown KB use case.
- Whether it can be safely used as inspiration only, static dependency, optional tool, or primary implementation.

## Output

Persist results in SQLite when possible, either by adding an idempotent safety-review table or by appending structured decision rows. Also write a checkpoint under `learnings/`.

The final recommendation must identify:

- Best KB approach after safety review.
- Best external project, if any, that is safe enough to consider later.
- Projects that remain disallowed or deferred.
- Exact next implementation goal.
