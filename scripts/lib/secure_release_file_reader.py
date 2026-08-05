"""Fail-closed file custody primitives for release contract validation."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Callable


RELEASE_FILE_SYMLINK_REJECTED = "RELEASE_FILE_SYMLINK_REJECTED"
RELEASE_FILE_HARDLINK_REJECTED = "RELEASE_FILE_HARDLINK_REJECTED"
RELEASE_FILE_NOT_REGULAR = "RELEASE_FILE_NOT_REGULAR"
RELEASE_FILE_CHANGED_DURING_READ = "RELEASE_FILE_CHANGED_DURING_READ"
RELEASE_FILE_OUTSIDE_ROOT = "RELEASE_FILE_OUTSIDE_ROOT"
RELEASE_FILE_PATH_INVALID = "RELEASE_FILE_PATH_INVALID"
RELEASE_FILE_SHA_MISMATCH = "RELEASE_FILE_SHA_MISMATCH"
RELEASE_FILE_OPEN_FAILED = "RELEASE_FILE_OPEN_FAILED"


class ReleaseFileError(ValueError):
    """A fixed-code release file custody failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SecureFileSnapshot:
    path: Path
    data: bytes
    sha256: str
    size: int
    device: int
    inode: int
    mode: int
    mtime_ns: int
    ctime_ns: int


ReadObserver = Callable[[str, Path, int, int], None]


def _fail(code: str) -> None:
    raise ReleaseFileError(code)


def validate_posix_relative_path(value: object) -> str:
    """Reject unsafe syntax without normalizing it into a safe-looking path."""

    if not isinstance(value, str) or not value or value != value.strip():
        _fail(RELEASE_FILE_PATH_INVALID)
    if "\x00" in value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        _fail(RELEASE_FILE_PATH_INVALID)
    if "\\" in value or "//" in value:
        _fail(RELEASE_FILE_PATH_INVALID)
    if re.match(r"^[A-Za-z]:", value) or re.match(
        r"^[A-Za-z][A-Za-z0-9+.-]*:", value
    ):
        _fail(RELEASE_FILE_PATH_INVALID)
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts:
        _fail(RELEASE_FILE_PATH_INVALID)
    components = value.split("/")
    if any(component in {"", ".", ".."} for component in components):
        _fail(RELEASE_FILE_PATH_INVALID)
    return value


