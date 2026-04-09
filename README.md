<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=for-the-badge&logo=anthropic" alt="Claude Code Skill" />
  <img src="https://img.shields.io/badge/Obsidian-Plugin_Ready-7C3AED?style=for-the-badge&logo=obsidian&logoColor=white" alt="Obsidian" />
  <img src="https://img.shields.io/github/v/release/eugeniughelbur/obsidian-second-brain?style=for-the-badge&color=green" alt="Release" />
  <img src="https://img.shields.io/github/license/eugeniughelbur/obsidian-second-brain?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/github/stars/eugeniughelbur/obsidian-second-brain?style=for-the-badge&color=yellow" alt="Stars" />
</p>

<h1 align="center">obsidian-second-brain</h1>

<p align="center">
  <strong>Your Obsidian vault is dead weight. This skill makes it alive.</strong>
  <br /><br />
  <em>24 commands &middot; self-rewriting knowledge base &middot; auto-synthesis &middot; thinking tools that argue with you &middot; 4 scheduled agents &middot; 4 role presets</em>
  <br /><br />
  <a href="#what-happens-when-you-install-this">See it in action</a> &middot;
  <a href="#24-commands">All commands</a> &middot;
  <a href="#install">Install</a> &middot;
  <a href="#choose-your-preset">Presets</a> &middot;
  <a href="https://github.com/eugeniughelbur/obsidian-second-brain/discussions">Discussions</a>
</p>

---

## The Problem

You use Claude every day. Every session starts from scratch. You re-explain everything. The conversation ends. Everything disappears.

You take notes in Obsidian. Hundreds of files. They just sit there. You make the same decision twice because you forgot you made it six months ago. Ideas rot in daily notes. Nobody connects the dots.

**Two powerful tools. Completely disconnected.**

---

## What Happens When You Install This

**After a meeting:** `/obsidian-save`
Claude pulls out every decision, person, task, and idea from the conversation and saves each one to the right note. You do nothing.

**You find a great video:** `/obsidian-ingest https://youtube.com/...`
Claude doesn't summarize into one note. It REWRITES your existing pages. People get updated. Contradictions get resolved. Patterns trigger new synthesis pages. One URL in. The vault is smarter.

**Before a big decision:** `/obsidian-challenge`
Claude searches your vault for past failures and reversed decisions on the same topic. Pushes back with your own words. Your vault holds you accountable.

**You do nothing:** The vault still gets smarter.
A background agent updates it during your sessions. Scheduled agents run morning, night, and weekly. An auto-synthesis engine finds patterns across sources and writes connection pages you never asked for.

**You never open Obsidian.** Everything happens through Claude.

---

## Before & After

| | Without this skill | With this skill |
|---|---|---|
| Saving decisions | Copy-paste or lose them | Auto-saved to the right project note |
| Daily notes | Write it yourself, forget half the time | Created automatically |
| Finding patterns | Re-read dozens of notes | `/emerge` finds them for you |
| Challenging yourself | Nobody pushes back | `/challenge` uses your own history against you |
| Session continuity | Re-explain every time | `/world` loads full context in 10 seconds |
| Ingesting content | Read it, forget it | `/ingest` rewrites 5-15 vault pages from 1 source |
| Contradictions | You don't know they exist | `/reconcile` resolves them automatically |
| Synthesis | You connect dots manually | `/synthesize` finds patterns across sources on its own |
| Sharing vault data | Only Claude can read it | `/export` gives any AI tool a clean snapshot |
| Facts change over time | Old info gets overwritten | Temporal facts track the full timeline -- nothing is lost |
| Starting a new session | Re-explain who you are | `CRITICAL_FACTS.md` loads your identity in ~120 tokens |

---

## How It Works

```
  +------------------------------------------+
  |                                          |
  |   LAYER 1: Operations (19 commands)      |
  |   Claude remembers everything            |
  |                                          |
  +------------------------------------------+
  |                                          |
  |   LAYER 2: Thinking Tools (4 commands)   |
  |   Claude thinks with you                 |
  |                                          |
  +------------------------------------------+
  |                                          |
  |   LAYER 3: Context Engine (1 command)    |
  |   Claude knows who you are               |
  |                                          |
  +------------------------------------------+
  |                                          |
  |   ALWAYS ON                              |
  |   Background agent + 4 scheduled agents  |
  |   Auto-synthesis + save reminders        |
  |                                          |
  +------------------------------------------+
```

