from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from scripts import execute_ebook_metadata_cas_update as command


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            EbookItem.__table__.insert(),
            {
                "id": "target",
                "source_name": "fixture",
                "source_item_id": "source-20",
                "title": "作品 20",
                "workflow_status": "NEW",
                "review_status": "NOT_REVIEWED",
                "publish_ready": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            StoreOffer.__table__.insert(),
            {
                "id": "offer",
                "ebook_item_id": "target",
                "store_name": "rakuten_kobo",
                "store_item_id": "item-20",
                "affiliate_url": "https://secret.invalid/affiliate-value",
                "last_checked_at": now,
            },
        )
    engine.dispose()


def _packet(tmp_path: Path) -> tuple[Path, Path, command.RepositoryState]:
    repository = tmp_path / "repository"
    repository.mkdir()
    implementation = repository / "implementation.py"
    implementation.write_text("SUPPORTED = True\n", encoding="utf-8")
    database = tmp_path / "test.db"
    _database(database)
    packet_directory = tmp_path / "authorization"
    packet_directory.mkdir()
    packet = packet_directory / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "approval_status": "AWAITING_HUMAN_APPROVAL",
                "state": "AWAITING_HUMAN_APPROVAL",
                "execution_gate": "BLOCKED",
                "hold_state": "HOLD_NO_DATABASE_UPDATE",
                "repository_binding": {
                    "repository_root": str(repository),
                    "git_commit": "expected-head",
                    "repository_branch": "expected-branch",
                },
                "database_binding": {
                    "path": str(database),
                    "sha256_at_authorization": _sha256(database),
                },
                "target": {"ebook_item_id": "target"},
                "compare_and_set": {
                    "author_name": {
                        "expected_before": None,
                        "approved_after": "著者",
                    },
                    "publisher_name": {
                        "expected_before": None,
                        "approved_after": "出版社",
                    },
                },
                "allowed_update_fields": ["author_name", "publisher_name"],
                "approval_contract": {
                    "required_exact_phrase": command.EXACT_APPROVAL_PHRASE,
                    "authorization_reuse_allowed": False,
                },
                "update_execution_support": {
                    "status": "SUPPORTED",
                    "implementation_bindings": [
                        {
                            "path": implementation.name,
                            "sha256": _sha256(implementation),
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return (
        packet,
        database,
        command.RepositoryState("expected-head", "expected-branch", True),
    )


def _validate(
    packet: Path,
    database: Path,
    state: command.RepositoryState,
    **overrides,
) -> command.ValidatedAuthorization:
    values = {
        "packet_path": packet,
        "expected_packet_sha256": _sha256(packet),
        "approval_phrase": command.EXACT_APPROVAL_PHRASE,
        "ebook_item_id": "target",
        "database_path": database,
        "repository_state": state,
    }
    values.update(overrides)
    return command.validate_execution_gate(**values)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"expected_packet_sha256": "0" * 64}, "AUTHORIZATION_SHA256_MISMATCH"),
        ({"approval_phrase": "wrong"}, "APPROVAL_PHRASE_MISMATCH"),
    ],
)
def test_packet_sha_or_approval_phrase_mismatch_is_rejected(
    tmp_path, override, message
) -> None:
    packet, database, state = _packet(tmp_path)
    with pytest.raises(command.ExecutionGateError, match=message):
        _validate(packet, database, state, **override)


def test_database_sha_mismatch_is_rejected(tmp_path) -> None:
    packet, database, state = _packet(tmp_path)
    connection = sqlite3.connect(database)
    connection.execute("UPDATE ebook_items SET author_name='changed'")
    connection.commit()
    connection.close()
    with pytest.raises(
        command.ExecutionGateError,
        match="DATABASE_SHA256_MISMATCH",
    ):
        _validate(packet, database, state)


def test_one_shot_lock_rejects_second_creation_and_uses_mode_0600(
    tmp_path,
) -> None:
    packet, database, state = _packet(tmp_path)
    authorization = _validate(packet, database, state)
    recovery = tmp_path / "recovery"
    first = command.create_one_shot_update_lock(authorization, recovery)
    assert first.stat().st_mode & 0o777 == 0o600
    with pytest.raises(
        command.ExecutionGateError,
        match="UPDATE_LOCK_ALREADY_EXISTS",
    ):
        command.create_one_shot_update_lock(authorization, recovery)


def test_backup_failure_happens_before_update(tmp_path) -> None:
    packet, database, state = _packet(tmp_path)
    authorization = _validate(packet, database, state)

    def fail_backup(_source: Path, _destination: Path) -> str:
        raise command.ExecutionGateError("BACKUP_FAILED")

    with pytest.raises(command.ExecutionGateError, match="BACKUP_FAILED"):
        command.execute_authorized_update(
            authorization,
            tmp_path / "failed-recovery",
            backup_creator=fail_backup,
        )
    engine = create_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        row = connection.execute(
            select(EbookItem.author_name, EbookItem.publisher_name)
        ).one()
    engine.dispose()
    assert tuple(row) == (None, None)


def test_full_temp_execution_uses_backup_and_writes_safe_audit(tmp_path) -> None:
    packet, database, state = _packet(tmp_path)
    authorization = _validate(packet, database, state)
    recovery = tmp_path / "successful-recovery"
    result = command.execute_authorized_update(authorization, recovery)
    assert result.updated_row_count == 1
    backup = recovery / "ebook_affiliate.pre_update.db"
    assert backup.is_file()
    connection = sqlite3.connect(backup)
    assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    connection.close()
    expected = set(command.AUDIT_FILENAMES) | {"SHA256SUMS"}
    assert expected <= {path.name for path in recovery.iterdir()}
    for line in (recovery / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert _sha256(recovery / name) == digest
    audit = b"".join(
        (recovery / name).read_bytes() for name in command.AUDIT_FILENAMES
    )
    for forbidden in (
        b"https://secret.invalid/affiliate-value",
        b"applicationId",
        b"accessKey",
        b"affiliateId",
        b"Cookie",
        b"Set-Cookie",
    ):
        assert forbidden not in audit


def test_execution_module_has_no_external_http_client_import() -> None:
    tree = ast.parse(Path(command.__file__).read_text(encoding="utf-8"))
    imported = {
        node.names[0].name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported.update(
        str(node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert imported.isdisjoint({"requests", "urllib", "httpx", "socket"})