def _absolute_without_resolution(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _require_within(path: Path, allowed_root: Path) -> tuple[Path, Path]:
    absolute_path = _absolute_without_resolution(path)
    absolute_root = _absolute_without_resolution(allowed_root)
    try:
        relative = absolute_path.relative_to(absolute_root)
    except ValueError:
        _fail(RELEASE_FILE_OUTSIDE_ROOT)
    if not relative.parts:
        _fail(RELEASE_FILE_PATH_INVALID)
    return absolute_path, absolute_root


def _reject_symlink_ancestry(path: Path, allowed_root: Path) -> None:
    cursor = path.parent
    while True:
        try:
            metadata = os.lstat(cursor)
        except OSError:
            _fail(RELEASE_FILE_OPEN_FAILED)
        if stat.S_ISLNK(metadata.st_mode):
            _fail(RELEASE_FILE_SYMLINK_REJECTED)
        if cursor == allowed_root:
            return
        if cursor == cursor.parent:
            _fail(RELEASE_FILE_OUTSIDE_ROOT)
        cursor = cursor.parent


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_secure_release_file(
    path: Path,
    *,
    allowed_root: Path,
    expected_path: Path | None = None,
    expected_sha256: str | None = None,
    chunk_size: int = 65536,
    observer: ReadObserver | None = None,
) -> SecureFileSnapshot:
    """Hash bytes from one descriptor and verify path identity after the read.

    The observer is a test-only race injector.  Production callers leave it
    unset.  It receives ``after_open``, ``after_chunk``, and
    ``before_path_identity_check`` events.
    """

    if chunk_size <= 0:
        _fail(RELEASE_FILE_PATH_INVALID)
    absolute, root = _require_within(path, allowed_root)
    if expected_path is not None and absolute != _absolute_without_resolution(expected_path):
        _fail(RELEASE_FILE_PATH_INVALID)
    _reject_symlink_ancestry(absolute, root)

    try:
        lexical = os.lstat(absolute)
    except FileNotFoundError:
        _fail(RELEASE_FILE_OPEN_FAILED)
    except OSError:
        _fail(RELEASE_FILE_OPEN_FAILED)
    if stat.S_ISLNK(lexical.st_mode):
        _fail(RELEASE_FILE_SYMLINK_REJECTED)
    if not stat.S_ISREG(lexical.st_mode):
        _fail(RELEASE_FILE_NOT_REGULAR)
    if lexical.st_nlink != 1:
        _fail(RELEASE_FILE_HARDLINK_REJECTED)

    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(os.fspath(absolute), flags)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            _fail(RELEASE_FILE_SYMLINK_REJECTED)
        _fail(RELEASE_FILE_OPEN_FAILED)

    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(RELEASE_FILE_NOT_REGULAR)
        if before.st_nlink != 1:
            _fail(RELEASE_FILE_HARDLINK_REJECTED)
        if (before.st_dev, before.st_ino) != (lexical.st_dev, lexical.st_ino):
            _fail(RELEASE_FILE_CHANGED_DURING_READ)
        if observer is not None:
            observer("after_open", absolute, descriptor, 0)

        digest = hashlib.sha256()
        chunks: list[bytes] = []
        bytes_read = 0
        while True:
            chunk = os.read(descriptor, chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            digest.update(chunk)
            bytes_read += len(chunk)
            if observer is not None:
                observer("after_chunk", absolute, descriptor, bytes_read)

        # A second read from the same descriptor catches a content mutation
        # that races the first sequential pass even on filesystems whose
        # timestamp granularity cannot make that race observable immediately.
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
        except OSError:
            _fail(RELEASE_FILE_NOT_REGULAR)
        verification_digest = hashlib.sha256()
        verification_bytes = 0
        while True:
            chunk = os.read(descriptor, chunk_size)
            if not chunk:
                break
            verification_digest.update(chunk)
            verification_bytes += len(chunk)
        if (
            verification_bytes != bytes_read
            or verification_digest.digest() != digest.digest()
        ):
            _fail(RELEASE_FILE_CHANGED_DURING_READ)

        after = os.fstat(descriptor)
        if _identity(before) != _identity(after) or bytes_read != before.st_size:
            _fail(RELEASE_FILE_CHANGED_DURING_READ)
        if observer is not None:
            observer("before_path_identity_check", absolute, descriptor, bytes_read)
        try:
            final_path = os.lstat(absolute)
        except OSError:
            _fail(RELEASE_FILE_CHANGED_DURING_READ)
        if stat.S_ISLNK(final_path.st_mode):
            _fail(RELEASE_FILE_SYMLINK_REJECTED)
        if final_path.st_nlink != 1:
            _fail(RELEASE_FILE_HARDLINK_REJECTED)
        if _identity(after) != _identity(final_path):
            _fail(RELEASE_FILE_CHANGED_DURING_READ)
        _reject_symlink_ancestry(absolute, root)

        actual_sha = digest.hexdigest()
        if expected_sha256 is not None and actual_sha != expected_sha256:
            _fail(RELEASE_FILE_SHA_MISMATCH)
        return SecureFileSnapshot(
            path=absolute,
            data=b"".join(chunks),
            sha256=actual_sha,
            size=bytes_read,
            device=after.st_dev,
            inode=after.st_ino,
            mode=stat.S_IMODE(after.st_mode),
            mtime_ns=after.st_mtime_ns,
            ctime_ns=after.st_ctime_ns,
        )
    finally:
        os.close(descriptor)


def resolve_secure_source_path(
    repository_root: Path,
    relative: object,
) -> tuple[str, Path]:
    text = validate_posix_relative_path(relative)
    root = repository_root.resolve(strict=True)
    lexical = root.joinpath(*PurePosixPath(text).parts)
    _require_within(lexical, root)
    _reject_symlink_ancestry(lexical, root)
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        _fail(RELEASE_FILE_OUTSIDE_ROOT)
    if lexical.is_symlink():
        _fail(RELEASE_FILE_SYMLINK_REJECTED)
    return text, lexical