**Layer 1** saves, organizes, ingests, reconciles, exports, and maintains your vault.
**Layer 2** challenges your ideas, surfaces hidden patterns, bridges unrelated domains, and graduates ideas into projects.
**Layer 3** loads your identity and current state so every session picks up where the last one ended.
**Always On** keeps the vault alive without you lifting a finger.

---

## 24 Commands

### Operations -- Claude remembers

| Command | What it does |
|---|---|
| `/obsidian-save` | Saves everything from the conversation -- decisions, tasks, people, ideas |
| `/obsidian-ingest` | Drop a URL. The vault REWRITES itself. 5-15 pages touched per source. |
| `/obsidian-synthesize` | Auto-finds patterns across sources and writes synthesis pages |
| `/obsidian-reconcile` | Finds contradictions and resolves them. The vault maintains its own truth. |
| `/obsidian-export` | Clean JSON/markdown snapshot any AI tool can read |
| `/obsidian-daily` | Creates or updates today's daily note |
| `/obsidian-log` | Logs a work session, links it everywhere |
| `/obsidian-task` | Adds task to the right board with priority and due date |
| `/obsidian-person` | Creates or updates a person note |
| `/obsidian-decide` | Logs decisions to the right project note |
| `/obsidian-capture` | Zero-friction idea capture |
| `/obsidian-find` | Smart search with context |
| `/obsidian-recap` | Summary of a day, week, or month |
| `/obsidian-review` | Structured weekly or monthly review |
| `/obsidian-board` | Kanban board view and updates |
| `/obsidian-project` | Project note with board and daily links |
| `/obsidian-health` | Vault audit -- contradictions, gaps, stale claims, orphans |
| `/obsidian-adr` | Decision records -- the vault knows why it's structured this way |
| `/obsidian-init` | Generates `_CLAUDE.md`, `index.md`, `log.md` |

### Thinking -- Claude thinks with you

| Command | What it does |
|---|---|
| `/obsidian-challenge` | Your vault argues against your idea using your own history |
| `/obsidian-emerge` | Surfaces patterns from 30 days of notes you never named |
| `/obsidian-connect [A] [B]` | Bridges two unrelated domains to spark new ideas |
| `/obsidian-graduate` | Turns an idea fragment into a full project with tasks |

### Context -- Claude knows you

| Command | What it does |
|---|---|
| `/obsidian-world` | Loads identity + state with progressive token budgets (L0-L3) |

<details>
<summary><strong>See the thinking tools in action</strong></summary>

<br />

**`/obsidian-challenge`**

You: *"I want to rewrite the API in Rust."*

Claude finds your 2025 post-mortem where the Rust rewrite failed. Finds your decision log committing to TypeScript for 2 years. Says: *"Your own notes say this failed. Still want to proceed?"*

---

**`/obsidian-emerge`**

Claude scans 30 daily notes. You mentioned "onboarding friction" in 4 unrelated projects.

*"Onboarding is your bottleneck across projects. You never named it."*

---

**`/obsidian-connect "distributed systems" "cooking"`**

Traces both clusters in your link graph. Finds shared concepts: preparation and load distribution. Generates 3 actionable ideas at the intersection.

---

**`/obsidian-graduate`**

An idea from 3 weeks ago. Claude reads it, finds related projects and people, generates a full spec with goals, phases, tasks, and board entries. The idea gets tagged `graduated`.

</details>

<details>
<summary><strong>See /obsidian-ingest in action</strong></summary>

<br />

```
/obsidian-ingest https://youtube.com/watch?v=example
```

1. Saves original to `raw/videos/` (immutable)
2. REWRITES entity pages with new context
3. REWRITES concept pages if the source adds depth or contradicts them
4. Creates synthesis pages when patterns emerge
5. Resolves contradictions and documents why
6. Updates `index.md`, `log.md`, daily note

**One URL in. The vault rewrites itself.**

</details>

---

## The Vault is Alive

Traditional vaults are filing cabinets. You put things in. They sit there.

This vault rewrites itself with every input:

- **Ingest a source** -- existing pages get rewritten, contradictions resolved, patterns synthesized
- **Save a conversation** -- entities, concepts, and decisions distribute across the vault
- **Ask a question** -- the Two-Output Rule means every answer also updates pages
- **A fact changes** -- temporal facts track the timeline. Old facts aren't deleted, they get a `until:` date. The vault remembers what was true and when.
- **Do nothing** -- background agent and scheduled agents maintain it while you sleep
- **Wait a week** -- auto-synthesis finds cross-source patterns and writes connection pages

