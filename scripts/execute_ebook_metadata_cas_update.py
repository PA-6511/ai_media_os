#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Callable, Mapping

from sqlalchemy import create_engine


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.services.ebook_metadata_cas_update_service import (
    EbookMetadataCasUpdateRequest,
    EbookMetadataCasUpdateResult,
    EbookMetadataCasUpdateService,
)


EXACT_APPROVAL_PHRASE = "EXECUTE_PHASE7_RAKUTEN_METADATA_UPDATE_V2"
ALLOWED_UPDATE_FIELDS = ["author_name", "publisher_name"]
LOCK_FILENAME = "ONE_SHOT_UPDATE_LOCK"
AUDIT_FILENAMES = (
    "execution_manifest.json",
    "before_snapshot.json",
    "after_snapshot.json",
    "immutable_comparison.json",
    "database_update_report.json",
)


class ExecutionGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryState:
    head: str
    branch: str
    staging_empty: bool


@dataclass(frozen=True)
class ValidatedAuthorization:
    packet: Mapping[str, object]
    packet_path: Path
    packet_sha256: str
    database_path: Path
    repository_root: Path
    request: EbookMetadataCasUpdateRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute one authorized two-field ebook metadata CAS update."
    )
    parser.add_argument("--authorization-packet", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--approval-phrase", required=True)
    parser.add_argument("--ebook-item-id", required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--recovery-directory", type=Path, required=True)
    return parser


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_repository_state(repository_root: Path) -> RepositoryState:
    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    return RepositoryState(
        head=git("rev-parse", "HEAD"),
        branch=git("branch", "--show-current"),
        staging_empty=git("diff", "--cached", "--name-status") == "",
    )


def validate_execution_gate(
    *,
    packet_path: Path,
    expected_packet_sha256: str,
    approval_phrase: str,
    ebook_item_id: str,
    database_path: Path,
    repository_state: RepositoryState | None = None,
) -> ValidatedAuthorization:
    packet_path = packet_path.resolve(strict=True)
    actual_packet_sha256 = sha256_file(packet_path)
    if actual_packet_sha256 != expected_packet_sha256:
        raise ExecutionGateError("AUTHORIZATION_SHA256_MISMATCH")
    if approval_phrase != EXACT_APPROVAL_PHRASE:
        raise ExecutionGateError("APPROVAL_PHRASE_MISMATCH")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if (
        packet.get("approval_status") != "AWAITING_HUMAN_APPROVAL"
        or packet.get("state") != "AWAITING_HUMAN_APPROVAL"
        or packet.get("execution_gate") != "BLOCKED"
        or packet.get("hold_state") != "HOLD_NO_DATABASE_UPDATE"
    ):
        raise ExecutionGateError("AUTHORIZATION_STATE_MISMATCH")
    approval = _mapping(packet, "approval_contract")
    if approval.get("required_exact_phrase") != EXACT_APPROVAL_PHRASE:
        raise ExecutionGateError("PACKET_APPROVAL_PHRASE_MISMATCH")
    if approval.get("authorization_reuse_allowed") is not False:
        raise ExecutionGateError("AUTHORIZATION_REUSE_NOT_DISABLED")
    support = _mapping(packet, "update_execution_support")
    if support.get("status") != "SUPPORTED":
        raise ExecutionGateError("UPDATE_EXECUTION_NOT_SUPPORTED")
    if packet.get("allowed_update_fields") != ALLOWED_UPDATE_FIELDS:
        raise ExecutionGateError("ALLOWED_UPDATE_FIELDS_MISMATCH")

    repository = _mapping(packet, "repository_binding")
    repository_root = Path(str(repository.get("repository_root", ""))).resolve(
        strict=True
    )
    current = repository_state or load_repository_state(repository_root)
    if (
        current.head != repository.get("git_commit")
        or current.branch != repository.get("repository_branch")
        or not current.staging_empty
    ):
        raise ExecutionGateError("REPOSITORY_BINDING_MISMATCH")
    _validate_implementation_bindings(
        repository_root,
        support.get("implementation_bindings"),
    )

    target = _mapping(packet, "target")
    if target.get("ebook_item_id") != ebook_item_id:
        raise ExecutionGateError("TARGET_EBOOK_ITEM_ID_MISMATCH")
    database = _mapping(packet, "database_binding")
    bound_database_path = Path(str(database.get("path", ""))).resolve(strict=True)
    if bound_database_path != database_path.resolve(strict=True):
        raise ExecutionGateError("DATABASE_PATH_MISMATCH")
    if sha256_file(bound_database_path) != database.get("sha256_at_authorization"):
        raise ExecutionGateError("DATABASE_SHA256_MISMATCH")

    compare_and_set = _mapping(packet, "compare_and_set")
    author = _mapping(compare_and_set, "author_name")
    publisher = _mapping(compare_and_set, "publisher_name")
    request = EbookMetadataCasUpdateRequest.from_mapping(
        {
            "ebook_item_id": ebook_item_id,
            "expected_author_name": author.get("expected_before"),
            "approved_author_name": author.get("approved_after"),
            "expected_publisher_name": publisher.get("expected_before"),
            "approved_publisher_name": publisher.get("approved_after"),
        }
    )
    lock_path = packet_path.parent / LOCK_FILENAME
    if lock_path.exists():
        raise ExecutionGateError("UPDATE_LOCK_ALREADY_EXISTS")
    return ValidatedAuthorization(
        packet=packet,
        packet_path=packet_path,
        packet_sha256=actual_packet_sha256,
        database_path=bound_database_path,
        repository_root=repository_root,
        request=request,
    )


def _validate_implementation_bindings(
    repository_root: Path,
    value: object,
) -> None:
    if not isinstance(value, list) or not value:
        raise ExecutionGateError("IMPLEMENTATION_BINDINGS_REQUIRED")
    for row in value:
        if not isinstance(row, dict):
            raise ExecutionGateError("IMPLEMENTATION_BINDING_INVALID")
        path = repository_root / str(row.get("path", ""))
        if (
            not path.is_file()
            or sha256_file(path) != row.get("sha256")
        ):
            raise ExecutionGateError("IMPLEMENTATION_BINDING_MISMATCH")


def create_one_shot_update_lock(
    authorization: ValidatedAuthorization,
    recovery_directory: Path,
) -> Path:
    path = authorization.packet_path.parent / LOCK_FILENAME
    body = (
        json.dumps(
            {
                "authorization_used": True,
                "authorization_packet_sha256": authorization.packet_sha256,
                "ebook_item_id": authorization.request.ebook_item_id,
                "locked_at_utc": datetime.now(timezone.utc).isoformat(),
                "recovery_directory": str(recovery_directory),
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    try:
        _write_new_private(path, body)
    except FileExistsError as exc:
        raise ExecutionGateError("UPDATE_LOCK_ALREADY_EXISTS") from exc
    return path


def create_sqlite_backup(source_path: Path, destination_path: Path) -> str:
    if destination_path.exists():
        raise ExecutionGateError("BACKUP_DESTINATION_ALREADY_EXISTS")
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ExecutionGateError("BACKUP_INTEGRITY_CHECK_FAILED")
    finally:
        destination.close()
        source.close()
    os.chmod(destination_path, 0o600)
    return sha256_file(destination_path)


def write_audit_evidence(
    *,
    directory: Path,
    authorization: ValidatedAuthorization,
    result: EbookMetadataCasUpdateResult,
    database_sha256_before: str,
    database_sha256_after: str,
    backup_sha256: str,
) -> tuple[Path, ...]:
    values = result.audit_values()
    documents = {
        "execution_manifest.json": {
            "ebook_item_id": result.ebook_item_id,
            "authorization_packet_sha256": authorization.packet_sha256,
            "repository_binding": dict(
                _mapping(authorization.packet, "repository_binding")
            ),
            "database_path": str(authorization.database_path),
            "audit_files": list(AUDIT_FILENAMES),
            "external_http_calls": 0,
            "wordpress_updated": False,
            "automatic_retry": False,
        },
        "before_snapshot.json": {
            "ebook_item_id": result.ebook_item_id,
            **values["before"],
        },
        "after_snapshot.json": {
            "ebook_item_id": result.ebook_item_id,
            **values["after"],
        },
        "immutable_comparison.json": {
            "ebook_item_id": result.ebook_item_id,
            "before": values["immutable_before"],
            "after": values["immutable_after"],
            "unchanged": result.immutable_fields_unchanged,
            "store_offers_sha256_before": result.store_offers_sha256_before,
            "store_offers_sha256_after": result.store_offers_sha256_after,
            "store_offers_unchanged": result.store_offers_unchanged,
        },
        "database_update_report.json": {
            "ebook_item_id": result.ebook_item_id,
            "database_sha256_before": database_sha256_before,
            "database_sha256_after": database_sha256_after,
            "backup_sha256": backup_sha256,
            "matched_row_count": result.matched_row_count,
            "updated_row_count": result.updated_row_count,
            "transaction_committed": result.transaction_result == "COMMITTED",
            "rollback_reason": None,
            "external_http_calls": 0,
            "wordpress_updated": False,
        },
    }
    paths: list[Path] = []
    for name, document in documents.items():
        path = directory / name
        _write_new_private(path, _json_bytes(document))
        paths.append(path)
    checksum_lines = [
        f"{sha256_file(path)}  {path.name}" for path in paths
    ]
    checksum_path = directory / "SHA256SUMS"
    _write_new_private(
        checksum_path,
        ("\n".join(checksum_lines) + "\n").encode("utf-8"),
    )
    paths.append(checksum_path)
    return tuple(paths)


def execute_authorized_update(
    authorization: ValidatedAuthorization,
    recovery_directory: Path,
    *,
    backup_creator: Callable[[Path, Path], str] = create_sqlite_backup,
    service_factory: Callable[..., EbookMetadataCasUpdateService] = (
        EbookMetadataCasUpdateService
    ),
) -> EbookMetadataCasUpdateResult:
    recovery_directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    create_one_shot_update_lock(authorization, recovery_directory)
    database_sha256_before = sha256_file(authorization.database_path)
    backup_path = recovery_directory / "ebook_affiliate.pre_update.db"
    backup_sha256 = backup_creator(authorization.database_path, backup_path)
    if sha256_file(authorization.database_path) != database_sha256_before:
        raise ExecutionGateError("DATABASE_CHANGED_AFTER_BACKUP")
    engine = create_engine(f"sqlite:///{authorization.database_path}")
    try:
        result = service_factory(engine).execute(authorization.request)
    finally:
        engine.dispose()
    database_sha256_after = sha256_file(authorization.database_path)
    write_audit_evidence(
        directory=recovery_directory,
        authorization=authorization,
        result=result,
        database_sha256_before=database_sha256_before,
        database_sha256_after=database_sha256_after,
        backup_sha256=backup_sha256,
    )
    return result


def _mapping(value: Mapping[str, object], name: str) -> Mapping[str, object]:
    nested = value.get(name)
    if not isinstance(nested, dict):
        raise ExecutionGateError(f"PACKET_SECTION_INVALID:{name}")
    return nested


def _write_new_private(path: Path, body: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=_json_default,
        )
        + "\n"
    ).encode("utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"unsupported audit value: {type(value).__name__}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        authorization = validate_execution_gate(
            packet_path=args.authorization_packet,
            expected_packet_sha256=args.authorization_sha256,
            approval_phrase=args.approval_phrase,
            ebook_item_id=args.ebook_item_id,
            database_path=args.database,
        )
        result = execute_authorized_update(
            authorization,
            args.recovery_directory,
        )
    except (ExecutionGateError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                "ebook_item_id": result.ebook_item_id,
                "updated_row_count": result.updated_row_count,
                "transaction_result": result.transaction_result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())