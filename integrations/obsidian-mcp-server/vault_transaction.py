"""Cooperative, hash-checked vault writes with crash recovery.

This is not an authorization service or an Obsidian Sync lock. All participating
agents must use it; external editors can still race a check and replacement.
Requests contain operation_id and writes [{path, expected_sha256, content}].
An expected hash of null means create-only. Existing files require their hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path


class Conflict(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read_bytes(path):
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.vault-write-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)  # noqa: PTH105 - shared helper preserves this syscall
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    if path.read_bytes() != data:
        raise Conflict(f'Saved bytes changed: {path.name}')


def reject_reparse(root, target):
    for component in [root, *target.relative_to(root).parents, target]:
        candidate = component if component.is_absolute() else root / component
        if is_reparse(candidate):
            raise ValueError('Symlink/junction paths are not supported')


def is_reparse(path):
    if path.is_symlink():
        return True
    try:
        info = path.lstat()
        return bool(getattr(info, 'st_file_attributes', 0) & 0x400 or getattr(info, 'st_reparse_tag', 0))
    except FileNotFoundError:
        return False


def target_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Use a vault-relative path with forward slashes')
    path = Path(relative)
    if path.is_absolute() or any(part in {'..', '.'} or ':' in part for part in path.parts):
        raise ValueError('Path must stay in the vault')
    if not path.parts or path.suffix.lower() != '.md':
        raise ValueError('Only Markdown note writes are supported')
    if any(part.startswith(('.', '_')) for part in path.parts):
        raise ValueError('Operating and hidden paths require their dedicated workflow')
    if path.parts[0].lower() in {'templates', 'finances'}:
        raise ValueError('Protected folder requires its dedicated workflow')
    if len(path.parts) == 1 and path.name.lower() in {'agents.md', 'claude.md', 'gemini.md'}:
        raise ValueError('Agent manuals require their dedicated workflow')
    target = root / path
    reject_reparse(root, target)
    if not target.resolve().is_relative_to(root):
        raise ValueError('Path escapes the vault')
    return target


@contextmanager
def writer_lock(root):
    state = root / '.vault-runtime'
    reject_reparse(root, state)
    state.mkdir(exist_ok=True)
    lock = state / 'writer.lock'
    reject_reparse(root, lock)
    with lock.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise Conflict('Another participating writer holds the vault lock') from error
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise Conflict('Another participating writer holds the vault lock') from error
        try:
            yield state
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def normalize_request(root, request):
    operation_id = request.get('operation_id')
    if not isinstance(operation_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', operation_id):
        raise ValueError('operation_id must be a stable identifier of 1-96 safe characters')
    writes = request.get('writes')
    if not isinstance(writes, list) or not 1 <= len(writes) <= 30:
        raise ValueError('A transaction needs 1-30 note writes')
    seen = set()
    normalized = []
    for item in writes:
        target = target_path(root, item['path'])
        key = str(target).casefold()
        if key in seen:
            raise ValueError('Duplicate target')
        seen.add(key)
        expected = item['expected_sha256']
        if expected is not None and not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError('Expected hash must be SHA-256 or null for create-only')
        content = item['content']
        if not isinstance(content, str) or len(content.encode('utf-8')) > 4_000_000:
            raise ValueError('Content must be UTF-8 text, at most 4MB per note')
        normalized.append({'path': item['path'], 'expected_sha256': expected, 'content': content})
    result = {'operation_id': operation_id, 'writes': normalized}
    if request.get('read_checks'):
        checks = []
        for item in request['read_checks']:
            target_path(root, item['path'])
            if not isinstance(item.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', item['sha256']):
                raise ValueError('Read checks require SHA-256')
            checks.append({'path': item['path'], 'sha256': item['sha256']})
        result['read_checks'] = checks
    return result


def save_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))


def apply(root, request, *, recover=False):
    root = Path(root).absolute()
    if is_reparse(root):
        raise ValueError('Vault root must not be a reparse point')
    root = root.resolve(strict=True)
    request = normalize_request(root, request)
    request_hash = digest(json.dumps(request, sort_keys=True).encode('utf-8'))
    with writer_lock(root) as state:
        journal_dir = state / 'transactions'
        reject_reparse(root, journal_dir)
        journal_dir.mkdir(exist_ok=True)
        journal_path = journal_dir / (request['operation_id'] + '.json')
        for path in journal_dir.glob('*.json'):
            reject_reparse(root, path)
            previous = json.loads(path.read_text(encoding='utf-8'))
            if path != journal_path and previous['state'] != 'committed':
                raise Conflict(f"Unresolved transaction: {path.stem}")
        if journal_path.exists():
            journal = json.loads(journal_path.read_text(encoding='utf-8'))
            expanded_hash = digest(json.dumps(journal['request'], sort_keys=True).encode('utf-8'))
            if journal['request_hash'] != request_hash and expanded_hash != request_hash:
                raise Conflict('Idempotency identifier reused with different content')
            if journal['state'] == 'committed':
                return journal
            if not recover:
                raise Conflict('Interrupted transaction; inspect journal and explicitly recover')
        else:
            if recover:
                raise Conflict('No transaction exists to recover')
            original_request = request
            # The task extension adds dependent invalidations to this same batch.
            # No import or dependency is needed for vaults without packet tasks.
            if (root / 'Tasks/PA').exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location('packet_invalidation', Path(__file__).with_name('packet_invalidation.py'))
                extension = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(extension)
                reject_reparse(root, root / 'Tasks/PA')
                request = normalize_request(root, extension.expand_invalidations(root, request))
            entries = []
            for item in request['writes']:
                current = read_bytes(target_path(root, item['path']))
                if digest(current) != item['expected_sha256']:
                    raise Conflict(f"Stale source: {item['path']}")
                entries.append({'path': item['path'], 'before_sha256': digest(current),
                                'after_sha256': digest(item['content'].encode('utf-8')),
                                'before_utf8': current.decode('utf-8') if current is not None else None})
            journal = {'operation_id': request['operation_id'], 'request_hash': request_hash,
                       'state': 'prepared', 'request': request, 'files': entries,
                       'original_request': original_request}
            check_reads(root, request, entries, recovering=False)
            save_json(journal_path, journal)
        request = journal['request']
        check_reads(root, request, journal['files'], recovering=True)
        # Preflight every remaining target before resuming a partial commit.
        for entry in journal['files']:
            current_hash = digest(read_bytes(target_path(root, entry['path'])))
            if current_hash not in {entry['before_sha256'], entry['after_sha256']}:
                raise Conflict(f"Concurrent edit needs manual reconciliation: {entry['path']}")
        journal['state'] = 'applying'
        save_json(journal_path, journal)
        for item, entry in zip(request['writes'], journal['files']):
            target = target_path(root, item['path'])
            current_hash = digest(read_bytes(target))
            if current_hash == entry['after_sha256']:
                continue
            if current_hash != entry['before_sha256']:
                raise Conflict(f"Concurrent edit: {entry['path']}")
            atomic_write(target, item['content'].encode('utf-8'))
        for entry in journal['files']:
            if digest(read_bytes(target_path(root, entry['path']))) != entry['after_sha256']:
                raise Conflict('Final verification failed; transaction remains unresolved')
        journal['state'] = 'committed'
        save_json(journal_path, journal)
        return journal


def check_reads(root, request, entries, *, recovering):
    """Check dependencies inside the writer lock, including before recovery."""
    after = {e['path'].casefold(): e['after_sha256'] for e in entries}
    for item in request.get('read_checks', []):
        accepted = {item['sha256']}
        if recovering and item['path'].casefold() in after:
            accepted.add(after[item['path'].casefold()])
        if digest(read_bytes(target_path(root, item['path']))) not in accepted:
            raise Conflict('Read dependency changed: ' + item['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True, type=Path)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--recover', action='store_true')
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding='utf-8-sig'))
    if not args.apply:
        normalize_request(args.vault.resolve(strict=True), request)
        print(json.dumps({'state': 'validated-only', 'note': 'No writes performed; source hashes not yet checked'}))
    else:
        receipt = apply(args.vault, request, recover=args.recover)
        print(json.dumps({'state': receipt['state'], 'operation_id': receipt['operation_id']}))


if __name__ == '__main__':
    main()
