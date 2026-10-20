"""Two small robustness fixes.

1. append_to_daily looked only in `wiki/daily/`, so a vault using the other
   documented layout (`Daily/`) never received a research summary even with
   today's note present.
2. The empty-folder check listed every folder with no guard, so one folder the
   scan cannot list (OS-protected, or locked by a sync client) raised
   PermissionError and aborted the whole health report.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import vault_health  # noqa: E402


class _Noon(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 2, 12, 0, 0)


@pytest.fixture
def research_vault(tmp_path, monkeypatch):
    from research.lib import vault

    root = tmp_path / "vault"
    root.mkdir()
    monkeypatch.setattr(vault, "VAULT_PATH", root)
    monkeypatch.setattr(vault, "datetime", _Noon)
    return root, vault


def test_summary_lands_in_an_obsidian_style_daily_folder(research_vault):
    root, vault = research_vault
    daily = root / "Daily" / "2026-09-02.md"
    daily.parent.mkdir()
    daily.write_text("# 2026-09-02\n", encoding="utf-8")
    assert vault.append_to_daily("found a thing") is True
    assert "found a thing" in daily.read_text(encoding="utf-8")


def test_wiki_style_daily_folder_still_works(research_vault):
    root, vault = research_vault
    daily = root / "wiki" / "daily" / "2026-09-02.md"
    daily.parent.mkdir(parents=True)
    daily.write_text("# 2026-09-02\n", encoding="utf-8")
    assert vault.append_to_daily("found a thing") is True
    assert "found a thing" in daily.read_text(encoding="utf-8")


def test_the_layout_holding_todays_note_wins(research_vault):
    """A vault with both folders, today's note only in Daily/: append there."""
    root, vault = research_vault
    (root / "wiki" / "daily").mkdir(parents=True)
    daily = root / "Daily" / "2026-09-02.md"
    daily.parent.mkdir()
    daily.write_text("# 2026-09-02\n", encoding="utf-8")
    assert vault.append_to_daily("x") is True
    assert "x" in daily.read_text(encoding="utf-8")
    assert not (root / "wiki" / "daily" / "2026-09-02.md").exists()


def test_an_unreadable_folder_is_skipped_not_fatal(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    (vault / "locked").mkdir(parents=True)
    (vault / "empty").mkdir()
    (vault / "full").mkdir()
    (vault / "full" / "n.md").write_text("x\n", encoding="utf-8")
    real_iterdir = Path.iterdir

    def iterdir(self):
        if self.name == "locked":
            raise PermissionError(13, "Permission denied", str(self))
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", iterdir)
    issues = vault_health.check_empty_folders(vault)
    reported = {i["message"] for i in issues}
    assert "Empty folder: empty/" in reported
    assert not any("locked" in m for m in reported), "unreadable is not empty"
    assert not any("full" in m for m in reported)
