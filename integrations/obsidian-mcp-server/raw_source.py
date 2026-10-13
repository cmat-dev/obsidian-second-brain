"""Create-only raw source validation and deterministic source fingerprints.

Extraction of article text is the caller's responsibility. Hash normalization
does not infer which text is navigation, metadata, or article content.
"""

from __future__ import annotations

import hashlib
import re
import stat
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SOURCE_FOLDERS = frozenset({"articles", "transcripts", "pdfs", "videos"})
SOURCE_TYPES = frozenset({"article", "pdf", "transcript", "video", "audio", "image", "text"})
SOURCE_FIELDS = frozenset({"source_url", "source_type", "content_hash", "capture_scope", "supersedes"})
REQUIRED_FIELDS = frozenset({"source_url", "source_type", "content_hash"})
CAPTURE_SCOPES = frozenset({"full-local", "bounded-local", "url-only"})
MAX_CONTENT_BYTES = 4_000_000


def content_hashes(content: str) -> dict[str, str]:
    """Fingerprint exact UTF-8 and normalized caller-extracted source text."""
    if not isinstance(content, str):
        raise ValueError("content must be UTF-8 text")
    try:
        exact = content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("content must be valid UTF-8 text") from exc
    if len(exact) > MAX_CONTENT_BYTES:
        raise ValueError("content exceeds the 4MB limit")
    normalized = content.replace("\r\n", "\n").removeprefix("\ufeff")
    normalized = re.sub(r"(?m)^([ \t]*)[+*]([ \t]+)", r"\1-\2", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    canonical = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "sha256": hashlib.sha256(exact).hexdigest(),
        "canonical_sha256": canonical,
        "content_hash": canonical[:16],
    }


def _reject_reparse(vault: Path, target: Path) -> None:
    components = [vault]
    relative = target.relative_to(vault)
    components.extend(vault.joinpath(*relative.parts[:i]) for i in range(1, len(relative.parts) + 1))
    for path in components:
        try:
            attributes = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(attributes.st_mode) or (
            getattr(attributes, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError("raw sources cannot use symlink or reparse paths")


def source_path(vault: Path, requested: str, *, dated: bool = True) -> Path:
    """Only explicit direct paths in the four raw-source folders are eligible."""
    if not isinstance(requested, str) or "\\" in requested:
        raise ValueError("raw source path must use forward slashes")
    parts = requested.split("/")
    if (
        len(parts) != 3 or parts[0] != "raw" or parts[1] not in SOURCE_FOLDERS
        or any(not part or part.startswith((".", "_")) for part in parts)
        or any(char in requested for char in '\r\n\x00<>:"|?*')
        or PurePosixPath(requested).is_absolute()
        or not parts[-1].endswith(".md")
    ):
        raise ValueError("raw source path must be raw/<source-folder>/<note>.md")
    if dated:
        match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2}) - (.+)\.md", parts[-1])
        if not match:
            raise ValueError("new raw source filename must be YYYY-MM-DD - Title.md")
        try:
            date.fromisoformat(match.group(1))
        except ValueError as exc:
            raise ValueError("raw source filename must contain a valid date") from exc
    target = vault.joinpath(*parts)
    _reject_reparse(vault, target)
    if not target.resolve().is_relative_to(vault.resolve()):
        raise ValueError("raw source path is outside the vault")
    return target


def prepare_source(
    vault: Path, requested: str, content: str, metadata: dict[str, str],
    canonical_content: str | None = None,
) -> tuple[Path, dict[str, str], list[dict[str, str]]]:
    """Validate creation metadata without writing or changing an older source."""
    target = source_path(vault, requested)
    if not isinstance(content, str) or not content.removeprefix("\ufeff").strip():
        raise ValueError("raw source content must be non-empty UTF-8 text")
    if not isinstance(metadata, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()
    ):
        raise ValueError("source_metadata must contain string keys and values")
    if set(metadata) - SOURCE_FIELDS:
        raise ValueError("source_metadata contains a forbidden or unknown field")
    if REQUIRED_FIELDS - set(metadata):
        raise ValueError("source_metadata requires source_url, source_type and content_hash")
    fields = dict(metadata)
    if fields["source_type"] not in SOURCE_TYPES:
        raise ValueError("source_type is not a supported raw source type")
    if "capture_scope" in fields and fields["capture_scope"] not in CAPTURE_SCOPES:
        raise ValueError("capture_scope must be full-local, bounded-local or url-only")
    if any(len(value) > 4096 or any(ord(char) < 32 for char in value) for value in fields.values()):
        raise ValueError("source metadata values must be bounded single-line strings")

    url = fields["source_url"]
    if url:
        try:
            parsed = urlsplit(url)
            parsed.hostname.encode("idna") if parsed.hostname else None
            valid = (
                parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and (parsed.port is None or 1 <= parsed.port <= 65535)
                and parsed.username is None and parsed.password is None
                and not any(char.isspace() for char in url)
            )
        except (ValueError, UnicodeError):
            valid = False
        if not valid:
            raise ValueError("source_url must be an HTTP(S) URL or empty for local/pasted content")
    if fields.get("capture_scope") == "url-only" and not url:
        raise ValueError("url-only captures require a source_url")
    if not re.fullmatch(r"[a-f0-9]{16}", fields["content_hash"]):
        raise ValueError("content_hash must be the canonical 16-character SHA-256 prefix")
    exact = content_hashes(content)
    if canonical_content is not None and (
        not isinstance(canonical_content, str) or not canonical_content.removeprefix("\ufeff").strip()
    ):
        raise ValueError("canonical_content must be non-empty extracted source text")
    basis = content if canonical_content is None else canonical_content
    fingerprint = content_hashes(basis)
    if fields["content_hash"] != fingerprint["content_hash"]:
        raise ValueError("content_hash does not match the canonical source text; call obsidian_content_hash")
    fields["body_sha256"] = exact["sha256"]
    fields["hash_basis"] = "body" if canonical_content is None else "provided-extraction"

    read_checks = []
    if "supersedes" in fields:
        match = re.fullmatch(r"\[\[([^\]|#]+)\]\]", fields["supersedes"])
        if not match:
            raise ValueError("supersedes must be one explicit raw-note wikilink")
        previous = match.group(1)
        if not previous.endswith(".md"):
            previous += ".md"
        old = source_path(vault, previous, dated=False)
        if old == target or not old.is_file():
            raise ValueError("supersedes must refer to an existing different raw source")
        data = old.read_bytes()
        read_checks.append({"path": old.relative_to(vault).as_posix(), "sha256": hashlib.sha256(data).hexdigest()})
    return target, fields, read_checks
