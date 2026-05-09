# Checkpoint 009: Promptfoo KB Safety Review

Date: 2026-05-09

## Scope

- Goal: perform promptfoo-backed static safety review before any KB implementation.
- Required docs and prior checkpoints were read before acting.
- `imports/` and WhatsApp data were not modified.
- No personal browser, cookies, saved sessions, CDP connection, or browser profile was used.
- No candidate GitHub project was installed, cloned, executed, imported, or run.
- SQLite remained the source of truth for candidate rows and decisions.

## Timing

- Started: 2026-05-09T12:57:36.0249931Z
- Ended/checkpoint generated: 2026-05-09T13:19:59.741677+00:00

## Promptfoo Tooling

- Node version: v24.14.0
- Local npm version: 11.14.1
- Local npm path: `<workspace>\.tools\npm\package\bin\npm-cli.js`
- promptfoo version: 0.121.11
- promptfoo path: `<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo-runner-ignore-scripts\node_modules\promptfoo\dist\src\entrypoint.js`
- promptfoo install prefix: `<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo-runner-ignore-scripts`
- promptfoo runtime dir: `<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo_config`
- Telemetry: disabled with `PROMPTFOO_DISABLE_TELEMETRY=1` for all promptfoo verification/eval commands.
- Setup note: Workspace .tools allows writes but not unlink/delete, so npm install/reify and promptfoo runtime DB use the documented local Codex memories writable root. Install used local npm bootstrap, --omit=optional, --ignore-scripts, then manually ran better-sqlite3 prebuild-install with npm_config_cache under the same local root. Telemetry disabled for verification.

Official promptfoo setup sources checked:

- https://www.promptfoo.dev/docs/installation/
- https://www.promptfoo.dev/docs/code-scanning/cli/
- https://www.promptfoo.dev/docs/providers/custom-api/
- https://www.promptfoo.dev/docs/configuration/test-cases/
- https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/

## Commands Run

- `Get-Content -Raw docs/README.md docs/handoff.md docs/operating-rules.md docs/safety-and-verification.md docs/promptfoo-safety-review.md docs/knowledge-base-review.md docs/sqlite-schema.md docs/codex-goals.md docs/cli-wake-bridge.md docs/browser-sandbox.md learnings/checkpoint-007-kb-candidate-review.md learnings/checkpoint-008-cli-wake-bridge.md`
- `uv run --no-cache python -B scripts/db_status.py`
- `node --version; Get-Command promptfoo/npm/npx; local npm bootstrap and promptfoo setup commands recorded in heartbeat/checkpoint`
- `uv run --no-cache python -B scripts/kb_safety_review.py collect-evidence`
- `$env:PROMPTFOO_DISABLE_TELEMETRY='1'; $env:PROMPTFOO_DISABLE_WAL_MODE='true'; $env:PROMPTFOO_CONFIG_DIR='<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo_config'; $env:PROMPTFOO_CACHE_PATH='<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo_cache'; $env:PROMPTFOO_LOG_DIR='<codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo_logs'; node <codex-home>\.codex\memories\agentic_workflow_tools\goal006\promptfoo-runner-ignore-scripts\node_modules\promptfoo\dist\src\entrypoint.js eval -c evals/promptfoo/kb-safety-review.yaml --no-cache --output data/safety_reviews/goal-006/promptfoo_outputs/kb-safety-results.json`
- `uv run --no-cache python -B scripts/kb_safety_review.py write-sqlite`
- `$env:PYTHONPYCACHEPREFIX='<codex-home>\.codex\memories\agentic_workflow_pycache_goal006'; uv run --no-cache python -B -m py_compile scripts\kb_safety_review.py`
- `node -c evals\promptfoo\kb_safety_provider.cjs`
- `uv run --no-cache python -B scripts/kb_safety_review.py validate`
- `uv run --no-cache python -B scripts/kb_safety_review.py checkpoint`

## Candidates Reviewed

