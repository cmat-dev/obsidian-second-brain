"""Compile command prose for MCP-only Grok Bot clients.

The build adapter and the live skill endpoint use the same transformations.
This changes platform instructions, never grants tools or vault authority.
"""

from __future__ import annotations

import argparse
import re
import sys

# Keep this explicit: the conformance test compares it to the decorated server
# functions, including parameter names, without importing the MCP package.
TOOL_SIGNATURES = {
    "obsidian_search": "query, limit",
    "obsidian_read_note": "path, offset, limit",
    "obsidian_content_hash": "content",
    "obsidian_save_note": "title, content, type, tags, path, summary, source_metadata, canonical_content",
    "obsidian_update_note": "path, append, heading, set_fields, expected_sha256",
    "obsidian_replace_text": "path, old_text, new_text, expected_sha256",
    "obsidian_move_note": "source, destination, expected_sha256",
    "obsidian_capture": "text, tags",
    "obsidian_validate_note": "path",
    "obsidian_backlinks": "target",
    "obsidian_vault_health": "",
    "obsidian_list_skills": "",
    "obsidian_get_skill": "name",
}

_TOOL_PURPOSES = (
    "search the vault; results may be capped",
    "read a note; follow next_offset until EOF",
    "hash provided source text for ingest deduplication; no vault write",
    "create a new note; use type, never note_type",
    "append or apply permitted scalar frontmatter changes to an existing note",
    "replace one unique exact anchor in an existing note",
    "move an existing note only when this tool is exposed and authorised",
    "capture an idea with optional tags",
    "validate a note against the AI-first spec",
    "find notes linking to a target",
    "get bounded structural counts and samples",
    "discover the available command playbooks",
    "retrieve a named command playbook",
)


def preamble() -> str:
    """The public tool contract and execution limits for MCP-only skills."""
    tools = "\n".join(
        f"- `{name}({parameters})` - {purpose}"
        for (name, parameters), purpose in zip(TOOL_SIGNATURES.items(), _TOOL_PURPOSES)
    )
    return f"""## Setup (read first)

**MCP vault I/O.** Use the connected Obsidian toolkit for every vault operation.
When tools arrive through Composio, discover them with its tool search and match
the `obsidian_*` suffix; the toolkit may add its own prefix. Use only tools
actually exposed by the deployment and permitted by the vault instructions.

{tools}

**Context.** At the start of a vault task, read the vault's `AGENTS.md` and
`CLAUDE.md` when present, then the shared `_Claude-Context/_CLAUDE(0).md` (or
`_CLAUDE.md` where the vault uses that manual), then `index.md`. Follow the vault's
navigation and authority rules, and reuse context already read in this task.
Use vault-relative paths. Finish every paginated read before relying on it.

**Writes.** Search and read before editing; use the returned source hash when the
write tool accepts one. On a changed-on-disk refusal, re-read and reconsider the
edit; never force or reuse a stale hash. Use create tools only for new notes,
and exact replacement or append tools for existing ones. After every successful
write, call `obsidian_validate_note` for the written path and inspect the
bookkeeping result. A saved note does not prove its index and log updates passed.
Vault policy controls which fields or operations are allowed; a tool's presence
does not grant permission.

**Source ingest.** Before deduplicating an extracted source, pass
the canonical extracted text to `obsidian_content_hash` and use its returned
`content_hash` in the vault search and source metadata. Do not invent a hash or
run a shell recipe. Preserve the captured source body exactly in `content`.
Create a source only at an explicit new dated `.md` path in `raw/articles`,
`raw/transcripts`, `raw/pdfs`, or `raw/videos`, with `type="source"` and
`source_metadata` containing `source_url`, `source_type`, and the returned
`content_hash`. Supported `source_type` values are `article`, `pdf`, `transcript`,
`video`, `audio`, `image`, and `text`. A local or pasted source may have an empty
`source_url`. For a changed source, an optional `supersedes` must name the exact
existing raw note as `[[raw/articles/Old source]]` (or another allowed source
folder); the old note stays unchanged.
If the captured body differs from the canonical extraction, also pass that
extraction as `canonical_content`; the server records the hash basis and the
saved body's own hash separately. Use actual extracted text, for example article
text with navigation removed; a URL alone is not an extraction. Preserve URL-only
or bounded capture limits in claims derived from it. Set `capture_scope` to
`full-local`, `bounded-local`, or `url-only` from the text actually retained.
Existing raw sources
are immutable: deduplicate before creation and never overwrite, append, patch,
or change their frontmatter.

**Execution limits.** Perform each work group yourself, in sequence. Do not spawn
agents or separate processes. This toolkit has no shell or general filesystem
execution tool: do not run Python recipes on another machine or invent a remote
execution tool. For a step requiring an unavailable capability, complete the
supported steps and report that specific gap. Use the embedded AI-first rule;
if another required reference is unavailable, report it before dependent writes.
Follow the same unattended-routine limits as the other authorised vault writers.

"""


