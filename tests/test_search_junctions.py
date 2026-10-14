"""Search must not follow Windows directory junctions on older Python versions."""

from __future__ import annotations

import importlib
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/obsidian-mcp-server"))


def test_scan_skips_mount_point_without_path_is_junction(tmp_path, monkeypatch):
    import vault_ops

    note = tmp_path / "allowed.md"
    note.write_text("needle", encoding="utf-8")
    junction = tmp_path / "junction"
    junction.mkdir()
    (junction / "outside.md").write_text("needle", encoding="utf-8")
    original_lstat = Path.lstat

    def lstat(path, *args, **kwargs):
        if path == junction:
            return SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_reparse_tag=getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
                st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
            )
        return original_lstat(path, *args, **kwargs)

    # Simulate Python 3.10/3.11 even when this test runs on a newer interpreter.
    monkeypatch.delattr(Path, "is_junction", raising=False)
    monkeypatch.setattr(Path, "lstat", lstat)
    assert [p.relative_to(tmp_path).as_posix() for p in vault_ops._iter_notes(tmp_path)] == ["allowed.md"]


@pytest.mark.skipif(os.name != "nt", reason="native Windows junction fixture")
def test_search_does_not_return_notes_through_a_real_windows_junction(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    external = tmp_path / "outside"
    root.mkdir()
    external.mkdir()
    (root / "allowed.md").write_text("junctionguard local", encoding="utf-8")
    (external / "private.md").write_text("junctionguard external", encoding="utf-8")
    junction = root / "external"
    quote = lambda p: "'" + str(p).replace("'", "''") + "'"
    command = (
        "New-Item -ItemType Junction -Path " + quote(junction)
        + " -Target " + quote(external) + " | Out-Null"
    )
    created = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, check=False,
    )
    assert created.returncode == 0, created.stderr
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(root))
    import vault_ops

    ops = importlib.reload(vault_ops)
    assert [r["path"] for r in ops.search("junctionguard", semantic=False)] == ["allowed.md"]
