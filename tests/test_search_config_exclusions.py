"""Configured non-knowledge directories must not contaminate retrieval."""
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/obsidian-mcp-server"))


def test_search_respects_config_and_config_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    import vault_ops
    ops = importlib.reload(vault_ops)
    (tmp_path / "real.md").write_text("needle", encoding="utf-8")
    for folder in (".astra-audit", "Archive/Generated", "Archive/GeneratedExtra"):
        directory = tmp_path / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "needle.md").write_text("needle " * 100, encoding="utf-8")
    config = tmp_path / ".vault-config.json"
    config.write_text(json.dumps({"exclude-dirs": [".ASTRA-AUDIT"], "exclude-paths": ["Archive/Generated"]}))
    paths = {r["path"] for r in ops.search("needle", semantic=False)}
    assert paths == {"real.md", "Archive/GeneratedExtra/needle.md"}
    config.write_text('{}')
    assert len(ops.search("needle", semantic=False)) == 4


@pytest.mark.parametrize("config", ['{', '[]', '{"exclude-dirs":"private"}'])
def test_invalid_exclusion_config_fails_visibly(tmp_path, monkeypatch, config):
    import vault_ops
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    (tmp_path / ".vault-config.json").write_text(config)
    with pytest.raises(ValueError):
        vault_ops.search("needle", semantic=False)


def test_semantic_fusion_cannot_restore_excluded_index_entries(tmp_path, monkeypatch):
    import vault_ops

    (tmp_path / vault_ops._SEMANTIC_INDEX_FILE).write_text('{}')
    monkeypatch.setattr(vault_ops, '_load_index_cached', lambda path: {
        'notes': {'allowed.md': {'_unit': [[1.0, 0.0]]},
                  'excluded.md': {'_unit': [[1.0, 0.0]]}}})
    monkeypatch.setattr(vault_ops, '_embed_query', lambda *args, **kwargs: [1.0, 0.0])
    hits = vault_ops._semantic_fuse('query', [], tmp_path, 10, enabled=True, scanned=['allowed.md'])
    assert [hit['path'] for hit in hits] == ['allowed.md']