def rewrite_body(text: str) -> str:
    """Replace platform tool vocabulary without guessing arguments from prose."""
    replacements = (
        (r"\b(?:Read|read) `([^`]+\.md)`", r'use `obsidian_read_note` for `\1`'),
        (r"\bRead tool\b", "MCP obsidian_read_note"),
        (r"\bWrite tool\b", "MCP obsidian_save_note for new notes"),
        (r"\bEdit tool\b", "MCP obsidian_replace_text or obsidian_update_note"),
        (r"\b(?:Glob|Grep) tool\b", "MCP obsidian_search followed by complete note reads"),
        (r"\b(?:Task|Agent) tool\b", "sequential work in this agent"),
        (r"\bBash tool\b", "an unavailable shell capability (report this step)"),
        (r"\bWebFetch tool\b", "an available web-reading tool"),
        (r"\bWebSearch tool\b", "an available web-search tool"),
        (r"\bTodoWrite tool\b", "track tasks in the response"),
        (r"\bAskUserQuestion tool\b", "ask the user"),
        (r"\bSkill tool\b", "MCP obsidian_get_skill"),
        (r"(?i)\bspawn parallel subagents\b", "Process the work groups yourself in sequence"),
        (r"(?i)\bspawn (?:a |an )?(?:parallel )?subagents?\b", "Perform the work yourself"),
        (r"(?i)\bsubagents?\b", "work groups"),
        (r"(?i)\bafter all agents complete\b", "After all work groups are complete"),
        (r"(?i)\bsimultaneously\b", "in sequence"),
        (r"(?i)\b(?:execute|run) `/([a-z][a-z0-9-]*)([^`]*)`",
         r'Retrieve `\1` with `obsidian_get_skill` and follow it\2'),
        (r"(?<!\w)/((?:obsidian-|vault-deep-|idea-discovery|research(?:-deep)?|notebooklm|youtube|x-read|x-pulse|podcast|create-command)[a-z0-9-]*)",
         r"\1"),
        (r"\.claude/commands/([a-z0-9-]+)\.md", r'`obsidian_get_skill("\1")`'),
        (r"SKILL_ROOT", "skills/obsidian-core"),
        (r"its absolute path was given at session start as \*\*Skill root\*\*",
         "this server-side path is not a client filesystem path"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text.strip()


def render_instructions(body: str, ai_rules: str | None = None) -> str:
    """Render live instructions with the same preamble as a compiled skill."""
    instructions = preamble() + rewrite_body(body)
    if ai_rules:
        instructions += "\n\n---\n\n## AI-first vault rule (embedded)\n\n" + rewrite_body(ai_rules)
    return instructions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preamble", action="store_true")
    args = parser.parse_args()
    # Deterministic UTF-8 when the adapter pipes output on Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    if args.preamble:
        sys.stdout.write(preamble())
    else:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.write(rewrite_body(sys.stdin.read()) + "\n")


if __name__ == "__main__":
    main()
