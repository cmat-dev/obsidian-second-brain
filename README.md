<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=for-the-badge&logo=anthropic" alt="Claude Code Skill" />
  <img src="https://img.shields.io/badge/Obsidian-Plugin_Ready-7C3AED?style=for-the-badge&logo=obsidian&logoColor=white" alt="Obsidian" />
  <img src="https://img.shields.io/github/v/release/eugeniughelbur/obsidian-second-brain?style=for-the-badge&color=green" alt="Release" />
  <img src="https://img.shields.io/github/license/eugeniughelbur/obsidian-second-brain?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/github/stars/eugeniughelbur/obsidian-second-brain?style=for-the-badge&color=yellow" alt="Stars" />
</p>

<h1 align="center">obsidian-second-brain</h1>

<p align="center">
  <strong>Turn your Obsidian vault into a personal AI operating system.</strong>
  <br />
  <em>19 commands &middot; 4 thinking tools &middot; 4 scheduled agents &middot; 1 background agent</em>
  <br /><br />
  <a href="#install">Install</a> &middot;
  <a href="#the-three-layers">Features</a> &middot;
  <a href="#commands-at-a-glance">Commands</a> &middot;
  <a href="#scheduled-agents--claude-works-while-you-sleep">Agents</a> &middot;
  <a href="#contributing">Contributing</a>
</p>

---

## The Problem

Most people use AI as a search engine. Ask a question, get an answer, forget it. Every session starts from zero. Your best ideas, decisions, and lessons scatter across chats that disappear.

And note-taking doesn't help — you take notes but never connect them. Decisions get made and forgotten. Patterns repeat across projects because you can't see them. Ideas sit in daily notes and never become anything.

## The Solution

This skill solves both problems at once. Your vault becomes Claude's memory, and Claude becomes your vault's brain.

> **You talk. Claude remembers.** Every decision, person, task, and idea gets saved to the right place — automatically.
>
> **You write. Claude thinks.** Your notes become fuel for insight. Claude red-teams your plans, finds unnamed patterns, and connects ideas across domains you'd never link yourself.
>
> **You sleep. Claude maintains.** Scheduled agents run morning, night, and weekly — autonomously. A background agent fires after every compaction and silently updates your vault while you keep working.

---

## The Three Layers

```
                    +-----------------------------------------+
                    |        obsidian-second-brain             |
                    +-----------------------------------------+
                    |                                         |
  LAYER 1           |   Vault Operations (14 commands)        |
  "Claude           |   save, daily, log, task, person,       |
   remembers"       |   decide, capture, find, recap,         |
                    |   review, board, project, health, init  |
                    +-----------------------------------------+
                    |                                         |
  LAYER 2           |   Thinking Tools (4 commands)           |
  "Claude           |   challenge  - red-team your ideas      |
   thinks           |   emerge     - surface hidden patterns  |
   with you"        |   connect    - bridge unrelated domains |
                    |   graduate   - idea -> full project     |
                    +-----------------------------------------+
                    |                                         |
  LAYER 3           |   Context Engine (1 command)            |
  "Claude           |   world - load identity + state         |
   knows you"       |          in one shot                    |
                    +-----------------------------------------+
                    |                                         |
  ALWAYS ON         |   Background Agent (PostCompact hook)   |
                    |   4 Scheduled Agents (cron)             |
                    +-----------------------------------------+
```

---

## Commands at a Glance

### Layer 1: Vault Operations

> Claude remembers everything. You never think about where to save something.

| Command | What it does |
|---|---|
| `/obsidian-save` | Scans your entire conversation and saves everything worth keeping — decisions, tasks, people, ideas — all at once |
| `/obsidian-daily` | Creates or updates today's daily note, pre-filled from conversation context |
| `/obsidian-log` | Logs a work session — infers the project, writes the log, links it everywhere |
| `/obsidian-task [desc]` | Adds a task to the right kanban board with inferred priority and due date |
| `/obsidian-person [name]` | Creates or updates a person note; logs the interaction in the daily note |
| `/obsidian-decide [topic]` | Extracts decisions and logs them in the right project's Key Decisions section |
| `/obsidian-capture [idea]` | Zero-friction idea capture to Ideas/ |
| `/obsidian-find [query]` | Smart search — returns context, not just filenames |
| `/obsidian-recap [period]` | Narrative summary of a day, week, or month |
| `/obsidian-review` | Generates a structured weekly or monthly review |
| `/obsidian-board [name]` | Shows kanban state, flags overdue items |
| `/obsidian-project [name]` | Creates or updates a project note with board and daily links |
| `/obsidian-health` | Vault audit — duplicates, orphans, broken links, stale tasks |
| `/obsidian-init` | Scans your vault and generates the `_CLAUDE.md` operating manual |

