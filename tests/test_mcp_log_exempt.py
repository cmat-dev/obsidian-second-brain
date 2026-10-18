"""MCP writes under log-exempt folders are validated but not logged, and the
log clock can follow the vault's timezone instead of the server's.

An agent that keeps its own activity log in the vault (the Crew logbook in
`wiki/team/`) appends one line per job. Through the MCP server each append
also wrote a vault-wide log entry saying a line was appended, so the vault log
grew one echo per job. Validation must survive the exemption: it is the part
that catches a malformed note, and it was gated on the same bookkeeping-surface
test the log uses, so exempting by that test would have dropped it too.

Separately, a server in UTC dated every entry made between local midnight and
the offset on the previous day.
"""

from __future__ import annotations

import importlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "integrations" / "obsidian-mcp-server"))

INDEX = "# Index\n\n## Inbox/\n\n- [[Inbox/seed]] - seed.\n\n## wiki/team/inbox/\n\n- [[wiki/team/inbox/old]] - old.\n"
NOTE = "---\ntype: note\ndate: 2026-01-01\ntags: [t]\nai-first: true\n---\n\n## For future agent\n\nhello\n"
INBOX = "---\ndate: 2026-01-01\ntags: [crew]\ntype: crew-inbox\n---\n\n- 09:00 | grokbot | ops | one | x\n"


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    (v / "Inbox").mkdir(parents=True)
    (v / "wiki" / "team" / "inbox").mkdir(parents=True)
    (v / "index.md").write_text(INDEX, encoding="utf-8")
    (v / "log.md").write_text("# Log\n", encoding="utf-8")
    (v / "note.md").write_text(NOTE, encoding="utf-8")
    (v / "wiki" / "team" / "inbox" / "agent-2026-01-01.md").write_text(INBOX, encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    for name in ("OBSIDIAN_BOOKKEEPING", "OBSIDIAN_POST_WRITE_CMD",
                 "OBSIDIAN_LOG_EXEMPT_PREFIXES", "OBSIDIAN_LOG_TZ"):
        monkeypatch.delenv(name, raising=False)
    import vault_ops
    importlib.reload(vault_ops)
    return v, vault_ops


def test_an_append_under_the_crew_folder_is_validated_not_logged(vault):
    v, ops = vault
    res = ops.update_note("wiki/team/inbox/agent-2026-01-01.md",
                          append="- 09:05 | grokbot | ops | two | y")
    assert "updated" in res, res
    assert "validation" in res, "validation must survive the log exemption"
    assert res["log"].startswith("not logged"), res
    assert (v / "log.md").read_text(encoding="utf-8") == "# Log\n"
    assert "two" in (v / "wiki" / "team" / "inbox" / "agent-2026-01-01.md").read_text(encoding="utf-8")


def test_a_save_under_the_crew_folder_is_validated_not_logged(vault):
    v, ops = vault
    res = ops.save_note("agent inbox", "- 10:00 | grokbot | ops | three | z",
                        path="wiki/team/inbox/agent-2026-01-02.md", note_type="crew-inbox",
                        tags=["crew"])
    assert "error" not in res, res
    assert "validation" in res and res["log"].startswith("not logged"), res
    assert (v / "log.md").read_text(encoding="utf-8") == "# Log\n"


def test_a_normal_note_still_logs(vault):
    v, ops = vault
    res = ops.update_note("note.md", append="more")
    assert res["log"] == "log.md" and res["validation"]["ok"] is True, res
    assert "] update | [[note]] appended" in (v / "log.md").read_text(encoding="utf-8")


def test_an_empty_setting_logs_everything(vault, monkeypatch):
    v, ops = vault
    monkeypatch.setenv("OBSIDIAN_LOG_EXEMPT_PREFIXES", "")
    res = ops.update_note("wiki/team/inbox/agent-2026-01-01.md", append="- 09:06 | grokbot | ops | four | w")
    assert res["log"] == "log.md", res


def test_custom_prefixes_replace_the_default(vault, monkeypatch):
    v, ops = vault
    monkeypatch.setenv("OBSIDIAN_LOG_EXEMPT_PREFIXES", " Inbox\\ , other/")
    assert ops._is_log_exempt("inbox/x.md") and ops._is_log_exempt("Other/y.md")
    assert not ops._is_log_exempt("wiki/team/inbox/z.md")
    assert not ops._is_log_exempt("inboxes/x.md"), "a prefix matches whole folders only"


def test_log_and_catalog_surfaces_are_unchanged(vault):
    v, ops = vault
    res = ops.update_note("index.md", append="- [[note]] - by hand.")
    assert "log" not in res and "validation" not in res, res
    assert (v / "log.md").read_text(encoding="utf-8") == "# Log\n"


def test_the_log_clock_follows_a_fixed_offset(vault, monkeypatch):
    v, ops = vault
    monkeypatch.setenv("OBSIDIAN_LOG_TZ", "+02:00")
    now = ops._now()
    assert now.utcoffset() == timedelta(hours=2)
    expected = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d")
    ops.update_note("note.md", append="tz")
    heading = re.findall(r"## \[(\d{4}-\d{2}-\d{2})\]", (v / "log.md").read_text(encoding="utf-8"))
    assert heading and heading[-1] == expected


@pytest.mark.parametrize("spec,hours", [("UTC+2", 2), ("-05:30", -5.5), ("GMT+0", 0)])
def test_offset_spellings(vault, monkeypatch, spec, hours):
    _, ops = vault
    monkeypatch.setenv("OBSIDIAN_LOG_TZ", spec)
    assert ops._now().utcoffset() == timedelta(hours=hours)


def test_an_unknown_zone_keeps_the_server_clock(vault, monkeypatch):
    _, ops = vault
    monkeypatch.setenv("OBSIDIAN_LOG_TZ", "Not/AZone")
    assert ops._now().tzinfo is None


def test_unset_keeps_the_server_clock(vault):
    _, ops = vault
    assert ops._now().tzinfo is None
