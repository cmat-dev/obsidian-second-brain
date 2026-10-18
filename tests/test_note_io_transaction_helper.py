"""note_io routes guarded writes through a vault's shared transaction helper.

The MCP server already writes through `OBSIDIAN_TRANSACTION_HELPER`, else the
vault's `scripts/vault_transaction.py`. The scripts that rewrite notes in
place (heal_links, triage_links, the research appenders) used note_io's own
compare-and-replace instead, so in a vault with the helper they took no part
in its writer lock or journal. What is pinned here: with a helper they go
through it, a refusal stays a NoteChangedError, and a vault without one is
written exactly as before.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import note_io  # noqa: E402

BUNDLED_HELPER = REPO_ROOT / "integrations" / "obsidian-mcp-server" / "vault_transaction.py"
NOTE = "---\ntype: note\ndate: 2026-10-18\ntags: [a]\nai-first: true\n---\n\nbody\n"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.delenv("OBSIDIAN_TRANSACTION_HELPER", raising=False)
    root = tmp_path / "vault"
    root.mkdir()
    return root


def _install_helper(root: Path) -> None:
    (root / "scripts").mkdir()
    shutil.copy(BUNDLED_HELPER, root / "scripts" / "vault_transaction.py")


def _journals(root: Path) -> list[Path]:
    return sorted(root.rglob("transactions/*.json"))


def test_without_a_helper_the_write_is_direct(vault):
    note = vault / "a.md"
    note.write_bytes(NOTE.encode())
    assert note_io.transaction_helper(vault) is None
    note_io.write_exact_if_unchanged(note, NOTE + "more\n", NOTE, vault_root=vault)
    assert note.read_bytes() == (NOTE + "more\n").encode()
    assert _journals(vault) == []


def test_with_a_helper_the_write_is_journalled(vault):
    _install_helper(vault)
    note = vault / "a.md"
    note.write_bytes(NOTE.encode())
    note_io.write_exact_if_unchanged(note, NOTE + "more\n", NOTE, vault_root=vault)
    assert note.read_bytes() == (NOTE + "more\n").encode()
    journals = _journals(vault)
    assert len(journals) == 1, "the helper journals every committed write"
    assert '"committed"' in journals[0].read_text(encoding="utf-8")


def test_create_only_goes_through_the_helper(vault):
    _install_helper(vault)
    note = vault / "new" / "b.md"
    note.parent.mkdir()
    note_io.write_exact_if_unchanged(note, NOTE, None, vault_root=vault)
    assert note.read_bytes() == NOTE.encode()
    with pytest.raises(note_io.NoteChangedError):
        note_io.write_exact_if_unchanged(note, "other\n", None, vault_root=vault)
    assert note.read_bytes() == NOTE.encode()


def test_a_stale_source_is_refused_and_left_untouched(vault):
    _install_helper(vault)
    note = vault / "a.md"
    note.write_bytes(b"changed by someone else\n")
    with pytest.raises(note_io.TransactionRefusedError) as caught:
        note_io.write_exact_if_unchanged(note, NOTE + "more\n", NOTE, vault_root=vault)
    assert isinstance(caught.value, note_io.NoteChangedError), "batch callers skip it"
    assert caught.value.__cause__ is not None, "the helper's reason is kept"
    assert note.read_bytes() == b"changed by someone else\n"


def test_crlf_and_bom_round_trip_through_the_hash(vault):
    _install_helper(vault)
    original = "﻿" + NOTE.replace("\n", "\r\n")
    note = vault / "a.md"
    note.write_bytes(original.encode("utf-8"))
    assert note_io.read_exact(note) == original
    note_io.write_exact_if_unchanged(note, original + "x\r\n", original, vault_root=vault)
    assert note.read_bytes() == (original + "x\r\n").encode("utf-8")


def test_a_configured_helper_that_is_missing_fails_closed(vault, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_TRANSACTION_HELPER", str(vault / "nowhere.py"))
    note = vault / "a.md"
    note.write_bytes(NOTE.encode())
    with pytest.raises(FileNotFoundError):
        note_io.write_exact_if_unchanged(note, "x\n", NOTE, vault_root=vault)
    assert note.read_bytes() == NOTE.encode()


def test_a_configured_helper_wins_over_the_vault_copy(vault, monkeypatch, tmp_path):
    elsewhere = tmp_path / "deployed" / "vault_transaction.py"
    elsewhere.parent.mkdir()
    shutil.copy(BUNDLED_HELPER, elsewhere)
    monkeypatch.setenv("OBSIDIAN_TRANSACTION_HELPER", str(elsewhere))
    assert note_io.transaction_helper(vault) == elsewhere


def test_the_expected_hash_is_over_the_exact_bytes():
    text = "﻿café\r\n"
    assert note_io._source_hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert note_io._source_hash(None) is None


# --- callers -------------------------------------------------------------------

def test_research_appenders_use_the_helper_and_keep_crlf(vault, monkeypatch):
    from research.lib import vault as research_vault

    _install_helper(vault)
    monkeypatch.setattr(research_vault, "VAULT_PATH", vault)
    log = vault / "log.md"
    log.write_bytes(b"# Log\r\n")
    assert research_vault.append_to_log("found a thing") is True
    data = log.read_bytes()
    assert data.startswith(b"# Log\r\n") and b"found a thing\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b""), "no bare LF mixed into a CRLF log"
    assert len(_journals(vault)) == 1


def test_research_notes_never_overwrite_an_earlier_one(vault, monkeypatch):
    from research.lib import vault as research_vault

    monkeypatch.setattr(research_vault, "VAULT_PATH", vault)
    first = research_vault.write_note("research", "same topic", {"type": "research"}, "one")
    second = research_vault.write_note("research", "same topic", {"type": "research"}, "two")
    assert first != second and second.name.endswith("(2).md")
    assert "one" in first.read_text(encoding="utf-8")
    assert "two" in second.read_text(encoding="utf-8")


def test_every_rewriting_caller_passes_the_vault_root():
    """A caller that forgets vault_root silently writes around the helper."""
    for rel in ("scripts/heal_links.py", "scripts/triage_links.py", "scripts/research/lib/vault.py"):
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        calls = source.count("write_exact_if_unchanged(") - source.count("import write_exact_if_unchanged")
        calls -= source.count("NoteChangedError, read_exact, write_exact_if_unchanged")
        assert calls > 0, rel
        assert source.count("vault_root=") >= calls, f"{rel} has a guarded write without vault_root"
        assert ".write_text(" not in source, f"{rel} still writes a note around note_io"