Every command searches before creating (no duplicates), propagates to every linked note (no orphans), and handles typos with fuzzy matching.

---

### Layer 2: Thinking Tools

> This is what makes this skill different. These commands don't organize — they generate insight.

| Command | What it does |
|---|---|
| `/obsidian-challenge` | Red-teams your idea against your own vault history |
| `/obsidian-emerge` | Surfaces unnamed patterns from your last 30 days of notes |
| `/obsidian-connect [A] [B]` | Bridges two unrelated domains to spark new ideas |
| `/obsidian-graduate` | Promotes an idea fragment into a full project with tasks and structure |

<details>
<summary><strong>See examples</strong></summary>

<br />

**`/obsidian-challenge`**

You say: *"I want to rewrite the API in Rust."*

Claude searches your vault, finds your 2025 post-mortem where you abandoned a Rust rewrite due to hiring constraints, and your decision log where you committed to TypeScript for 2 years. It presents the counter-evidence and asks: *"Still want to proceed?"*

This is your vault arguing with you — using your own words.

---

**`/obsidian-emerge`**

After a busy month, Claude scans 30 daily notes and finds you mentioned "onboarding friction" in 4 different client projects without ever naming it as a problem.

It surfaces: *"You have an unnamed pattern — onboarding is your bottleneck across projects, not a one-off issue."*

These are conclusions your notes already contain but you never stated.

---

**`/obsidian-connect "distributed systems" "cooking"`**

Claude traces both clusters in your link graph and finds shared concepts around preparation and load distribution. It generates 3 concrete ideas at the intersection — not vague analogies, but actionable concepts grounded in your own notes.

---

**`/obsidian-graduate`**

An idea you captured 3 weeks ago is ready to become real. Claude reads the idea note, researches your vault for related projects and people, and generates a full project spec with goals, phases, tasks, and board entries.

The idea note gets tagged `graduated` and linked to the new project. Nothing dies in your inbox.

</details>

---

### Layer 3: Context Engine

> Every session picks up where you left off.

| Command | What it does |
|---|---|
| `/obsidian-world` | Loads your identity, values, priorities, and current state in one shot |

Run `/obsidian-world` at the start of any session. Claude reads your `SOUL.md`, checks your last 3 daily notes, scans your boards, and reports:

> *"You're focused on the API launch (due Friday), you left off debugging the auth middleware last night, and you have 2 overdue tasks on the Marketing board."*

No re-explaining. No context loss.

---

## Background Agent

The most hands-off feature. Fires automatically after every context compaction — no user action needed.

```
PostCompact -> obsidian-bg-agent.sh -> claude -p (headless) -> vault updated
```

A headless Claude subprocess wakes up, reads `_CLAUDE.md`, scans the session summary, and writes updates everywhere they belong. You keep working. The vault updates itself.

---

## Scheduled Agents — Claude works while you sleep

| Agent | When | What it does |
|---|---|---|
| `obsidian-morning` | Daily 8 AM | Creates today's daily note, surfaces overdue tasks and stale projects |
| `obsidian-nightly` | Daily 10 PM | Closes out the day, appends a summary, moves completed tasks to Done |
| `obsidian-weekly` | Fridays 6 PM | Generates a weekly review from the week's activity |
| `obsidian-health-check` | Sundays 9 PM | Runs a vault health audit and saves a report |

Set up once: `/schedule`

---

## Parallel Subagents

Complex commands spawn parallel subagents — one per task group — and merge results when all finish.

| Command | What runs in parallel |
|---|---|
| `/obsidian-save` | People + Projects + Tasks + Decisions + Ideas |
| `/obsidian-challenge` | Decisions + Failures + Contradictions |
| `/obsidian-emerge` | Daily notes + Dev logs + Decisions + Ideas |
| `/obsidian-health` | Links + Duplicates + Frontmatter + Staleness + Orphans |
| `/obsidian-recap` | One agent per daily note in the range |
| `/obsidian-init` | Dashboard + Templates + Boards + Samples |

