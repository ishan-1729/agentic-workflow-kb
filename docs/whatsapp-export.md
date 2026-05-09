# WhatsApp Group Export Plan

## Required Source Material

1. Entire primary WhatsApp group about agentic optimizations and setups/workflows.
2. Messages from other WhatsApp groups tagged with phrases such as:
   - `Add to Claude Code`
   - `Add to Codex`
   - `Claude Code`
   - close variants with different casing or punctuation

## Export Policy

- Read-only only.
- Store raw exports under `imports/whatsapp_raw/`.
- Do not alter WhatsApp state.
- Prefer user-provided official exports when possible.

## Suggested Official Export Flow

Use WhatsApp's official export-chat flow for each relevant group where possible:

1. Export the primary group as a full chat export, preferably without media unless media is necessary.
2. Search other groups for the tag phrases.
3. Export the relevant groups or copy matched messages into separate files, preserving group name and date.
4. Place files in `imports/whatsapp_raw/`.
5. Add a note describing how each file was produced.

## Parser Requirements

The importer should tolerate:

- WhatsApp `.txt` exports.
- Export archives containing media and text.
- Manually saved `.txt`, `.md`, `.csv`, or `.json` excerpts.
- Missing sender or timestamp fields.

The importer must preserve raw text exactly in the database.
