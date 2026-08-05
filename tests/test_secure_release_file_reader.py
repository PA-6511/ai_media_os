from __future__ import annotations

import os
from pathlib import Path
import socket

import pytest

from scripts.lib import secure_release_file_reader as secure
from scripts.validate_slack_worker_release_bundle_contract import (
    load_production_manifest,
    validate_production_manifest_contract,
)


def assert_code(code: str, action: object) -> None:
    with pytest.raises(secure.ReleaseFileError) as captured:
        action()  # type: ignore[operator]
    assert captured.value.code == code


def test_manifest_symlink_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "real.json"
    source.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "manifest.json"
    link.symlink_to(source)
    assert_code(
        secure.RELEASE_FILE_SYMLINK_REJECTED,
        lambda: secure.read_secure_release_file(link, allowed_root=tmp_path),
    )


def test_manifest_hardlink_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "real.json"
    source.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "manifest.json"
    os.link(source, link)
    assert_code(
        secure.RELEASE_FILE_HARDLINK_REJECTED,
        lambda: secure.read_secure_release_file(link, allowed_root=tmp_path),
    )


def test_manifest_directory_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "manifest.json"
    directory.mkdir()
    assert_code(
        secure.RELEASE_FILE_NOT_REGULAR,
        lambda: secure.read_secure_release_file(directory, allowed_root=tmp_path),
    )


def test_manifest_change_during_read_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(b"{\"padding\":\"" + b"A" * 100 + b"\"}\n")
    changed = False

    def observer(event: str, observed: Path, _fd: int, _count: int) -> None:
        nonlocal changed
        if event == "after_chunk" and not changed:
            changed = True
            descriptor = os.open(observed, os.O_WRONLY)
            try:
                os.pwrite(descriptor, b"B", 1)
            finally:
                os.close(descriptor)

    assert_code(
        secure.RELEASE_FILE_CHANGED_DURING_READ,
        lambda: secure.read_secure_release_file(
            path, allowed_root=tmp_path, chunk_size=16, observer=observer
        ),
    )


@pytest.mark.parametrize(
    "value",
    [
        "/absolute.py",
        "../outside.py",
        "dir/../outside.py",
        "./source.py",
        "dir/./source.py",
        "dir\\source.py",
        "dir//source.py",
        "dir/\x01source.py",
        "C:/source.py",
        "https://example.invalid/source.py",
        " source.py",
        "source.py ",
        "",
    ],
)
def test_unsafe_source_path_syntax_is_rejected(value: str) -> None:
    assert_code(
        secure.RELEASE_FILE_PATH_INVALID,
        lambda: secure.validate_posix_relative_path(value),
    )


def test_source_outside_root_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    link_parent = tmp_path / "linked"
    link_parent.symlink_to(outside.parent, target_is_directory=True)
    assert_code(
        secure.RELEASE_FILE_SYMLINK_REJECTED,
        lambda: secure.resolve_secure_source_path(
            tmp_path, f"linked/{outside.name}"
        ),
    )


def test_explicit_file_outside_root_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.bin"
    outside.write_bytes(b"outside")
    assert_code(
        secure.RELEASE_FILE_OUTSIDE_ROOT,
        lambda: secure.read_secure_release_file(outside, allowed_root=tmp_path),
    )


def test_source_symlink_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source-real.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    link = tmp_path / "source.py"
    link.symlink_to(source)
    assert_code(
        secure.RELEASE_FILE_SYMLINK_REJECTED,
        lambda: secure.read_secure_release_file(link, allowed_root=tmp_path),
    )


def test_source_hardlink_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source-real.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    link = tmp_path / "source.py"
    os.link(source, link)
    assert_code(
        secure.RELEASE_FILE_HARDLINK_REJECTED,
        lambda: secure.read_secure_release_file(link, allowed_root=tmp_path),
    )


