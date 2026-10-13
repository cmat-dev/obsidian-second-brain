#!/usr/bin/env bash
# =============================================================================
# adapters/grok-bot/adapter.sh - Grok Bot / Sand platform adapter
# =============================================================================
# Grok Bot (aka Sand) reads the obsidian-second-brain MCP server for vault I/O
# and runs SKILL.md workflow files for playbooks. This adapter compiles the
# platform-neutral commands/ into Grok-runnable SKILL.md files.
#
# Emits, at the dist root:
#   skills/<name>/SKILL.md        - one skill per command (45; calendar is
#                                   excluded). Frontmatter is name + description
#                                   (when to use). Body tells the agent to use
#                                   MCP obsidian_* tools for all vault I/O.
#   skills/obsidian-core/         - the shared engine skill carrying references/,
#                                   scripts/, and pyproject.toml for Python-backed
#                                   commands.
#   INSTALL.md                    - how workflows and MCP work on Grok Bot / Sand.
#
# Design notes:
#   - Each skill body opens with MCP vault I/O instructions telling the agent to
#     use obsidian_* tools rather than filesystem operations.
#   - references/ai-first-rules.md is embedded in every command skill so the
#     non-negotiable write spec survives even a cherry-picked install.
#   - The trigger policy (proactive vs explicit) is encoded in each description.
#   - Grok Bot has no hook runtime, so no SessionStart or PostToolUse hooks.
#   - Python-backed research commands still need the scripts/ directory accessible;
#     the preamble tells the agent how to resolve that path.
# =============================================================================

GROK_PLATFORM="grok-bot"
GROK_SKILLS_DIR="skills"
GROK_CORE="obsidian-core"
GROK_SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/python-interpreter.sh
source "$GROK_SOURCE_ROOT/scripts/python-interpreter.sh"

_grok_resolve_python() {
  if [[ -z "${GROK_PYTHON:-}" ]]; then
    GROK_PYTHON="$(osb_python)" || {
      echo "error: the Grok skill compiler requires Python" >&2
      return 1
    }
  fi
}

adapter_build() {
  local src="$1" dst="$2"
  _grok_resolve_python

  _grok_emit_skills "$src/commands" "$dst/$GROK_SKILLS_DIR" "$src/references/ai-first-rules.md"
  _grok_emit_core "$src" "$dst/$GROK_SKILLS_DIR/$GROK_CORE"
  _grok_emit_install_hint "$dst"
}