---

## How `_CLAUDE.md` Works

The entire system runs on one file at your vault root.

```
Your Mac
|
+-- Claude Desktop / Claude Code / VS Code
|   +-- reads _CLAUDE.md on every session start
|
+-- Your Vault/
    +-- _CLAUDE.md          <-- Claude's operating manual
    +-- Home.md
    +-- Daily/
    +-- Projects/
    +-- Boards/
    +-- ...
```

Every Claude surface reads this file first. It contains your folder structure, naming conventions, frontmatter schemas, propagation rules, and active context. No memory required. Every session starts with full context.

---

## Install

Two commands. That's it.

```bash
# 1. Clone the skill
git clone https://github.com/eugeniughelbur/obsidian-second-brain ~/.claude/skills/obsidian-second-brain

# 2. Run setup (wires the hook, sets vault path, optionally configures MCP)
bash ~/.claude/skills/obsidian-second-brain/scripts/setup.sh "/path/to/your/vault"
```

Then run:

```
/obsidian-init
```

Claude scans your vault and generates a `_CLAUDE.md` — its operating manual for your specific vault.

<details>
<summary><strong>Bootstrap a new vault from scratch</strong></summary>

<br />

```bash
python ~/.claude/skills/obsidian-second-brain/scripts/bootstrap_vault.py \
  --path ~/my-vault \
  --name "Your Name" \
  --jobs "Company Name"
```

Creates a complete vault with folders, templates, kanban boards, a Home dashboard, and a pre-filled `_CLAUDE.md`. Then run `setup.sh` pointing at the new path.

</details>

---

## Recommended Obsidian Plugins

| Plugin | Why |
|---|---|
| [Dataview](https://github.com/blacksmithgu/obsidian-dataview) | Powers the Home dashboard queries |
| [Templater](https://github.com/SilentVoid13/Templater) | Powers the Templates/ folder |
| [Kanban](https://github.com/mgmeyers/obsidian-kanban) | Powers the Boards/ folder |
| [Calendar](https://github.com/liamcain/obsidian-calendar-plugin) | Daily note navigation |

---

## Skill Structure

```
obsidian-second-brain/
+-- SKILL.md                        # Core instructions for Claude
+-- commands/                       # 19 slash commands
+-- hooks/                          # Background agent hook
+-- references/
|   +-- vault-schema.md             # Folder structure + frontmatter specs
|   +-- write-rules.md              # Writing, linking, and propagation rules
|   +-- claude-md-template.md       # Template for generating _CLAUDE.md
+-- scripts/
|   +-- setup.sh                    # One-command installer
|   +-- bootstrap_vault.py          # Bootstrap a vault from scratch
|   +-- vault_health.py             # Audit a vault for structural issues
```

---

## Philosophy

> Most second brain tools make you the janitor. You spend more time organizing than thinking.

This skill inverts that. You think, work, and talk. Claude handles the memory. And then it uses that memory to make you think better — surfacing what you'd miss, challenging what you'd assume, and connecting what you'd never link.

The vault gets smarter every day you use it. Not because of AI magic, but because your own writing compounds. The more you write, the more context Claude has, the more it can do for you.

**Your notes are the moat.**

---

## Contributing

PRs welcome. Especially interested in:
- New thinking tools (novel ways to use vault data for insight)
- Note type schemas (habits, books, investments)
- MCP integrations (Calendar, Linear, Slack context in daily rituals)
- Alternative vault structures (GTD, PARA, Zettelkasten variants)
- VS Code / Cursor setup guides

---

## Author

Built by **Eugeniu Ghelbur**

[![X](https://img.shields.io/badge/X-@eugeniu__ghelbur-000000?style=flat-square&logo=x)](https://x.com/eugeniu_ghelbur)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-eugeniu--ghelbur-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/eugeniu-ghelbur/)
[![GitHub](https://img.shields.io/badge/GitHub-eugeniughelbur-181717?style=flat-square&logo=github)](https://github.com/eugeniughelbur/)

---

## License

MIT
