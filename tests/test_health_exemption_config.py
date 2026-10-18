"""`frontmatter-exempt` and `orphan-exempt` in `<vault>/.vault-config.json`.

Some notes are kept on purpose without frontmatter or incoming links: generated
working files, agent manuals, a skill folder synced into the vault. The checks
are right that they look like defects and cannot know they are not, and before
these keys the only way to quiet them was to edit vault_health.py, which every
update undid. These run the real script, as test_user_excludes.py does, and each
positive test fails on the code without the keys.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import vault_health  # noqa: E402

LONG = "plain text with no frontmatter, long enough to be reported " * 2 + "\n"


def _health(vault: Path) -> list:
    result = subprocess.run(
        [sys.executable, "scripts/vault_health.py", "--path", str(vault), "--json"],
        cwd=REPO_ROOT, check=False, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout[result.stdout.find("{"):]).get("issues", [])


def _files(issues: list, kind: str) -> set:
    return {i["files"][0] for i in issues if i["type"] == kind}


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "Reviews" / "Generated" / "deep").mkdir(parents=True)
    (vault / "Reviews" / "Generated" / "deep" / "run.md").write_text(LONG, encoding="utf-8")
    (vault / "Skills" / "tool").mkdir(parents=True)
    (vault / "Skills" / "tool" / "SKILL.md").write_text("---\ntype: skill\n---\nx\n", encoding="utf-8")
    (vault / "kept.md").write_text(LONG, encoding="utf-8")
    return vault


def test_without_config_both_are_reported(tmp_path):
    issues = _health(_vault(tmp_path))
    assert "Reviews/Generated/deep/run.md" in _files(issues, "no_frontmatter")
    assert "Skills/tool/SKILL.md" in _files(issues, "orphan")


def test_frontmatter_exempt_glob_covers_a_subtree(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".vault-config.json").write_text(
        json.dumps({"frontmatter-exempt": ["Reviews/Generated/*"]}), encoding="utf-8")
    issues = _health(vault)
    assert "Reviews/Generated/deep/run.md" not in _files(issues, "no_frontmatter")
    assert "kept.md" in _files(issues, "no_frontmatter"), "only the glob is exempt"


def test_orphan_exempt_matches_a_bare_filename_anywhere(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".vault-config.json").write_text(
        json.dumps({"orphan-exempt": ["SKILL.md"]}), encoding="utf-8")
    issues = _health(vault)
    assert "Skills/tool/SKILL.md" not in _files(issues, "orphan")
    assert "kept.md" in _files(issues, "orphan"), "only the glob is exempt"


def test_an_exemption_is_scoped_to_its_own_check(tmp_path):
    """Exempting a note from the orphan check leaves it in the frontmatter check."""
    vault = _vault(tmp_path)
    (vault / ".vault-config.json").write_text(
        json.dumps({"orphan-exempt": ["kept.md"]}), encoding="utf-8")
    issues = _health(vault)
    assert "kept.md" not in _files(issues, "orphan")
    assert "kept.md" in _files(issues, "no_frontmatter")


def test_malformed_values_are_ignored_not_fatal(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".vault-config.json").write_text(
        json.dumps({"frontmatter-exempt": "Reviews/*", "orphan-exempt": [3, None, ""]}),
        encoding="utf-8")
    issues = _health(vault)
    assert "Reviews/Generated/deep/run.md" in _files(issues, "no_frontmatter")


def test_config_loader_reads_both_keys(tmp_path):
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / ".vault-config.json").write_text(json.dumps({
        "frontmatter-exempt": ["A\\*"], "orphan-exempt": ["B/*"],
    }), encoding="utf-8")
    excludes = vault_health.load_vault_config(vault)
    assert excludes.frontmatter_exempt == ["A/*"], "Windows separators are normalised"
    assert excludes.orphan_exempt_note("B/c/d.md")
    assert not excludes.orphan_exempt_note("C/d.md")