# Emit one Grok Bot skill per command at skills/<name>/SKILL.md.
_grok_emit_skills() {
  local src="$1" dst="$2" ai_rules="$3"
  [[ -d "$src" ]] || return 0
  local f name desc triggers category trigmode trig_clean out
  for f in "$src"/*.md; do
    [[ -f "$f" ]] || continue
    should_include "$f" "$GROK_PLATFORM" || continue

    name="$(basename "$f" .md)"
    desc="$(parse_frontmatter "$f" description)"
    triggers="$(parse_frontmatter "$f" triggers_en)"
    category="$(parse_frontmatter "$f" category)"
    trigmode="$(parse_frontmatter "$f" trigger-mode)"
    [[ -z "$category" ]] && category="other"
    [[ -z "$desc" ]] && desc="Run the $name command of the obsidian-second-brain skill."
    desc="$(strip_quotes "$desc")"

    # Fold English triggers into the description for implicit selection.
    if [[ -n "$triggers" ]]; then
      trig_clean="$(format_triggers "$triggers")"
      [[ -n "$trig_clean" ]] && desc="$desc Triggers: $trig_clean."
    fi

    # Encode the selection policy.
    desc="$(with_trigger_policy "$desc" "$trigmode")"

    mkdir -p "$dst/$name"
    out="$dst/$name/SKILL.md"
    {
      echo "---"
      echo "name: $name"
      printf 'description: "%s"\n' "${desc//\"/\\\"}"
      echo "---"
      echo
      _grok_preamble
      _grok_rewrite_command_body "$f"
      echo
      echo "---"
      echo
      echo "## AI-first vault rule (embedded)"
      echo
      echo "The write spec below is non-negotiable for every note this skill creates or"
      echo "updates. It is embedded here so it applies even on a partial install."
      echo
      $GROK_PYTHON "$GROK_SOURCE_ROOT/scripts/grok_skills.py" < "$ai_rules"
    } > "$out"

    # Rewrite bare references/ paths to .agents/skills/obsidian-core/references/
    # (the perl adds the leading dot, so pass without it)
    rewrite_platform_paths "$out" "agents/skills/obsidian-core"
  done
}

# The MCP-first preamble prepended to every command skill body.
_grok_preamble() {
  _grok_resolve_python
  $GROK_PYTHON "$GROK_SOURCE_ROOT/scripts/grok_skills.py" --preamble
}

# Rewrite command body to use MCP tools instead of filesystem operations.
# Transform Read/Write/Edit tool language into MCP tool calls.
_grok_rewrite_command_body() {
  local file="$1"
  _grok_resolve_python
  command_body "$file" | $GROK_PYTHON "$GROK_SOURCE_ROOT/scripts/grok_skills.py"
}

# Emit the shared obsidian-core skill carrying references/ and scripts/.
_grok_emit_core() {
  local src="$1" dst="$2"
  mkdir -p "$dst"

  # references/
  if [[ -d "$src/references" ]]; then
    mkdir -p "$dst/references"
    cp -R "$src/references/." "$dst/references/"
  fi
  # scripts/ + pyproject.toml (for Python-backed research commands)
  if [[ -d "$src/scripts" ]]; then
    mkdir -p "$dst/scripts"
    cp -R "$src/scripts/." "$dst/scripts/"
    copy_vault_ops "$src" "$dst"  # see adapters/lib.sh (#332)
  fi
  [[ -f "$src/pyproject.toml" ]] && cp "$src/pyproject.toml" "$dst/pyproject.toml"

  # SKILL.md - not invoked directly, just carries the support files
  cat > "$dst/SKILL.md" <<'EOF'
---
name: obsidian-core
description: "Shared engine for the obsidian-second-brain skills - the AI-first write spec (references/), the Python research toolkit (scripts/), and its uv project (pyproject.toml). Support files only; the other skills reference it. Do not invoke directly."
---

## What this is

The shared support tree the other obsidian-second-brain skills depend on. It is
not a task skill - do not run it on its own.

- `references/` - shared specs. `references/ai-first-rules.md` is the canonical,
  non-negotiable vault-write spec; `vault-schema.md`, `folder-map.md`, and
  `freshness-policy.md` back the other skills. These paths are relative to the
  install root, which is load-bearing: if one does not resolve from your working
  directory, search upward for it, and say so before writing if you still cannot
  read it. Every command skill also embeds the AI-first spec inline, so the rule
  survives an unreachable path - but an unreachable path must never pass in
  silence.
- `scripts/` - Python helpers for the research toolkit (research, research-deep,
  x-read, x-pulse, youtube, podcast, notebooklm, obsidian-architect). The command
  skills invoke them as `uv run -m scripts.research.<name> ...` or
  `uv run scripts/<name>.py ...`.
- `pyproject.toml` - makes this directory a self-contained uv project, so both
  modules and dependencies resolve without a separate install step.

When a command needs these, locate the obsidian-core skill directory in your
skill tree and reference it there.
EOF
}

_grok_emit_install_hint() {
  local dst="$1"
  local GROK_CMD_COUNT=0
  GROK_CMD_COUNT="$(find "$dst/$GROK_SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d \
                    ! -name "$GROK_CORE" 2>/dev/null | wc -l | tr -d ' ')"
  cat > "$dst/INSTALL.md" <<EOF
# Install on Grok Bot / Sand

This build contains ${GROK_CMD_COUNT} compiled command skills and the shared
skills/${GROK_CORE}/ support tree. Vault operations use the connected Obsidian
MCP toolkit. A client such as Composio may prefix tool names; discover tools by
the obsidian_* suffix rather than requiring a particular server name.

## Recommended live playbooks

Connect the MCP server through your client, then use obsidian_list_skills and
obsidian_get_skill. With OBSIDIAN_SKILL_FLAVOR=grok-bot, the server returns the
same MCP-only platform instructions as this adapter. This keeps playbooks
current without copying every command into the Bot. Set OBSIDIAN_COMMANDS_DIR
to your maintained command bank on the server; sync does not deploy hidden
command directories automatically.

Create one private entry skill that loads the vault manual, shared context and
index, discovers tools, and fetches the named playbook. Follow the vault's
permissions, source-hash refusals, after-write validation, and unattended limits.

## Compiled skills

For clients supporting workflow files, place skills/<name>/SKILL.md in the
client's documented skill location. The exact loading mechanism depends on the
client. Verify access by discovering tools and retrieving a playbook; an agent's
claim that a skill exists is not a connection test.

## Capability limits

The toolkit supports note reads, guarded writes, search, backlinks, validation,
and bounded structural health. It exposes no shell or general filesystem tool.
A Python recipe in a playbook is not remotely executable through the toolkit;
report the unsupported step instead of inventing a tool or another vault route.
The support files ship for administrators and local harnesses. Hooks and the
Claude-only calendar command remain excluded from this build.

## Verification

1. Call obsidian_list_skills through the connected toolkit.
2. Retrieve obsidian-find and search a known fixture note.
3. Create a scratch note, inspect validation/index/log results, then validate it.
4. Re-read the scratch note and verify guarded updates refuse a stale hash.

Keep API keys outside skills, commands, repositories and vault notes.
EOF
}
