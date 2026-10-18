"""note_io.py - byte-exact read/write for scripts that rewrite vault notes in place.

Scripts that only READ a note may decode forgivingly (errors="replace"); a lossy
copy that dies in memory hurts nobody. A script that reads, edits, and WRITES BACK
must never do that: every undecodable byte would be saved to disk as a permanent
U+FFFD, and the text-mode round-trip would silently rewrite CRLF line endings.

Rule enforced here: strict UTF-8 in, byte-exact UTF-8 out, and a file we cannot
decode losslessly is never rewritten at all.

Writes are atomic. A note is rewritten by writing a sibling temp file and renaming
it over the target, so an interrupted write (Ctrl-C, a crash, a disk that fills
mid-write) can never leave a real note truncated or half-written. The original
survives untouched until one final same-filesystem rename swaps the new bytes in.

Atomic is not the same as safe from a concurrent writer (#217). Every caller here
reads a note, transforms the text, and writes it back, and the gap between the
read and the write is where a second writer's change is lost - silently, because
both writes succeed. A multi-adapter vault runs in exactly that shape: a Hermes
cron agent and a live session against one vault, plus LiveSync landing a third
device's edits as a local file change. `write_exact_if_unchanged` closes that by
checking, immediately before the rename, that the note still holds the bytes the
caller read. It refuses rather than overwrites. See NoteChangedError.

A vault that runs the shared transaction helper (the one the MCP server uses:
`OBSIDIAN_TRANSACTION_HELPER`, else `<vault>/scripts/vault_transaction.py`)
gets more than that. Pass `vault_root` and the write goes through the helper
instead: one writer lock shared with every other participating agent, a
SHA-256 source check made under that lock, and a recoverable journal. A vault
without the helper is written exactly as before.
"""
import hashlib
import importlib.util
import os
import stat as stat_mod
import tempfile
import uuid
from pathlib import Path


class NoteChangedError(RuntimeError):
    """A note changed on disk between the caller's read and its write (#217).

    Carries `path` so a caller processing many notes can report which one it
    skipped and keep going. Raised, never swallowed: the whole point is that a
    lost update stops being silent.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        super().__init__(
            f"{self.path} changed on disk since it was read - refusing to overwrite. "
            "Another writer (a scheduled agent, a second session, or a sync client) "
            "edited it; re-read the note and redo the change."
        )


class TransactionRefusedError(NoteChangedError):
    """The vault's transaction helper refused the write.

    A stale source hash, a held lock, or an unresolved journal from an earlier
    interrupted write. A NoteChangedError subclass, so batch callers already
    skip the note and carry on; the helper's own reason is kept as __cause__.
    Never bypass it with a direct write: an unresolved journal is waiting to
    be inspected and recovered.
    """

    def __init__(self, path: Path, reason: BaseException):
        RuntimeError.__init__(
            self, f"{Path(path)} - the vault's transaction helper refused the write: {reason}"
        )
        self.path = Path(path)


def transaction_helper(vault_root: Path) -> Path | None:
    """The shared transaction helper for this vault, or None when it has none.

    Same discovery as the MCP server's writes, minus its bundled fallback: a
    vault that never deployed a helper keeps note_io's own direct writes. An
    explicitly configured OBSIDIAN_TRANSACTION_HELPER that is missing fails
    closed rather than silently writing around it.
    """
    configured = os.environ.get("OBSIDIAN_TRANSACTION_HELPER", "").strip()
    if configured:
        helper = Path(configured).expanduser()
        if not helper.is_file():
            raise FileNotFoundError(f"OBSIDIAN_TRANSACTION_HELPER not found: {helper}")
        return helper
    helper = Path(vault_root) / "scripts" / "vault_transaction.py"
    return helper if helper.is_file() else None


def _load_helper(helper: Path):
    spec = importlib.util.spec_from_file_location("obsidian_shared_transaction", helper)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


def _source_hash(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_exact(path: Path) -> str | None:
    """Decode the file as strict UTF-8, or return None if it is not valid UTF-8.

    Bytes are decoded directly, so CRLF line endings and a leading BOM survive in
    the returned text and round-trip unchanged through write_exact.
    """
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def write_exact(path: Path, text: str) -> None:
    """Rewrite path with text as UTF-8 bytes, atomically and with no newline translation.

    The bytes go to a temp file in the same directory, so the closing os.replace is a
    same-filesystem rename (atomic on POSIX and Windows). If the write is interrupted
    or fails before that rename, the temp file is removed and the original note is left
    exactly as it was. The target's permission bits are carried over so a rewrite never
    quietly changes a note's mode.
    """
    data = text.encode("utf-8")
    directory = path.parent
    try:
        keep_mode = stat_mod.S_IMODE(Path(path).stat().st_mode)
    except OSError:
        keep_mode = None  # new file: let the umask decide, as write_bytes would have

    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass  # durability is best-effort; the atomic rename is not
        if keep_mode is not None:
            Path(tmp).chmod(keep_mode)
        Path(tmp).replace(path)
    except BaseException:
        # Interrupted or failed before the rename: the original is untouched. Drop
        # the temp so a half-written file never lingers in the vault, then re-raise.
        # BaseException (not Exception) so a Ctrl-C mid-write still cleans up.
        try:
            Path(tmp).unlink()
        except OSError:
            pass
        raise


def write_exact_if_unchanged(
    path: Path, text: str, expected: str | None, *, vault_root: Path | None = None
) -> None:
    """write_exact, but only while the note still holds the bytes it was read with.

    `expected` is what read_exact returned for this path, or None when the caller
    means "this note must not exist yet". If the file on disk no longer matches,
    nothing is written and NoteChangedError is raised.

    With `vault_root`, a vault that runs the shared transaction helper gets the
    write through it (see the module docstring); a refusal raises
    TransactionRefusedError, a NoteChangedError.

    What this does and does not buy. It does not make the read and the write one
    operation - a writer that lands between the comparison below and the rename
    a few microseconds later still wins. What it removes is the window that
    actually loses data here: the seconds or minutes an agent spends thinking
    between reading a note and writing it back, during which a cron agent, a
    second session, or a sync client rewrites the same file. A lock would not
    cover the last of those anyway, because a change replicated onto disk by a
    sync client participates in no lock this process could hold.

    The comparison is over bytes, not mtime: a same-size edit inside one
    timestamp tick is invisible to stat on a filesystem with coarse timestamps,
    and a synced vault is exactly where those turn up.
    """
    helper = transaction_helper(vault_root) if vault_root is not None else None
    if helper is not None:
        root = Path(vault_root).resolve()
        rel = Path(path).resolve().relative_to(root).as_posix()  # ValueError if outside
        request = {
            "operation_id": f"note-io-{uuid.uuid4().hex}",
            "writes": [{"path": rel, "expected_sha256": _source_hash(expected), "content": text}],
        }
        engine = _load_helper(helper)
        try:
            engine.apply(root, request)
        except Exception as exc:  # the helper's Conflict, a held lock, a rejected path
            raise TransactionRefusedError(path, exc) from exc
        return
    if expected is None:
        # "must not exist yet" is checked as absence, never as a read result:
        # read_exact returns None for a file that is not valid UTF-8 too, and
        # treating that as absent would let this clobber the one class of file
        # the module exists to refuse to rewrite.
        if path.exists():
            raise NoteChangedError(path)
    elif read_exact(path) != expected:
        raise NoteChangedError(path)
    write_exact(path, text)
