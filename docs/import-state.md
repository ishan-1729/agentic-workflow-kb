# Import State

## Current Import Layout

The user added local WhatsApp group exports under `imports/`.

Observed files:

- `imports/Primary/WhatsApp Chat with Claude CodeOpenClawCodex.txt`
- `imports/Primary/Thinking_with_Visual_Primitives.pdf`
- `imports/Secondary_1/WhatsApp Chat with +91 70196 97453.txt`
- `imports/Secondary_2/WhatsApp Chat with Task List.txt`

## Scope Interpretation

- `imports/Primary/` is treated as the complete primary group export and all parsed messages are in scope.
- `imports/Secondary_*` folders are parsed but only messages matching agentic/Codex/Claude/OpenClaw-style tag patterns are inserted into the derived database.
- Raw files in `imports/` must remain untouched.

## First Import Outputs

Expected derived outputs:

- `data/db/agentic_workflow.db`
- `data/intermediate/messages_in_scope_all.jsonl`
- `data/intermediate/messages_level1_dedup.jsonl`
- `data/intermediate/links_all.jsonl`
- `data/intermediate/links_all.csv`
- `data/intermediate/import_summary.json`
