# obsidian-second-brain

A Claude skill that turns your Obsidian vault into a living second brain — operated autonomously across every Claude surface.

Instead of manually saving notes, Claude reads your conversations and writes directly to your vault: creating daily notes, logging dev sessions, updating kanban boards, tracking people, capturing decisions — and always propagating changes everywhere they belong.

---

## Install

Two commands. That's it.

```bash
# 1. Clone the skill
git clone https://github.com/eugeniughelbur/obsidian-second-brain ~/.claude/skills/obsidian-second-brain

# 2. Run setup (wires the hook, sets vault path, optionally configures MCP)
bash ~/.claude/skills/obsidian-second-brain/scripts/setup.sh "/path/to/your/vault"
```

Then open Claude Code in your vault directory and run:

```
/obsidian-init
```

Claude scans your vault structure and generates a `_CLAUDE.md` — its operating manual for your specific vault. That's the file that makes every Claude surface (Desktop, Code, VS Code, terminal) behave consistently in your vault from that point forward.

**New vault? Bootstrap from scratch instead:**

```bash
python ~/.claude/skills/obsidian-second-brain/scripts/bootstrap_vault.py \
  --path ~/my-vault \
  --name "Your Name" \
  --jobs "Company Name"
```

Creates a complete vault with folders, templates, kanban boards, a Home dashboard, and a pre-filled `_CLAUDE.md`. Then run `setup.sh` pointing at the new path.

---

## What It Does

### The core idea: `_CLAUDE.md`

A plain markdown file at your vault root that tells every Claude surface exactly how your vault works — folder structure, naming conventions, frontmatter schemas, what to auto-save, what to ask first. No memory needed. Every session starts with full context.

### Propagation rule

Nothing gets saved in isolation. Create a project → it appears on the kanban board and in today's daily note. Complete a task → it's logged in the project, the board, and the daily note. Every write ripples everywhere it belongs.

### Search before write

Claude searches for existing notes before creating new ones. No duplicates, no vault rot.

---

## Features

| Feature | What it does |
|---|---|
| **14 slash commands** | Every common vault operation — all smart, context-aware |
| **Background agent** | Fires after every compaction, silently propagates updates to the vault |
| **Scheduled agents** | Morning briefing, nightly close-out, weekly review, Sunday health check |
| **Parallel subagents** | Complex commands spawn parallel agents per note type — faster, more thorough |
| **Vault health check** | Audits for broken links, duplicates, orphans, stale tasks, missing frontmatter |
| **Bootstrap script** | One command creates a complete production-ready vault from nothing |

---

## Commands

14 slash commands usable from any Claude surface. Each one searches before writing, handles typos, and propagates changes everywhere they belong.

| Command | What it does |
|---|---|
| `/obsidian-save` | Reads the whole conversation and saves everything worth keeping — decisions, tasks, people, learnings |
| `/obsidian-daily` | Creates or updates today's daily note, pre-filled from conversation context |
| `/obsidian-log` | Logs a work or dev session — infers the project, creates the log, links it everywhere |
| `/obsidian-task [desc]` | Adds a task to the right kanban board with inferred priority and due date |
| `/obsidian-person [name]` | Creates or updates a person note; logs the interaction in the daily note |
| `/obsidian-decide [topic]` | Extracts decisions and logs them in the right project's Key Decisions section |
| `/obsidian-capture [idea]` | Quick idea capture — saves to Ideas/ and mentions in the daily note |
| `/obsidian-find [query]` | Smart vault search — returns results with context, not just filenames |
| `/obsidian-recap [today\|week\|month]` | Synthesizes a time period from daily notes and logs into a narrative |
| `/obsidian-review` | Generates a structured weekly or monthly review note |
| `/obsidian-board [name]` | Shows kanban board state, flags overdue items, updates from conversation |
| `/obsidian-project [name]` | Creates or updates a project note; adds to board and daily note |
| `/obsidian-health` | Vault health check grouped by severity; offers to auto-fix safe issues |
| `/obsidian-init` | Scans your vault and generates a `_CLAUDE.md` operating manual |

**Typo handling:** all name arguments fuzzy-match — Claude finds the closest match, confirms, then acts.

---

## Background Agent

The background agent is the most hands-off feature. It fires automatically after every context compaction with no user action needed.

```
PostCompact → obsidian-bg-agent.sh → claude -p (headless) → vault updated
```

After each compaction, a headless Claude subprocess wakes up, reads `_CLAUDE.md`, scans the session summary for vault-worthy items, and writes updates everywhere they belong — people notes, project notes, dev logs, kanban boards, today's daily note. You keep working. The vault updates itself.

`setup.sh` wires this automatically. To check it's working: `tail -f /tmp/obsidian-bg-agent.log`

---

## Parallel Subagents

Complex commands don't run sequentially — they spawn parallel subagents, one per task group, and merge results when all finish.

