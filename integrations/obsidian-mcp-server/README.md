# Obsidian Second Brain MCP server

An MCP server that turns an Obsidian vault into a set of tools any MCP client can call - [Hermes Agent](https://github.com/NousResearch/hermes-agent) (via `discover_mcp_tools()`), Claude Desktop, Claude Code, or Cursor.

This is the connector half of [Issue #60](https://github.com/eugeniughelbur/obsidian-second-brain/issues/60): the agent gets a doorway to **use** your vault as a knowledge second brain (search it, read it, add to it) **without** the vault becoming the agent's own behavioral memory. Those stay two distinct things, as requested.

## Status

v0, live-tested at the protocol level. The vault logic (`vault_ops.py`) is pure stdlib and unit-tested, and the full MCP round-trip (a real client connecting over stdio, discovering tools, and calling search / read / save) passes via `live_test.py`. The one thing not yet done is driving it from an actual Hermes instance - see "Testing" below.

## Tools exposed

Data tools (deterministic primitives):

| Tool | What it does |
|---|---|
| `obsidian_search(query, limit=6)` | Ranked keyword search across vault notes; returns snippets + paths |
| `obsidian_read_note(path)` | Read a full note by vault-relative path (path-traversal guarded) |
| `obsidian_content_hash(content)` | Read-only exact UTF-8 SHA-256 and canonical source hash; use its `content_hash` before source deduplication |
| `obsidian_save_note(title, content, type, tags)` | Save a new AI-first note to the vault `Inbox/`; the result also reports validation, the index entry, the log line and the post-write command (see Bookkeeping) |
| `obsidian_capture(text, tags)` | Quick-capture an idea as a lightweight `type: idea` note, with the same bookkeeping |

Curator tools (guarded mutation + graph + health, per Issue #79):

| Tool | What it does |
|---|---|
| `obsidian_update_note(path, append, heading, set_fields)` | Guarded edit of an existing note: append a section and/or merge scalar frontmatter; preserves the rest verbatim, never creates, never touches `tags:` blocks, stamps `updated` |
| `obsidian_validate_note(path)` | Check a note for AI-first compliance (frontmatter keys, `## For future agent` preamble) and unresolved `[[wikilinks]]` |
| `obsidian_backlinks(target)` | List every note that links to `target` via `[[wikilink]]` |
| `obsidian_vault_health()` | Bounded structural summary: orphans, wanted notes (linked but unwritten - a wishlist, not errors), notes missing frontmatter (counts + capped samples) |

Skill tools (the higher-level behaviors, per Issue #60 - "use the skills, not just file search"):

| Tool | What it does |
|---|---|
| `obsidian_list_skills()` | List the obsidian-second-brain commands available as skills (name + description) |
| `obsidian_get_skill(name)` | Return a command's playbook (step-by-step instructions) for the agent to execute, using the data tools above for actual vault I/O |

The skill tools expose the command playbooks (e.g. `obsidian-ingest`, `idea-discovery`, `obsidian-find`) so the connecting agent runs the real skill behavior with its own model - ingest, for instance, is multi-step (it rewrites and links existing pages), so it runs as an agent-executed skill rather than a single function. Niche / agent-only / Claude-only commands (challenge, health, the scheduled agents, and the Google Calendar commands) are excluded from the exposed set. Override the commands source with `OBSIDIAN_COMMANDS_DIR` if the server is deployed away from the repo.

Saved notes follow `references/ai-first-rules.md` (frontmatter, `## For future agent` preamble, `source: mcp` marker) so connector-written notes are distinguishable from hand-authored ones.

### Create immutable raw sources

`obsidian_save_note` can create a new raw source when `type="source"`,
`source_metadata` is provided, and `path` is an explicit
`raw/articles|transcripts|pdfs|videos/YYYY-MM-DD - Title.md` path. This is a
create-only exception: existing raw notes remain protected from updates,
replacement and moves. Ordinary saves cannot write to `raw/`.

Before creation, call `obsidian_content_hash` on the source text extracted from
the article, transcript or document, then search for its returned `content_hash`
and read any matches. The hash tool returns `sha256` for the exact UTF-8 input,
`canonical_sha256`, and the first 16 characters of the canonical hash as
`content_hash`. Canonical normalization removes a leading BOM, converts CRLF to
LF, converts line-start `*` and `+` list markers to `-`, collapses whitespace,
and trims it. Article-body extraction, including removal of navigation and
metadata, is supplied by the agent; the server does not verify that semantic
choice. No shell or invented hash is needed.

The `source_metadata` object allows only these string fields:

| Field | Rule |
|---|---|
| `source_url` | Required; HTTP(S) URL, or an empty string for local/pasted text |
| `source_type` | Required; `article`, `pdf`, `transcript`, `video`, `audio`, `image` or `text` |
| `content_hash` | Required; copy the canonical 16-character hash returned by the hash tool |
| `capture_scope` | Optional; `full-local`, `bounded-local` or `url-only`; the last requires a URL |
| `supersedes` | Optional; one explicit wikilink to an existing different raw source |

Pass the retained verbatim capture as `content`. If the extracted article text
differs from that capture, also pass it as `canonical_content`. The declared
hash must match the same normalization of `canonical_content`, or of `content`
when no extraction is supplied. The server preserves the retained body exactly,
including BOM and line endings, adds no preamble, and records server-owned
`body_sha256` and `hash_basis` (`body` or `provided-extraction`). Source metadata
cannot override type, date, tags, agent or other server fields. `summary`, when
provided for a raw source, informs the catalog description only.

A `supersedes` reference must stay in the four raw-source folders and cannot
use a symlink or reparse point. It is a hash-checked read dependency of the
creation transaction; the older source is never changed. New source, catalog
entry and log line share the same create-only transaction. The catalog uses an
explicit folder section when present, or the supported `## raw` section for
these source folders. Missing sections are reported rather than guessed.

## Bookkeeping after writes

Every successful write (`save_note`, `capture`, `update_note`, `replace_text`, `move_note`) is followed by the vault's own bookkeeping, done by the server so an agent that may only write to `Inbox/` (any agent working from another project) still leaves the vault consistent:

- **validation** - the note is checked with the same rules as `obsidian_validate_note`; reported as `"validation": {"ok": true, "issues": []}`.
- **index** - a new note gets `- [[note]] - summary` under `index.md`'s section for its folder (`## Inbox/` for captures). Index layouts differ per vault, so a missing section is reported (`"index.md has no '## Inbox/' section; no entry added"`), never guessed.
- **log** - one line in the vault's operation-log convention: `**HH:MM** - capture | Title -> [[Inbox/...]] (tags: ...)` in `Logs/YYYY-MM-DD.md` when that folder exists (as `/obsidian-init` creates it, with the log frontmatter on a new day), otherwise `## [YYYY-MM-DD] capture | ...` appended to `log.md`. Reported as `"log": "Logs/2026-09-05.md"`.
- **post_write** - optional. Set `OBSIDIAN_POST_WRITE_CMD` to a command and the server runs it after the bookkeeping as `<cmd> <vault-path> <note-path> <action>`, from the vault directory, bounded by `OBSIDIAN_POST_WRITE_TIMEOUT` (seconds, default 45). This is where a git commit-and-push belongs: the server never touches git itself. Reported as `"post_write": {"ran": true, "ok": true, "detail": "ok"}`; a failure or timeout is reported, never raised, and the note stays saved. The command string is split shell-style (`shlex`); on Windows prefer a path without spaces or a small wrapper script.

Each part has its own key so `saved` alone never implies the others happened. Writes to `Logs/`, `log.md` and `index.md` themselves are never logged (no loops). `OBSIDIAN_BOOKKEEPING=0` switches validation, index and log off; the post-write command is independent of that switch.

Notes under `OBSIDIAN_LOG_EXEMPT_PREFIXES` (comma-separated folders, default `wiki/team/`, the Crew logbook) are validated and catalogued as usual but get no log line, so an agent's own activity log is not echoed into the vault log once per appended line; the report says `"log": "not logged: ..."`. Set it to an empty string to log everything. `OBSIDIAN_LOG_TZ` sets the clock for log days, `HH:MM` stamps and note dates: an IANA name (`Europe/Berlin`) or a fixed offset (`+02:00`). Unset, the server's local time is used, so a server in UTC dates late-evening entries by UTC.

## Run it

Requires the vault path in the environment and the `mcp` package:

```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"
uv run --no-project --with 'mcp<2' python integrations/obsidian-mcp-server/server.py
```

### Authenticated Streamable HTTP

For the exercised Windows/phone/cloud topology, background process settings
and physical-off acceptance sequence, see [the deployment profile](DEPLOYMENT.md).

Stdio remains the default. For a remote client, run the server behind a TLS
proxy such as Tailscale Funnel. HTTP mode is tested with the official Python
SDK `mcp==1.30.0`; use `mcp>=1.30,<2` for this transport.

```bash
export OBSIDIAN_VAULT_PATH="/path/to/synced/vault"
export OBSIDIAN_MCP_TRANSPORT=streamable-http
export OBSIDIAN_MCP_HOST=127.0.0.1
export OBSIDIAN_MCP_PORT=8420
export OBSIDIAN_MCP_PUBLIC_URL="https://your-server.your-tailnet.ts.net"
export OBSIDIAN_MCP_DISABLED_TOOLS=obsidian_move_note
export OBSIDIAN_MCP_ALLOW_FRONTMATTER=0
export OBSIDIAN_MCP_AGENT=grok-bot
export OBSIDIAN_SKILL_FLAVOR=grok-bot
# Set OBSIDIAN_MCP_API_KEY from the private service environment file.
uv run --no-project --with 'mcp>=1.30,<2' python integrations/obsidian-mcp-server/server.py
```

The MCP endpoint is `/mcp`. Every HTTP request except `GET /health` and
`HEAD /health` requires `Authorization: Bearer <key>`, including requests
within an existing MCP session. Tokens are compared in constant time. Missing,
wrong, malformed and duplicate authorization headers receive `401` without
reaching the MCP application. `/health` returns only `{"status":"ok"}`.
The API key is required before HTTP startup and must contain visible ASCII
characters without spaces. Keep its generated value out of the vault, logs,
repository and chat; store it in the private service environment file.

Only literal loopback IP addresses can be bound. The port must be from 1 to
65535. `OBSIDIAN_MCP_PUBLIC_URL` is optional for local testing, but a TLS proxy
that forwards its public hostname needs it. Use an HTTPS origin with no `/mcp`
path, credentials, query or fragment. The configured public hostname and origin
are added to FastMCP's allowlist; DNS rebinding protection remains enabled.

`OBSIDIAN_MCP_DISABLED_TOOLS` is a comma-separated list of exact tool names.
Disabled tools disappear from `tools/list` and cannot be called. Unknown names
or malformed lists refuse startup so a misspelling cannot silently weaken the
policy. There are no standalone delete, frontmatter-update or tag-management
tools in this server. `OBSIDIAN_MCP_ALLOW_FRONTMATTER=0` separately blocks the
`set_fields` argument on `obsidian_update_note`, blocks frontmatter patches, and
preserves the existing note bytes during appends. Existing-note provenance then
lives in the operation log; newly saved notes can use `OBSIDIAN_MCP_AGENT`.

HTTP mode enforces `OBSIDIAN_MCP_REQUIRE_READ_HASH=1`. Read the current note
with `obsidian_read_note`, then pass its full-file `sha256` as
`expected_sha256` to `obsidian_update_note`, `obsidian_replace_text`, or
`obsidian_move_note` when that tool is enabled. A stale hash refuses the write;
re-read and redo the change. New notes remain create-only. Stdio has no HTTP
authentication requirement and ignores the HTTP-only host, port and public URL
settings.

Notes, catalog entries and log lines use the cooperative transaction helper,
with source hashes and recoverable journals. `OBSIDIAN_TRANSACTION_HELPER`
can select an existing vault's canonical helper; otherwise the vault's
`scripts/vault_transaction.py` is preferred over the bundled helper. Vaults
with `Tasks/PA` need the matching `packet_invalidation.py` extension. Do not
remove an unresolved journal to bypass a refused write. This lock does not
lock Obsidian or coordinate edits between separately synced devices.

`OBSIDIAN_SKILL_FLAVOR=grok-bot` renders the command bank for Composio clients
without a fixed toolkit prefix. `OBSIDIAN_COMMANDS_DIR` selects the actual
customised bank. `OBSIDIAN_AI_FIRST_RULES` and `OBSIDIAN_VAULT_CONFIG` can point
at separately deployed policy files when a sync client excludes hidden files;
explicitly configured missing files fail closed. The skill list mirrors the
available bank, while each playbook reports steps requiring unavailable tools.

## Wire it into a client

Hermes Agent and most MCP clients take a launch command. Example client config entry:

```json
{
  "mcpServers": {
    "obsidian-second-brain": {
      "command": "uv",
      "args": ["run", "--no-project", "--with", "mcp<2", "python", "/abs/path/integrations/obsidian-mcp-server/server.py"],
      "env": { "OBSIDIAN_VAULT_PATH": "/path/to/your/vault" }
    }
  }
}
```

For Hermes specifically, add the server to its MCP config; Hermes picks the tools up through `discover_mcp_tools()` with zero Hermes-specific code. The same server works unchanged in Claude Desktop / Claude Code / Cursor.

## Testing

`vault_ops.py` is covered by a standalone harness (search / read / save / path-guard) - no `mcp` install needed. `live_test.py` runs the full MCP round-trip with a real client:

```bash
# read-only (safe against a real vault)
OBSIDIAN_VAULT_PATH=/path/to/vault uv run --no-project --with 'mcp<2' python live_test.py "your query"
# also write one test note to Inbox/
OBSIDIAN_VAULT_PATH=/path/to/vault uv run --no-project --with 'mcp<2' python live_test.py --save "your query"
```

Live-test checklist:
  - [x] Server starts and an MCP client completes the handshake.
  - [x] Client lists the three tools.
  - [x] Client calls `obsidian_search` (results), `obsidian_read_note` (content), `obsidian_save_note` (writes a valid AI-first note to `Inbox/`). Verified 2026-06-06 via `live_test.py` against both a throwaway vault and a real vault (read-only).
  - [ ] Connect from a real Hermes instance and confirm the tools appear via `discover_mcp_tools()`.

Transport regressions use a throwaway vault and synthetic keys, with a real
FastMCP ASGI handshake, session, `tools/list`, disabled-tool call and stdio
subprocess round-trip:

```bash
uv run --no-project --with 'mcp>=1.30,<2' --with pytest python -m pytest -q tests/test_mcp_http.py
```

The configuration/auth-wrapper tests run without MCP installed. Live protocol
tests require the MCP package and are skipped when it is absent.

## Notes

- Search is a bounded linear scan (good for small/medium vaults; large vaults want an index).
- `vault_ops.py` is intentionally dependency-free and overlaps with the memory-provider integration; the two are separate artifacts and can later share a common module if both are kept.
