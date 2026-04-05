---
description: Ingest a source (article, PDF, transcript, video) into the vault — extracts entities, creates/updates multiple pages, and logs the ingest
---

Use the obsidian-second-brain skill. Execute `/obsidian-ingest $ARGUMENTS`:

The argument is a URL, file path, or pasted text. If no argument, ask what to ingest.

1. Read `_CLAUDE.md` first if it exists in the vault root

2. Classify the source type before reading the full content:
   - **Article/blog post** — extract key claims, people, tools, concepts
   - **PDF/document** — extract structure, findings, recommendations
   - **Transcript (meeting/podcast)** — extract speakers, decisions, action items, quotes
   - **YouTube video** — pull metadata, description, and transcript (see step 3 for method)
   - **Raw text** — classify by content (opinion, technical, narrative) and extract accordingly

3. Read or fetch the full source content:

   **For YouTube URLs** — try methods in this order (use the first one that works):

   **Method A — `yt-dlp` (best, works in Claude Code / terminal):**
   ```bash
   # Check if installed
   which yt-dlp || brew install yt-dlp

   # Pull metadata
   yt-dlp --skip-download --print title --print description --print duration_string --print view_count --print like_count --print upload_date --print channel "URL"

   # Pull transcript if available
   yt-dlp --write-auto-sub --sub-lang en --skip-download -o "/tmp/%(id)s" "URL"
   ```

   **Method B — YouTube MCP tools (works in Claude Desktop if configured):**
   Check if YouTube MCP tools are available (e.g., `youtube_get_video_details`). If so, use them to pull metadata and description.

   **Method C — oEmbed fallback (works everywhere, limited data):**
   Fetch `https://www.youtube.com/oembed?url=URL&format=json` — gives title and channel only. Then ask user: "I got the title and channel but YouTube blocks full descriptions. Paste the video description here for a complete ingest."

   **For articles** — use WebFetch to pull the page content
   **For PDFs** — read the file directly
   **For pasted text** — use as-is

   Always be transparent about what was extracted. If the ingest is partial, say so and tell the user what to paste for a full ingest.

4. Extract and organize:
   - **Entities**: people mentioned, companies, tools, projects
   - **Concepts**: key ideas, frameworks, methodologies
   - **Claims**: specific assertions with supporting evidence
   - **Action items**: anything actionable for the user
   - **Quotes**: notable quotes worth preserving

5. Save the raw source:
   - Create `Knowledge/YYYY-MM-DD — Source Title.md` with full summary and source link
   - Frontmatter: `date`, `tags: [source, <type>]`, `source_url`, `source_type`

6. Spawn parallel subagents to update the vault from the source:
   - **People agent**: for each person mentioned, search People/ — create or update with new context
   - **Projects agent**: if the source relates to existing projects, update those notes with new findings
   - **Ideas agent**: for new concepts or ideas, search Ideas/ — create or append
   - **Knowledge agent**: for factual claims or frameworks, create or update Knowledge/ notes

7. Update structural files:
   - Append to `index.md` — add all newly created notes
   - Append to `log.md` — `## [YYYY-MM-DD] ingest | Source Title (type: article/transcript/etc.) — X notes created, Y notes updated`

8. Update today's daily note with a summary of what was ingested

9. Report back: source title, type, and a list of every note created or updated

A single ingest should touch 5-15 files. The goal is to compile knowledge once and distribute it across the vault — not just dump a summary into one note.