| Candidate | Risk | Fit | Disposition |
| --- | --- | --- | --- |
| Project-owned Obsidian-compatible Markdown wiki backed by SQLite | medium | high | approve_initial_component |
| Karpathy LLM Wiki pattern | medium | high | approve_pattern_only |
| Obsidian-compatible local Markdown vault | medium | high | approve_initial_component |
| SQLite FTS5 lexical search layer | medium | high | approve_initial_component |
| Ars Contexta | medium | medium | defer_compare_or_inspiration_only |
| Pal (Personal Agent that Learns) | medium | medium | defer_compare_or_inspiration_only |
| LLM Wiki desktop app (nashsu/llm_wiki) | medium | medium | defer_compare_or_inspiration_only |
| claude-obsidian | medium | medium | defer_compare_or_inspiration_only |
| Cognee | medium | medium | defer_later_optional_backend |
| Understand Anything | medium | medium | defer_inspiration_only |
| OpenWolf | high | low | not_initial_dependency |
| Graphify | medium | medium | defer_inspiration_only |
| Obsidian Skills | medium | low | not_initial_dependency |
| CocoIndex-style graph and semantic retrieval backend | medium | medium | defer_later_optional_backend |

## Source URLs Checked

- https://api.github.com/repos/AgriciDaniel/claude-obsidian
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/commits?per_page=1
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/git/trees/main?recursive=1
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/issues?state=open&per_page=5
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/releases/latest
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/releases?per_page=5
- https://api.github.com/repos/AgriciDaniel/claude-obsidian/security-advisories?per_page=10
- https://api.github.com/repos/Lum1104/Understand-Anything
- https://api.github.com/repos/Lum1104/Understand-Anything/commits?per_page=1
- https://api.github.com/repos/Lum1104/Understand-Anything/git/trees/main?recursive=1
- https://api.github.com/repos/Lum1104/Understand-Anything/issues?state=open&per_page=5
- https://api.github.com/repos/Lum1104/Understand-Anything/releases/latest
- https://api.github.com/repos/Lum1104/Understand-Anything/releases?per_page=5
- https://api.github.com/repos/Lum1104/Understand-Anything/security-advisories?per_page=10
- https://api.github.com/repos/agenticnotetaking/arscontexta
- https://api.github.com/repos/agenticnotetaking/arscontexta/commits?per_page=1
- https://api.github.com/repos/agenticnotetaking/arscontexta/git/trees/main?recursive=1
- https://api.github.com/repos/agenticnotetaking/arscontexta/issues?state=open&per_page=5
- https://api.github.com/repos/agenticnotetaking/arscontexta/releases/latest
- https://api.github.com/repos/agenticnotetaking/arscontexta/releases?per_page=5
- https://api.github.com/repos/agenticnotetaking/arscontexta/security-advisories?per_page=10
- https://api.github.com/repos/agno-agi/pal
- https://api.github.com/repos/agno-agi/pal/commits?per_page=1
- https://api.github.com/repos/agno-agi/pal/git/trees/main?recursive=1
- https://api.github.com/repos/agno-agi/pal/issues?state=open&per_page=5
- https://api.github.com/repos/agno-agi/pal/releases/latest
- https://api.github.com/repos/agno-agi/pal/releases?per_page=5
- https://api.github.com/repos/agno-agi/pal/security-advisories?per_page=10
- https://api.github.com/repos/cocoindex-io/cocoindex-code
- https://api.github.com/repos/cytostack/openwolf
- https://api.github.com/repos/cytostack/openwolf/commits?per_page=1
- https://api.github.com/repos/cytostack/openwolf/git/trees/main?recursive=1
- https://api.github.com/repos/cytostack/openwolf/issues?state=open&per_page=5
- https://api.github.com/repos/cytostack/openwolf/releases/latest
- https://api.github.com/repos/cytostack/openwolf/releases?per_page=5
- https://api.github.com/repos/cytostack/openwolf/security-advisories?per_page=10
- https://api.github.com/repos/kepano/obsidian-skills
- https://api.github.com/repos/kepano/obsidian-skills/commits?per_page=1
- https://api.github.com/repos/kepano/obsidian-skills/git/trees/main?recursive=1
- https://api.github.com/repos/kepano/obsidian-skills/issues?state=open&per_page=5
- https://api.github.com/repos/kepano/obsidian-skills/releases/latest
- https://api.github.com/repos/kepano/obsidian-skills/releases?per_page=5
- https://api.github.com/repos/kepano/obsidian-skills/security-advisories?per_page=10
- https://api.github.com/repos/nashsu/llm_wiki
- https://api.github.com/repos/nashsu/llm_wiki/commits?per_page=1
- https://api.github.com/repos/nashsu/llm_wiki/git/trees/main?recursive=1
- https://api.github.com/repos/nashsu/llm_wiki/issues?state=open&per_page=5
- https://api.github.com/repos/nashsu/llm_wiki/releases/latest
- https://api.github.com/repos/nashsu/llm_wiki/releases?per_page=5
- https://api.github.com/repos/nashsu/llm_wiki/security-advisories?per_page=10
- https://api.github.com/repos/safishamsi/graphify
- https://api.github.com/repos/safishamsi/graphify/commits?per_page=1
- https://api.github.com/repos/safishamsi/graphify/git/trees/v7?recursive=1
- https://api.github.com/repos/safishamsi/graphify/issues?state=open&per_page=5
- https://api.github.com/repos/safishamsi/graphify/releases/latest
- https://api.github.com/repos/safishamsi/graphify/releases?per_page=5
- https://api.github.com/repos/safishamsi/graphify/security-advisories?per_page=10
- https://api.github.com/repos/topoteretes/cognee
- https://api.github.com/repos/topoteretes/cognee/commits?per_page=1
- https://api.github.com/repos/topoteretes/cognee/git/trees/main?recursive=1
- https://api.github.com/repos/topoteretes/cognee/issues?state=open&per_page=5
- https://api.github.com/repos/topoteretes/cognee/releases/latest
- https://api.github.com/repos/topoteretes/cognee/releases?per_page=5
- https://api.github.com/repos/topoteretes/cognee/security-advisories?per_page=10
- https://cocoindex.io/
- https://cocoindex.io/cocoindex-code/
- https://context7.com/agenticnotetaking/arscontexta
- https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/
- https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- https://gist.github.com/karpathy?direction=desc&sort=created
- https://github.com/AgriciDaniel/claude-obsidian
- https://github.com/Lum1104/Understand-Anything
- https://github.com/agenticnotetaking/arscontexta
- https://github.com/agno-agi/pal
- https://github.com/cocoindex-io/cocoindex
- https://github.com/cocoindex-io/cocoindex-code
- https://github.com/cytostack/openwolf
- https://github.com/kepano/obsidian-skills
- https://github.com/nashsu/llm_wiki
- https://github.com/safishamsi/graphify
- https://github.com/topoteretes/cognee
- https://llmwiki.app/
- https://obsidian.md/help/data-storage
- https://obsidian.md/help/links
- https://obsidian.md/help/plugins/backlinks
- https://obsidian.md/help/plugins/graph
- https://openwolf.com/
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/AGENTS.md
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/CLAUDE.md
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/LICENSE
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/Makefile
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/README.md
- https://raw.githubusercontent.com/AgriciDaniel/claude-obsidian/main/hooks/README.md
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/.github/workflows/ci.yml
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/.github/workflows/deploy-homepage.yml
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/CLAUDE.md
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/LICENSE
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/README.md
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/homepage/README.md
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/homepage/package.json
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.ps1
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.sh
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/package.json
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/pnpm-lock.yaml
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/package.json
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/packages/core/package.json
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/packages/dashboard/package.json
- https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/pnpm-lock.yaml
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/LICENSE
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/README.md
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/platforms/README.md
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/platforms/claude-code/hooks/README.md
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/platforms/shared/features/README.md
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/platforms/shared/templates/README.md
- https://raw.githubusercontent.com/agenticnotetaking/arscontexta/main/presets/experimental/starter/README.md
- https://raw.githubusercontent.com/agno-agi/pal/main/.github/workflows/validate.yml
- https://raw.githubusercontent.com/agno-agi/pal/main/CLAUDE.md
- https://raw.githubusercontent.com/agno-agi/pal/main/Dockerfile
- https://raw.githubusercontent.com/agno-agi/pal/main/LICENSE
- https://raw.githubusercontent.com/agno-agi/pal/main/README.md
- https://raw.githubusercontent.com/agno-agi/pal/main/pyproject.toml
- https://raw.githubusercontent.com/agno-agi/pal/main/requirements.txt
- https://raw.githubusercontent.com/cytostack/openwolf/main/.github/workflows/docs.yml
- https://raw.githubusercontent.com/cytostack/openwolf/main/LICENSE
- https://raw.githubusercontent.com/cytostack/openwolf/main/README.md
- https://raw.githubusercontent.com/cytostack/openwolf/main/docs/package-lock.json
- https://raw.githubusercontent.com/cytostack/openwolf/main/docs/package.json
- https://raw.githubusercontent.com/cytostack/openwolf/main/package.json
- https://raw.githubusercontent.com/cytostack/openwolf/main/pnpm-lock.yaml
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/.github/workflows/build.yml
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/.github/workflows/ci.yml
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/LICENSE
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/README.md
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/package-lock.json
- https://raw.githubusercontent.com/nashsu/llm_wiki/main/package.json
- https://raw.githubusercontent.com/safishamsi/graphify/v7/.github/workflows/ci.yml
- https://raw.githubusercontent.com/safishamsi/graphify/v7/AGENTS.md
- https://raw.githubusercontent.com/safishamsi/graphify/v7/LICENSE
- https://raw.githubusercontent.com/safishamsi/graphify/v7/README.md
- https://raw.githubusercontent.com/safishamsi/graphify/v7/pyproject.toml
- https://raw.githubusercontent.com/safishamsi/graphify/v7/worked/example/README.md
- https://raw.githubusercontent.com/safishamsi/graphify/v7/worked/httpx/README.md
- https://raw.githubusercontent.com/safishamsi/graphify/v7/worked/karpathy-repos/README.md
- https://raw.githubusercontent.com/safishamsi/graphify/v7/worked/mixed-corpus/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/.github/workflows/backend_docker_build_test.yml
- https://raw.githubusercontent.com/topoteretes/cognee/main/LICENSE
- https://raw.githubusercontent.com/topoteretes/cognee/main/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-frontend/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-frontend/package.json
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-mcp/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-mcp/pyproject.toml
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-starter-kit/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee-starter-kit/pyproject.toml
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee/alembic/README
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee/tasks/codingagents/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee/tasks/summarization/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee/tasks/web_scraper/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/cognee/tests/tasks/translation/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/deployment/helm/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/distributed/deploy/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/evals/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/evals/old/comparative_eval/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/evals/requirements.txt
- https://raw.githubusercontent.com/topoteretes/cognee/main/evals/src/pyproject.toml
- https://raw.githubusercontent.com/topoteretes/cognee/main/examples/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/examples/pocs/disambiguation/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/licenses/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/logs/README.md
- https://raw.githubusercontent.com/topoteretes/cognee/main/pyproject.toml
- https://www.arscontexta.org/
- https://www.promptfoo.dev/docs/code-scanning/cli/
- https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/
- https://www.promptfoo.dev/docs/configuration/test-cases/
- https://www.promptfoo.dev/docs/installation/
- https://www.promptfoo.dev/docs/providers/custom-api/
- https://www.sqlite.org/fts5.html
- https://x.com/cocoindex_io/status/2049916455286927624
- https://x.com/i/status/2039805659525644595
- https://x.com/i/status/2039906409387610408
- https://x.com/i/status/2040089501159047279

