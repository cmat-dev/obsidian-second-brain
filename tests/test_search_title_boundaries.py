"""Regression for unrelated proper names receiving a strong title bonus."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/obsidian-mcp-server"))


def test_boot_lookup_does_not_match_booth_title(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("OBSIDIAN_SEARCH_LENGTHNORM", "1")
    import vault_ops

    ops = importlib.reload(vault_ops)
    (tmp_path / "Trade Booth.md").write_text("Unrelated exhibit description", encoding="utf-8")
    (tmp_path / "boot-card.md").write_text("Session initialization instructions", encoding="utf-8")
    hits = ops.search("boot", semantic=False)
    assert [hit["path"] for hit in hits] == ["boot-card.md"]
