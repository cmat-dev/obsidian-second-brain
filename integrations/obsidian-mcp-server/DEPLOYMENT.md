# Obsidian Sync and Composio deployment profile

This profile was exercised with a Windows PC, a phone and an always-on Ubuntu
server on 2026-10-14. It documents configuration and acceptance checks, without
including account credentials, private command files or vault contents.

The server holds an official Obsidian Headless Sync copy and exposes this MCP
server through Tailscale Funnel. Grok Bot uses the Composio custom MCP toolkit
as its vault route. The PC runs Headless Sync with the desktop Sync plugin
disabled; its desktop app continues to use the same local vault folder.

## Versions and release boundaries

The exercised application commit is
`cf77d5f5b993bc5f960d99fc21c3d3fc96a15709`, with `mcp==1.30.0` and
`obsidian-headless==0.0.14`. The main merge commit
`45a8e433af646284b426e559912e19584e13d311` has the same application tree.
The PC's native SQLite dependency and the Linux installation were checked
separately. Pin the complete npm dependency graph and Python dependencies in
each private deployment; do not infer identical installed dependencies from a
matching application commit. This document does not update a running release.

## HTTP configuration

Use this non-secret profile in a private service environment file, replacing
the example host and release paths. Generate `OBSIDIAN_MCP_API_KEY` privately
on the server and add it to that file; do not paste its value into a command,
repository, vault, log or chat. The file is root-owned with mode `0600` and is
loaded by systemd before dropping to the service account.

```dotenv
OBSIDIAN_VAULT_PATH=/srv/obsidian/vault
OBSIDIAN_MCP_TRANSPORT=streamable-http
OBSIDIAN_MCP_HOST=127.0.0.1
OBSIDIAN_MCP_PORT=8420
OBSIDIAN_MCP_PUBLIC_URL=https://your-server.your-tailnet.ts.net
OBSIDIAN_MCP_DISABLED_TOOLS=obsidian_move_note
OBSIDIAN_MCP_ALLOW_FRONTMATTER=0
OBSIDIAN_MCP_REQUIRE_READ_HASH=1
OBSIDIAN_MCP_AGENT=grok-bot
OBSIDIAN_SKILL_FLAVOR=grok-bot
OBSIDIAN_COMMANDS_DIR=/opt/obsidian-commands/releases/your-release
OBSIDIAN_TRANSACTION_HELPER=/opt/obsidian-private/releases/your-release/scripts/vault_transaction.py
OBSIDIAN_VAULT_CONFIG=/opt/obsidian-private/releases/your-release/config/vault-config.json
OBSIDIAN_AI_FIRST_RULES=/opt/obsidian-private/releases/your-release/references/ai-first-rules.md
```

Deliver the actual customised command bank and policy/runtime files separately
as immutable, hash-verified releases. Include the transaction helper's matching
`packet_invalidation.py` extension when the vault requires it. Hidden folders
do not arrive through Obsidian Sync. Do not publish this private bundle.

The tested profile exposes 12 tools; move is absent. Its private bank contained
46 commands, which is a deployment-specific count. Listing a playbook does not
provide shell access, subagents, binary export, external providers or dedicated
protected-context write facilities. Keep separately billed research APIs
disabled when the owner's policy requires it.

## Background processes and network access

Both Linux processes run as the same unprivileged account. The transaction
helper's atomic replacement creates mode-`0600` note files, so a shared group
and umask alone do not make distinct service users compatible. This choice
does not isolate the processes by OS identity. Keep releases and service files
root-owned, and grant write access only to the vault and each process's state
directory. Systemd units use `Restart=on-failure`, network-online ordering and
startup checks against actual readiness receipts, never a template marked
passed in advance.

The Windows task uses boot and login triggers, `S4U`, limited privileges,
`IgnoreNew` for overlapping triggers, retry on failure and no execution time
limit. A hidden launcher holds a file lock while the single continuous client
runs. It checks desktop Sync is disabled before starting. Registration is a
privileged setup step; S4U does not collect or store a Windows password.
Verify the task against the actual Windows account SID, not only its display
name. Logs and readiness receipts stay outside the vault.

Verify private Tailscale SSH before attaching a firewall with no public inbound
rules. Expose only the loopback MCP backend using persistent Funnel:

```sh
tailscale funnel --bg --https=443 http://127.0.0.1:8420
```

The Composio URL ends in `/mcp`. Choose API-key authentication with the
`Authorization` header and `Bearer` prefix. The account owner enters the key
privately. Confirm the enabled tools in Composio itself.

## Sync settings and acceptance

Before the first reconciliation, make a byte-verified backup and complete
account/encryption setup privately. Use bidirectional sync, `conflict` copies,
no desktop configuration syncing, and explicit machine-local folder
exclusions. Review required file types, storage and per-file limits in the
actual account. Oversized attachments may remain local under an explicitly
accepted exception; successful note sync is not proof those attachments synced.

Acceptance requires observed results:

1. Public health is content-free; missing and incorrect keys receive `401`;
   authenticated tool discovery matches the configured allowlist.
2. PC writes with the desktop app closed reach the cloud and phone. Grok can
   search, create, validate and find a note through Composio with correct
   provenance, catalog and log updates.
3. A write with a stale read hash is refused without changing current bytes.
4. An offline conflict preserves both device versions and the earlier baseline
   in the phone's version history.
5. With the PC physically shut down, Grok creates and appends through Composio.
   Both markers appear in phone Obsidian before the PC is powered on.
6. After a new Windows boot, the task starts automatically with Obsidian closed.
   The cloud write precedes that boot, both markers arrive, and the PC and cloud
   whole-file SHA-256 values match.
7. A server restart restores Sync, MCP, Tailscale and the authenticated public
   endpoint automatically.

A rejected shutdown, a stopped client or a configuration receipt is not a
passed physical-off test. Keep source hashes, service/log evidence and the
owner's phone observations distinct. Archive scratch evidence only after the
full acceptance sequence passes and the owner authorises that cleanup.

The cooperative lock serialises participating writers on one machine. It does
not lock Obsidian or Sync, and does not create a cross-device lock. Preserve
conflict copies and recover unresolved transaction journals explicitly.