| Command | What runs in parallel |
|---|---|
| `/obsidian-save` | People agent · Projects agent · Tasks agent · Decisions agent · Ideas agent |
| `/obsidian-health` | Links agent · Duplicates agent · Frontmatter agent · Staleness agent · Orphans agent |
| `/obsidian-recap` | One agent per daily note in the date range |
| `/obsidian-init` | Dashboard agent · Templates agent · Boards agent · Note samples agent |

---

## Scheduled Agents

Four agents that run on a schedule — no user action required. Set up once with `/schedule` in Claude Code.

| Agent | Schedule | What it does |
|---|---|---|
| `obsidian-morning` | Daily 8:00 AM | Creates today's daily note, surfaces overdue tasks and stale projects |
| `obsidian-nightly` | Daily 10:00 PM | Closes the day, appends an End of Day summary, moves done tasks |
| `obsidian-weekly` | Fridays 6:00 PM | Generates a weekly review from the week's daily notes and completed tasks |
| `obsidian-health-check` | Sundays 9:00 PM | Runs health check, saves report — never auto-fixes, only reports |

```
/schedule
```

Then tell Claude which agents you want and at what times.

---

## Vault Health Check

```bash
python ~/.claude/skills/obsidian-second-brain/scripts/vault_health.py --path ~/my-vault
```

Reports (by severity):
- 🔴 Unfilled template syntax left in notes
- 🟡 Possible duplicate notes
- 🟡 Stale / overdue tasks
- 🟡 Notes missing frontmatter
- 🟡 Broken internal links (`[[Note]]` pointing to nothing)
- ⚪ Orphaned notes (nothing links to them)
- ⚪ Empty folders

For machine-readable output:
```bash
python scripts/vault_health.py --path ~/my-vault --json
```

---

## How `_CLAUDE.md` Works

```
Your machine
│
├── Claude Desktop / Claude Code / VS Code / terminal
│   └── reads _CLAUDE.md at session start
│
└── Your Vault/
    ├── _CLAUDE.md          ← Claude's operating manual for this vault
    ├── Home.md
    ├── Daily/
    ├── Projects/
    ├── Boards/
    └── ...
```

`_CLAUDE.md` is a plain markdown file. It's what makes every Claude surface behave consistently in your vault without relying on memory between sessions. It contains your folder map, naming conventions, frontmatter schemas, auto-save rules, active context, kanban format, and propagation rules.

Update it when your priorities shift:
```
"Claude, update my _CLAUDE.md"
```

---

## Recommended Obsidian Plugins

| Plugin | Why |
|---|---|
| [Dataview](https://github.com/blacksmithgu/obsidian-dataview) | Powers Home dashboard queries |
| [Templater](https://github.com/SilentVoid13/Templater) | Powers the Templates/ folder |
| [Kanban](https://github.com/mgmeyers/obsidian-kanban) | Powers the Boards/ folder |
| [Calendar](https://github.com/liamcain/obsidian-calendar-plugin) | Daily note navigation |

---

## Skill Structure

```
obsidian-second-brain/
├── SKILL.md                          ← Core instructions for Claude
├── hooks/
│   └── obsidian-bg-agent.sh          ← PostCompact background agent hook
├── references/
│   ├── vault-schema.md               ← Folder structure + frontmatter specs
│   ├── write-rules.md                ← How Claude writes, links, and propagates
│   └── claude-md-template.md        ← Template for generating _CLAUDE.md
└── scripts/
    ├── setup.sh                      ← One-command installer
    ├── bootstrap_vault.py            ← Bootstrap a complete vault from scratch
    └── vault_health.py               ← Audit a vault for structural issues
```

---

## Examples

**`/obsidian-save`** — after a long conversation about a new project: Claude scans the whole chat, identifies the project, the decisions made, the people mentioned, and any tasks committed to. Creates the project note, adds a card to the kanban board, stubs out people notes, logs tasks, links everything from today's daily note. No instructions needed.

**`/obsidian-log`** — after a dev session: Claude infers the project, writes a dev log with what was worked on, problems encountered, and next steps. Links it from the project's Recent Activity section and today's daily note automatically.

**`/obsidian-project markting campain`** — typo and all: Claude searches the vault, finds "Marketing Campaign Q2", confirms *"Found 'Marketing Campaign Q2' — is this the one?"*, then updates it from the conversation.

**`/obsidian-health`** — Claude runs the script, groups findings by severity, offers to fix safe issues. Asks before touching anything destructive.

---

## Philosophy

> A second brain shouldn't require manual maintenance. If you have to think about where to put something, the system is broken.

The goal is zero friction. You work, talk, and think. Claude handles the memory.

---

## Contributing

PRs welcome. Especially interested in:
- Additional note type schemas (habits, books, investments)
- Agent integration (automated vault updates from Slack/email)
- Alternative folder structures (GTD, PARA, Zettelkasten variants)
- VS Code / Cursor-specific setup guides

---

## License

MIT