## Promptfoo Results Summary

- Config: `evals/promptfoo/kb-safety-review.yaml`
- Main result: `data/safety_reviews/goal-006/promptfoo_outputs/kb-safety-results.json`
- Per-candidate outputs: `data/safety_reviews/goal-006/promptfoo_outputs/reviews`
- Reviewed candidates: 14
- Eval pass/fail: 14 passed, 0 failed, 0 errors; assertions 56 passed / 0 failed.
- SQLite validation rows: 14 of 14

## SQLite Writes

- Table: `kb_safety_reviews` created/updated idempotently with one row per required candidate for reviewer method `goal-006-promptfoo-static-review-v1`.
- Decision: `knowledge_base_approach_after_safety_review` inserted and linked to the previous initial decision when present.
- Validation JSON: `data/safety_reviews/goal-006/validation.json`

## Goal 005 Comparison

The Goal 005 recommendation does not change after the promptfoo-backed safety review. The project-owned SQLite-to-Obsidian-compatible-Markdown approach remains the safest initial implementation because it avoids external install surfaces, runtime daemons, browser/profile handling, credential capture, and untrusted hooks while preserving SQLite provenance and readable Markdown. External projects remain useful inspiration or later comparison targets, but not implementation dependencies for the first KB.

## Recommendation

