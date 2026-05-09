# Safety And Verification

## GitHub Projects

Before installing, running, or integrating any GitHub project discovered from WhatsApp or scraped links:

1. Inspect repository metadata and README.
2. Review install scripts, package scripts, Dockerfiles, CI, and lockfiles.
3. Check dependencies for risky postinstall behavior.
4. Run promptfoo-based evaluations or review prompts against the project claims and safety assumptions.
5. Prefer an isolated environment for execution.
6. Document the decision in `learnings/`.

## promptfoo Role

promptfoo should be used as a repeatable evaluation harness for:

- Testing claims made by candidate projects.
- Evaluating prompt/workflow quality where relevant.
- Checking whether a downloaded agentic project behaves within expected boundaries.
- Recording pass/fail criteria before adoption.

For Knowledge Base tooling, run the promptfoo-backed safety review before implementation. The review may inspect public static files and repository metadata, but must not install, import, or execute candidate project code until the safety gate explicitly allows it.

Local tooling note: as of 2026-05-09, `promptfoo` is not on PATH and this shell has Node but not npm/npx. Use `docs/promptfoo-safety-review.md` for the required workspace-local setup and telemetry-disabled execution rules.

## Internet Verification

Use internet sources when:

- A tool or method is unfamiliar.
- The item may have changed recently.
- Expert reviews, maintenance status, or limitations matter.
- A Knowledge Base candidate is being compared for adoption.

Prefer primary sources such as official docs, repositories, release pages, and author posts. Use secondary reviews as supporting evidence, not sole proof.
