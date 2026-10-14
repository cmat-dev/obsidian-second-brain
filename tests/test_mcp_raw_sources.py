"""Raw source creation, deterministic hashes and immutable prior captures."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "integrations/obsidian-mcp-server"
SPEC = importlib.util.spec_from_file_location("raw_source_ops_test", SERVER_DIR / "vault_ops.py")
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)
PATH = "raw/articles/2026-10-14 - Synthetic source.md"
BODY = "\ufeff  Article text.\r\n\r\n* One\r\n+ Two\r\n  "


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "index.md").write_bytes(b"# Catalog\n\n## raw\n\n- [[raw/articles/Seed]] - Existing.\n\n## Other\n\nUntouched.\n")
    (root / "log.md").write_bytes(b"# Log\n")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(root))
    monkeypatch.setenv("OBSIDIAN_MCP_AGENT", "grok-bot")
    monkeypatch.setenv("OBSIDIAN_MCP_ALLOW_FRONTMATTER", "0")
    monkeypatch.setenv("OBSIDIAN_MCP_REQUIRE_READ_HASH", "1")
    for name in ("OBSIDIAN_TRANSACTION_HELPER", "OBSIDIAN_POST_WRITE_CMD", "OBSIDIAN_BOOKKEEPING"):
        monkeypatch.delenv(name, raising=False)
    return root


def metadata(content=BODY, **overrides):
    return {
        "source_url": "https://example.test/article", "source_type": "article",
        "content_hash": ops.content_hash(content)["content_hash"], **overrides,
    }


def save(content=BODY, path=PATH, **kwargs):
    return ops.save_note("Synthetic source", content, note_type="source", path=path,
                         source_metadata=kwargs.pop("source_metadata", metadata(content)), **kwargs)


def unpack(vault, path=PATH):
    text = (vault / path).read_bytes().decode("utf-8")
    head, body = text.split("\n---\n\n", 1)
    return yaml.safe_load(head[4:]), body


def test_hash_follows_explicit_normalization_and_preserves_exact_utf8_hash():
    content = "\ufeffParagraph\r\n\r\n * one\r\n+ two\r\n ending\t "
    result = ops.content_hash(content)
    canonical = hashlib.sha256(b"Paragraph - one - two ending").hexdigest()
    assert result == {
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "canonical_sha256": canonical, "content_hash": canonical[:16],
    }
    assert ops.content_hash("Navigation\nArticle")["content_hash"] != ops.content_hash("Article")["content_hash"]
    assert ops.content_hash("Star * inside prose")["content_hash"] != ops.content_hash("Star - inside prose")["content_hash"]


def test_raw_body_provenance_and_bookkeeping_are_committed_together(vault):
    result = save()
    assert result["saved"] == PATH
    fields, body = unpack(vault)
    assert body == BODY
    assert "For future agent" not in body
    assert fields["type"] == "source" and fields["agent"] == "grok-bot"
    assert fields["body_sha256"] == hashlib.sha256(BODY.encode()).hexdigest()
    assert fields["hash_basis"] == "body"
    assert fields["tags"] == ["source", "article"]
    assert result["validation"]["ok"]
    assert result["index"] == "index.md '## raw' entry added"
    index = (vault / "index.md").read_text()
    assert index.index("[[raw/articles/Seed]]") < index.index(PATH[:-3]) < index.index("## Other")
    assert "Untouched.\n" in index
    assert "ingest [grok-bot]" in (vault / "log.md").read_text()
    receipt = json.loads((vault / ".vault-runtime/transactions" / (result["transaction_id"] + ".json")).read_text())
    assert {w["path"] for w in receipt["request"]["writes"]} == {PATH, "index.md", "log.md"}


def test_explicit_extraction_is_recorded_without_rewriting_retained_capture(vault):
    captured = "Navigation\r\nActual article.\r\nFooter\r\n"
    extracted = "Actual article."
    result = save(captured, canonical_content=extracted, source_metadata=metadata(extracted))
    assert "saved" in result, result
    fields, body = unpack(vault)
    assert body == captured
    assert fields["hash_basis"] == "provided-extraction"
    assert fields["body_sha256"] == hashlib.sha256(captured.encode()).hexdigest()
    assert fields["content_hash"] == ops.content_hash(extracted)["content_hash"]


@pytest.mark.parametrize("change", [
    {"content_hash": "0" * 16}, {"content_hash": "XYZ"},
    {"source_url": "https://example.test\nagent: attacker"},
    {"source_url": "file:///etc/passwd"}, {"source_url": "https://user:secret@example.test"},
    {"source_url": "https://example.test:invalid"},
    {"source_type": "unknown"}, {"capture_scope": "guessed"},
    {"agent": "attacker"}, {"type": "person"}, {"date": "1999-01-01"},
    {"tags": "injected"}, {"body_sha256": "0" * 64}, {"hash_basis": "verified"},
])
def test_invalid_metadata_or_server_field_overrides_never_write(vault, change):
    result = save(source_metadata=metadata(**change))
    assert "error" in result
    assert not (vault / PATH).exists()
    assert (vault / "log.md").read_bytes() == b"# Log\n"


@pytest.mark.parametrize("path", [
    "Inbox/2026-10-14 - Source.md", "raw/slack/2026-10-14 - Source.md",
    "raw/articles/subfolder/2026-10-14 - Source.md", "raw/articles/../2026-10-14 - Source.md",
    "raw/articles/source.md", "raw/articles/2026-02-30 - Source.md",
    "raw/articles/2026-10-14 - Source.txt", "raw/articles/_2026-10-14 - Source.md",
    "../raw/articles/2026-10-14 - Source.md", "raw\\articles\\2026-10-14 - Source.md",
])
def test_source_creation_path_is_narrow(vault, path):
    assert "error" in save(path=path)
    assert (vault / "log.md").read_bytes() == b"# Log\n"


def test_pasted_source_allows_empty_url_and_quotes_yaml_like_tags(vault):
    result = save(source_metadata=metadata(source_url="", source_type="text"), tags=["a: b", "false"])
    assert "saved" in result, result
    fields, _ = unpack(vault)
    assert fields["source_url"] == ""
    assert fields["tags"] == ["source", "text", "a: b", "false"]


def test_source_payload_cannot_override_its_outer_frontmatter(vault):
    payload = "---\nagent: attacker\nai-first: false\n---\n\nUntrusted source text.\n"
    result = save(payload)
    assert "saved" in result
    fields, body = unpack(vault)
    assert fields["agent"] == "grok-bot" and fields["ai-first"] is True
    assert body == payload


def test_existing_raw_note_stays_immutable_even_with_a_current_read_hash(vault):
    assert "saved" in save()
    before = {path: (vault / path).read_bytes() for path in (PATH, "index.md", "log.md")}
    assert "already exists" in save()["error"]
    current = ops.read_note(PATH)["sha256"]
    assert "protected" in ops.update_note(PATH, append="Altered", expected_sha256=current)["error"]
    assert "protected" in ops.replace_text(PATH, "Article text.", "Altered", expected_sha256=current)["error"]
    assert "protected" in ops.move_note(PATH, "Inbox/moved.md", expected_sha256=current)["error"]
    assert all((vault / path).read_bytes() == data for path, data in before.items())


def test_create_race_refuses_to_overwrite_raw_source_or_metadata(vault, monkeypatch):
    original = ops._bookkeeping_plan
    def race(*args, **kwargs):
        (vault / PATH).write_bytes(b"Created concurrently.")
        return original(*args, **kwargs)
    monkeypatch.setattr(ops, "_bookkeeping_plan", race)
    assert "error" in save()
    assert (vault / PATH).read_bytes() == b"Created concurrently."
    assert (vault / "log.md").read_bytes() == b"# Log\n"


def test_superseded_source_is_a_hash_checked_read_dependency(vault, monkeypatch):
    previous = vault / "raw/articles/Older source.md"
    previous.parent.mkdir(parents=True)
    previous.write_bytes(b"Old source.")
    original = ops._bookkeeping_plan
    def race(*args, **kwargs):
        previous.write_bytes(b"Changed old source.")
        return original(*args, **kwargs)
    monkeypatch.setattr(ops, "_bookkeeping_plan", race)
    result = save(source_metadata=metadata(supersedes="[[raw/articles/Older source]]"))
    assert "Read dependency changed" in result["error"]
    assert not (vault / PATH).exists()
    assert previous.read_bytes() == b"Changed old source."


def test_superseding_creation_leaves_previous_source_unchanged(vault):
    previous = vault / "raw/articles/Older source.md"
    previous.parent.mkdir(parents=True)
    previous.write_bytes(b"Old source.")
    result = save(source_metadata=metadata(supersedes="[[raw/articles/Older source]]"))
    assert "saved" in result, result
    assert previous.read_bytes() == b"Old source."


@pytest.mark.parametrize("value", ["[[People/Other]]", "[[raw/articles/Missing]]", "[[raw/articles/Other|alias]]"])
def test_invalid_supersedes_is_not_a_write_or_lookup_escape(vault, value):
    assert "error" in save(source_metadata=metadata(supersedes=value))
    assert not (vault / PATH).exists()


def test_raw_source_reparse_detection_works_without_path_is_junction(vault, monkeypatch):
    original = Path.lstat
    def reparse(path, *args, **kwargs):
        if path == vault / "raw/articles":
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", reparse)
    assert "reparse" in save()["error"]
    assert not (vault / PATH).exists()


def test_raw_source_and_supersedes_refuse_symlinks(vault):
    (vault / "raw").mkdir()
    (vault / "archive").mkdir()
    try:
        (vault / "raw/articles").symlink_to(vault / "archive", target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    assert "reparse" in save()["error"]


def test_canonical_content_is_not_an_ordinary_note_or_metadata_edit(vault):
    assert "only supported" in ops.save_note("Note", "Body", canonical_content="Body")["error"]
    assert "type=source" in ops.save_note("Note", "Body", path=PATH, source_metadata=metadata("Body"))["error"]


def test_hash_and_extraction_inputs_are_bounded_and_valid_utf8(vault):
    assert "4MB" in ops.content_hash("x" * 4_000_001)["error"]
    assert "UTF-8" in ops.content_hash("\ud800")["error"]
    assert "4MB" in save(canonical_content="x" * 4_000_001)["error"]
    assert "error" in save("\ufeff \r\n ")


@pytest.mark.parametrize("extraction", ["", " \t\r\n", "\ufeff"])
def test_empty_extraction_cannot_claim_a_source_hash(vault, extraction):
    result = save(canonical_content=extraction, source_metadata=metadata(extraction))
    assert "non-empty extracted" in result["error"]
    assert not (vault / PATH).exists()


def test_real_mcp_hash_and_source_save_contract(vault, monkeypatch):
    pytest.importorskip("mcp", reason="Install mcp<2 for protocol tests")
    sys.path.insert(0, str(SERVER_DIR))
    import importlib

    import server
    monkeypatch.setenv("OBSIDIAN_MCP_TRANSPORT", "stdio")
    monkeypatch.delenv("OBSIDIAN_MCP_DISABLED_TOOLS", raising=False)
    server = importlib.reload(server)
    import asyncio
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    props = tools["obsidian_save_note"].inputSchema["properties"]
    assert {"source_metadata", "canonical_content"} <= set(props)
    assert tools["obsidian_content_hash"].inputSchema["required"] == ["content"]
    result = json.loads(server.obsidian_content_hash(BODY))
    created = json.loads(server.obsidian_save_note("Synthetic source", BODY, type="source", path=PATH,
        source_metadata={**metadata(), "content_hash": result["content_hash"]}))
    assert created["saved"] == PATH