def test_parent_symlink_is_rejected(tmp_path: Path) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    (real_parent / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    assert_code(
        secure.RELEASE_FILE_SYMLINK_REJECTED,
        lambda: secure.read_secure_release_file(
            linked_parent / "source.py", allowed_root=tmp_path
        ),
    )


def test_source_directory_and_fifo_are_rejected_without_blocking(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "directory.py"
    directory.mkdir()
    fifo = tmp_path / "fifo.py"
    os.mkfifo(fifo)
    for path in (directory, fifo):
        assert_code(
            secure.RELEASE_FILE_NOT_REGULAR,
            lambda path=path: secure.read_secure_release_file(
                path, allowed_root=tmp_path
            ),
        )


def test_source_socket_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.sock"
    server = socket.socket(socket.AF_UNIX)
    try:
        server.bind(str(path))
        assert_code(
            secure.RELEASE_FILE_NOT_REGULAR,
            lambda: secure.read_secure_release_file(path, allowed_root=tmp_path),
        )
    finally:
        server.close()


def test_truncate_during_digest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.bin"
    path.write_bytes(b"A" * 100)

    def observer(event: str, observed: Path, _fd: int, _count: int) -> None:
        if event == "after_chunk":
            os.truncate(observed, 10)

    assert_code(
        secure.RELEASE_FILE_CHANGED_DURING_READ,
        lambda: secure.read_secure_release_file(
            path, allowed_root=tmp_path, chunk_size=16, observer=observer
        ),
    )


def test_content_change_during_digest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.bin"
    path.write_bytes(b"A" * 100)
    changed = False

    def observer(event: str, observed: Path, _fd: int, _count: int) -> None:
        nonlocal changed
        if event == "after_chunk" and not changed:
            changed = True
            descriptor = os.open(observed, os.O_WRONLY)
            try:
                os.pwrite(descriptor, b"B", 0)
            finally:
                os.close(descriptor)

    assert_code(
        secure.RELEASE_FILE_CHANGED_DURING_READ,
        lambda: secure.read_secure_release_file(
            path, allowed_root=tmp_path, chunk_size=16, observer=observer
        ),
    )


def test_rename_replacement_after_digest_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.bin"
    moved = tmp_path / "source-original.bin"
    path.write_bytes(b"original")

    def observer(event: str, observed: Path, _fd: int, _count: int) -> None:
        if event == "before_path_identity_check":
            observed.rename(moved)
            observed.write_bytes(b"replacement")

    assert_code(
        secure.RELEASE_FILE_CHANGED_DURING_READ,
        lambda: secure.read_secure_release_file(
            path, allowed_root=tmp_path, observer=observer
        ),
    )


def test_lstat_to_open_symlink_replacement_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.bin"
    target = tmp_path / "target.bin"
    path.write_bytes(b"original")
    target.write_bytes(b"target")
    real_open = secure.os.open
    replaced = False

    def racing_open(name: object, flags: int, *args: object) -> int:
        nonlocal replaced
        if Path(name) == path and not replaced:
            replaced = True
            path.unlink()
            path.symlink_to(target)
        return real_open(name, flags, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(secure.os, "open", racing_open)
    assert_code(
        secure.RELEASE_FILE_SYMLINK_REJECTED,
        lambda: secure.read_secure_release_file(path, allowed_root=tmp_path),
    )


def test_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.bin"
    path.write_bytes(b"source")
    assert_code(
        secure.RELEASE_FILE_SHA_MISMATCH,
        lambda: secure.read_secure_release_file(
            path, allowed_root=tmp_path, expected_sha256="0" * 64
        ),
    )


def test_candidate_contract_is_rejected_as_production() -> None:
    with pytest.raises(
        SystemExit, match="CANDIDATE_MANIFEST_NOT_VALID_AS_PRODUCTION_RELEASE"
    ):
        validate_production_manifest_contract(
            {
                "schema_version": "slack_worker_release_manifest_candidate_v1",
                "release_status": "CANDIDATE_NOT_APPROVED",
                "candidate_id": "CANDIDATE-NOT-APPROVED",
            }
        )


def test_production_manifest_known_path_is_enforced(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    wrong = config / "candidate-manifest.json"
    wrong.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=secure.RELEASE_FILE_PATH_INVALID):
        load_production_manifest(tmp_path, wrong)