Implement the repo-owned KB next: generate source-cited Markdown under `kb/` from SQLite, keep Obsidian-compatible wikilinks/frontmatter, add backlinks/index pages, and add SQLite FTS5 lexical search. Treat external tools as deferred until the local KB baseline exists and any proposed integration gets its own isolated execution review.

## Unresolved Risks

- This was a static review. It did not install, clone, import, execute, Docker-run, or authenticate to any candidate project.
- GitHub security advisories endpoints are public when available, but missing/403/404 advisory evidence is marked unknown rather than safe.
- External projects with MCP servers, browser capture, cloud APIs, Docker/native dependencies, or broad filesystem indexing need separate isolated execution gates before any adoption.
- The workspace denies unlink/delete operations; promptfoo runtime DB and npm install artifacts are therefore in a documented local Codex memories folder, while review evidence/results stay under `data/safety_reviews/goal-006/`.

## Validation

```json
{
  "validated_at": "2026-05-09T13:19:09.537797+00:00",
  "integrity_check": "ok",
  "required_candidate_count": 14,
  "safety_review_row_count": 14,
  "missing_required_candidates": [],
  "post_safety_decision_count": 1,
  "latest_post_safety_decision": {
    "id": 2,
    "decision_key": "knowledge_base_approach_after_safety_review",
    "decided_at": "2026-05-09T13:18:23.783316+00:00",
    "supersedes_decision_id": 1
  },
  "rows": [
    {
      "candidate_name": "Ars Contexta",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_compare_or_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "CocoIndex-style graph and semantic retrieval backend",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_later_optional_backend",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Cognee",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_later_optional_backend",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Graphify",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Karpathy LLM Wiki pattern",
      "risk_rating": "medium",
      "fit_rating": "high",
      "final_disposition": "approve_pattern_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "LLM Wiki desktop app (nashsu/llm_wiki)",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_compare_or_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Obsidian Skills",
      "risk_rating": "medium",
      "fit_rating": "low",
      "final_disposition": "not_initial_dependency",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Obsidian-compatible local Markdown vault",
      "risk_rating": "medium",
      "fit_rating": "high",
      "final_disposition": "approve_initial_component",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "OpenWolf",
      "risk_rating": "high",
      "fit_rating": "low",
      "final_disposition": "not_initial_dependency",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Pal (Personal Agent that Learns)",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_compare_or_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Project-owned Obsidian-compatible Markdown wiki backed by SQLite",
      "risk_rating": "medium",
      "fit_rating": "high",
      "final_disposition": "approve_initial_component",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "SQLite FTS5 lexical search layer",
      "risk_rating": "medium",
      "fit_rating": "high",
      "final_disposition": "approve_initial_component",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "Understand Anything",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    },
    {
      "candidate_name": "claude-obsidian",
      "risk_rating": "medium",
      "fit_rating": "medium",
      "final_disposition": "defer_compare_or_inspiration_only",
      "reviewed_at": "2026-05-09T13:18:23.783316+00:00"
    }
  ]
}
```

## Next Work Correction

After orchestrator audit, this is self-work rather than a CLI goal. The project-owned SQLite-to-Markdown KB generator and FTS5 lexical search baseline should be implemented directly by the orchestrator app because it is deterministic, bounded local integration work after the Goal 005/Goal 006 decision was already made.

The next appropriate CLI `/goal` should be the exhaustive unresolved-link scrape retry after the baseline KB exists. That phase is long-running, retry-heavy, and has a clear stopping condition: every link is either successfully captured or has a terminal logged reason.