The vault after a week is fundamentally different from the vault you started with.

---

## Choose Your Preset

Pick your role at bootstrap. Each preset creates tailored folder structures, templates, and kanban boards.

| Preset | Who it's for | Kanban style |
|---|---|---|
| **executive** | Founders, operators, managers | OKRs / Quarterly / Weekly |
| **builder** | Developers, engineers, architects | Backlog / Sprint / Done |
| **creator** | Writers, YouTubers, marketers | Ideas / Drafts / Published |
| **researcher** | Academics, analysts, deep-divers | Reading / Processing / Synthesized |

```bash
python bootstrap_vault.py --path ~/my-vault --name "Your Name" --preset builder
```

No preset? You get a general-purpose vault that works for everyone.

---

## Background Agent & Scheduled Agents

**Background:** fires after every context compaction. You keep working. The vault updates itself.

```
PostCompact -> obsidian-bg-agent.sh -> claude -p (headless) -> vault updated
```

**Scheduled:**

| Agent | When | What |
|---|---|---|
| `morning` | 8 AM | Daily note + overdue tasks |
| `nightly` | 10 PM | End of day summary + board cleanup |
| `weekly` | Fridays 6 PM | Weekly review |
| `health` | Sundays 9 PM | Vault health audit |

**Save reminders:** Claude nudges you to `/obsidian-save` after 10+ exchanges or when you say "done" or "thanks". No lost conversations.

---

## Vault Architecture

### Wiki-style (default) -- LLM-first

Claude is the reader and writer. The vault is a database.

```
vault/
+-- _CLAUDE.md          # Operating manual
+-- index.md            # Page catalog (Claude reads FIRST)
+-- log.md              # Activity timeline
+-- SOUL.md             # Your identity
+-- CRITICAL_FACTS.md   # ~120 tokens, always loaded (timezone, manager, location)
+-- raw/                # IMMUTABLE source material
+-- wiki/               # Claude's workspace
|   +-- entities/       # People, companies, tools
|   +-- concepts/       # Ideas, frameworks, synthesis
|   +-- projects/       # Project notes
|   +-- daily/          # Daily notes
|   +-- logs/           # Work session logs
|   +-- reviews/        # Weekly/monthly reviews
|   +-- tasks/          # Task notes
|   +-- decisions/      # ADRs
+-- boards/             # Kanban boards
+-- templates/          # Note templates
```

<details>
<summary><strong>Obsidian-style (alternative) -- for daily browsers</strong></summary>

```
vault/
+-- Daily/, Projects/, People/, Ideas/, Knowledge/
+-- Dev Logs/, Tasks/, Reviews/, Boards/, Templates/
```

```bash
python bootstrap_vault.py --path ~/my-vault --name "Your Name" --style obsidian
```

</details>

---

## Install

One line:

```bash
curl -sL https://raw.githubusercontent.com/eugeniughelbur/obsidian-second-brain/main/scripts/quick-install.sh | bash
```

Or two commands:

```bash
git clone https://github.com/eugeniughelbur/obsidian-second-brain ~/.claude/skills/obsidian-second-brain
bash ~/.claude/skills/obsidian-second-brain/scripts/setup.sh "/path/to/your/vault"
```

Then: `/obsidian-init`

---

## Philosophy

Most second brain tools make you the janitor.

This skill inverts that. You think, work, and talk. Claude handles the memory. Then it uses that memory to make you think better -- surfacing what you'd miss, challenging what you'd assume, connecting what you'd never link, and synthesizing patterns you didn't ask for.

The vault doesn't grow. It evolves.

**Your notes are the moat.**

Inspired by [Andrey Karpathy's LLM-Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

## Contributing

PRs welcome:
- New thinking tools
- Note type schemas (habits, books, investments)
- MCP integrations (Calendar, Linear, Slack)
- Alternative vault structures
- VS Code / Cursor setup guides

---

## Author

Built by **Eugeniu Ghelbur**

[![X](https://img.shields.io/badge/X-@eugeniu__ghelbur-000000?style=flat-square&logo=x)](https://x.com/eugeniu_ghelbur)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-eugeniu--ghelbur-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/eugeniu-ghelbur/)
[![GitHub](https://img.shields.io/badge/GitHub-eugeniughelbur-181717?style=flat-square&logo=github)](https://github.com/eugeniughelbur/)
[![Substack](https://img.shields.io/badge/Substack-ghelburlabs-FF6719?style=flat-square&logo=substack)](https://ghelburlabs.substack.com/)

---

## License

MIT
