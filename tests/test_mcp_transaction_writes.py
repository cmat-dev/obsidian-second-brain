"""Read-to-write conflicts and shared recoverable MCP transactions."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('guarded_mcp_ops', ROOT / 'integrations/obsidian-mcp-server/vault_ops.py')
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)

NOTE = '---\ntype: note\ndate: 2026-10-14\ntags: [note]\nai-first: true\n---\n\n## For future agent\n\nOriginal body.\n'


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / 'vault'
    root.mkdir()
    (root / 'Inbox').mkdir()
    (root / 'index.md').write_bytes(b'# Catalog\n\n## Inbox/\n\n')
    (root / 'log.md').write_bytes(b'# Log\n')
    (root / 'note.md').write_bytes(NOTE.encode())
    monkeypatch.setenv('OBSIDIAN_VAULT_PATH', str(root))
    monkeypatch.setenv('OBSIDIAN_MCP_REQUIRE_READ_HASH', '1')
    monkeypatch.setenv('OBSIDIAN_MCP_AGENT', 'grok-bot')
    monkeypatch.setenv('OBSIDIAN_MCP_ALLOW_FRONTMATTER', '0')
    monkeypatch.delenv('OBSIDIAN_TRANSACTION_HELPER', raising=False)
    monkeypatch.delenv('OBSIDIAN_POST_WRITE_CMD', raising=False)
    return root


def test_hash_covers_the_same_bytes_as_paginated_read(vault):
    data = ('\ufeff' + NOTE.replace('\n', '\r\n')).encode()
    (vault / 'note.md').write_bytes(data)
    first = ops.read_note('note.md', limit=20)
    second = ops.read_note('note.md', offset=20)
    assert first['sha256'] == second['sha256'] == hashlib.sha256(data).hexdigest()
    assert first['truncated']


@pytest.mark.parametrize('mutation', ['update', 'replace', 'move'])
def test_edit_between_client_read_and_submission_is_refused(vault, mutation):
    expected = ops.read_note('note.md')['sha256']
    theirs = NOTE + '\nHuman edit.\n'
    (vault / 'note.md').write_bytes(theirs.encode())
    if mutation == 'update':
        result = ops.update_note('note.md', append='Agent edit.', expected_sha256=expected)
    elif mutation == 'replace':
        result = ops.replace_text('note.md', 'Original body.', 'Agent edit.', expected_sha256=expected)
    else:
        result = ops.move_note('note.md', 'Inbox/moved.md', expected_sha256=expected)
    assert 'changed on disk' in result['error']
    assert (vault / 'note.md').read_bytes() == theirs.encode()
    assert not (vault / 'Inbox/moved.md').exists()


def test_update_requires_a_client_read_hash(vault):
    assert 'supply its sha256' in ops.update_note('note.md', append='x')['error']


def test_note_catalog_and_log_commit_together_with_agent_provenance(vault):
    result = ops.save_note('Scratch', 'A scratch capture.', note_type='idea')
    assert 'saved' in result, result
    note = (vault / result['saved']).read_text()
    assert 'agent: "grok-bot"' in note
    assert '[grok-bot]' in (vault / 'log.md').read_text()
    assert '[[Inbox/' in (vault / 'index.md').read_text()
    journal = json.loads((vault / '.vault-runtime/transactions' / (result['transaction_id'] + '.json')).read_text())
    assert journal['state'] == 'committed'
    assert {w['path'] for w in journal['request']['writes']} == {result['saved'], 'index.md', 'log.md'}
    before = {p: (vault / p).read_bytes() for p in [result['saved'], 'index.md', 'log.md']}
    duplicate = ops.save_note('Scratch', 'A scratch capture.', note_type='idea')
    assert 'already exists' in duplicate['error']
    assert all((vault / p).read_bytes() == data for p, data in before.items())


def test_create_race_does_not_overwrite_new_note_or_bookkeeping(vault, monkeypatch):
    original = ops._bookkeeping_plan
    raced = vault / 'Inbox/2026-10-14 - race.md'
    def race(*args, **kwargs):
        raced.write_bytes(b'Human created this.')
        return original(*args, **kwargs)
    monkeypatch.setattr(ops, '_bookkeeping_plan', race)
    result = ops.save_note('Race', 'Agent body.', path='Inbox/2026-10-14 - race.md')
    assert 'error' in result
    assert raced.read_bytes() == b'Human created this.'
    assert (vault / 'log.md').read_bytes() == b'# Log\n'


def test_catalog_race_retries_only_metadata_and_preserves_other_entry(vault, monkeypatch):
    real_engine = ops._transaction_engine(vault)
    real_apply = real_engine.apply
    attempts = []
    def raced_apply(root, request):
        attempts.append(request)
        if len(attempts) == 1:
            with (root / 'index.md').open('ab') as fh:
                fh.write(b'- [[Other]] - Human addition.\n')
        return real_apply(root, request)
    real_engine.apply = raced_apply
    monkeypatch.setattr(ops, '_transaction_engine', lambda _: real_engine)
    result = ops.save_note('Race', 'Agent body.')
    assert 'saved' in result, result
    assert len(attempts) == 2
    index = (vault / 'index.md').read_text()
    assert '[[Other]]' in index and '[[Inbox/' in index
    assert (vault / 'log.md').read_text().count('[grok-bot]') == 1


def test_frontmatter_policy_cannot_be_bypassed_by_exact_patch(vault):
    expected = ops.read_note('note.md')['sha256']
    assert 'disabled' in ops.update_note('note.md', set_fields={'owner': 'agent'}, expected_sha256=expected)['error']
    assert 'disabled' in ops.replace_text('note.md', 'type: note', 'type: person', expected_sha256=expected)['error']
    result = ops.replace_text('note.md', 'Original body.', 'Updated body.', expected_sha256=expected)
    assert 'updated' in result, result
    assert 'agent:' not in (vault / 'note.md').read_text()
    assert '[grok-bot]' in (vault / 'log.md').read_text()


def test_frontmatter_policy_guards_the_closing_fence(vault, monkeypatch):
    monkeypatch.delenv('OBSIDIAN_MCP_AGENT')
    expected = ops.read_note('note.md')['sha256']
    result = ops.replace_text('note.md', 'true\n---\n', 'true\n---not-a-fence\n', expected_sha256=expected)
    assert 'disabled' in result['error']
    assert (vault / 'note.md').read_bytes() == NOTE.encode()


def test_patch_provenance_preserves_the_frontmatter_body_gap(vault):
    (vault / 'note.md').write_bytes(NOTE.replace('\n', '\r\n').encode())
    expected = ops.read_note('note.md')['sha256']
    result = ops.replace_text('note.md', 'Original body.', 'Changed body.', expected_sha256=expected)
    assert 'updated' in result, result
    data = (vault / 'note.md').read_bytes()
    assert b'---\r\n\r\n## For future agent' in data
    assert b'---\r\n\r\n\r\n' not in data


def test_byte_exact_sources_preserve_bom_and_crlf(vault):
    (vault / 'note.md').write_bytes(('\ufeff' + NOTE.replace('\n', '\r\n')).encode())
    expected = ops.read_note('note.md')['sha256']
    result = ops.update_note('note.md', append='Extra body.', expected_sha256=expected)
    assert 'updated' in result, result
    data = (vault / 'note.md').read_bytes()
    assert data.startswith(b'\xef\xbb\xbf')
    assert b'\n' not in data.replace(b'\r\n', b'')


def test_no_frontmatter_policy_allows_a_true_append_for_routines(vault):
    before = (vault / 'note.md').read_bytes()
    expected = ops.read_note('note.md')['sha256']
    result = ops.update_note('note.md', append='Routine audit append.', expected_sha256=expected)
    assert 'updated' in result, result
    assert (vault / 'note.md').read_bytes().startswith(before)
    assert result['set'] == []


def test_invalid_utf8_is_never_rewritten(vault):
    bad = b'\xff broken text'
    (vault / 'note.md').write_bytes(bad)
    result = ops.update_note('note.md', append='x', expected_sha256=hashlib.sha256(bad).hexdigest())
    assert 'UTF-8' in result['error']
    assert (vault / 'note.md').read_bytes() == bad


@pytest.mark.parametrize('path', ['AGENTS.md', '_Claude-Context/rules.md', 'Finances/private.md', '.obsidian/config.md'])
def test_shared_helper_refuses_protected_writes(vault, path):
    result = ops.save_note('Private', 'Protected.', path=path)
    assert 'error' in result
    assert not (vault / path).exists()


def test_unresolved_journal_blocks_new_writes(vault):
    journals = vault / '.vault-runtime/transactions'
    journals.mkdir(parents=True)
    (journals / 'interrupted.json').write_text(json.dumps({'state': 'applying'}))
    result = ops.save_note('Blocked', 'Should not save.')
    assert 'Unresolved transaction' in result['error']
    assert not list((vault / 'Inbox').glob('*.md'))


def test_grok_flavour_lists_the_exact_available_command_bank(vault, tmp_path, monkeypatch):
    commands = tmp_path / 'commands'
    commands.mkdir()
    for name in ['obsidian-save', 'obsidian-health', 'obsidian-init']:
        (commands / (name + '.md')).write_text('---\ndescription: A command\n---\n\nRead index.md and write the note.\n')
    monkeypatch.setenv('OBSIDIAN_COMMANDS_DIR', str(commands))
    monkeypatch.setenv('OBSIDIAN_SKILL_FLAVOR', 'grok-bot')
    assert {s['name'] for s in ops.list_skills()} == {p.stem for p in commands.glob('*.md')}
    instructions = ops.get_skill('obsidian-save')['instructions']
    assert 'obsidian_read_note' in instructions
    assert 'Composio' in instructions


def test_explicit_missing_scan_policy_fails_closed(vault, monkeypatch):
    monkeypatch.setenv('OBSIDIAN_VAULT_CONFIG', str(vault / 'not-present.json'))
    with pytest.raises(ValueError, match='scan policy is missing'):
        ops.search('Original')


def test_explicit_private_rules_are_embedded_and_never_silently_replaced(vault, tmp_path, monkeypatch):
    commands = tmp_path / 'commands'
    commands.mkdir()
    (commands / 'obsidian-save.md').write_text('---\ndescription: Save\n---\n\nWrite a note.')
    rules = tmp_path / 'private-rules.md'
    rules.write_text('Private configured AI-first rule.')
    monkeypatch.setenv('OBSIDIAN_COMMANDS_DIR', str(commands))
    monkeypatch.setenv('OBSIDIAN_SKILL_FLAVOR', 'grok-bot')
    monkeypatch.setenv('OBSIDIAN_AI_FIRST_RULES', str(rules))
    assert 'Private configured AI-first rule.' in ops.get_skill('obsidian-save')['instructions']
    rules.unlink()
    assert 'missing' in ops.get_skill('obsidian-save')['error']
