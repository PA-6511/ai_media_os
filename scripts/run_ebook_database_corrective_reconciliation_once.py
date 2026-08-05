#!/usr/bin/env python3
"""Fail-closed one-shot reconciliation for the ebook production database.

The CLI is dry-run by default.  Production mutation requires an explicit
``--execute`` flag plus a SHA-bound approval document.  This module is
stdlib-only on purpose and never imports the project's database engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
from typing import Any, Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.access_guard import (  # noqa: E402
    ProductionDatabaseAccessBlocked,
    assert_database_target_allowed,
)


PRODUCTION_SOURCE_SHA256 = (
    "1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"
)
TEST_COMIC_ID = "8b1d6d10-af13-4527-8819-fc456f23b908"
SAMPLE_ID = "35e20030-c858-4468-94c4-adaf7bbf3c4b"
NOA_ID = "3e4158c3-1c19-5a07-a5ed-5234a9446db9"
MEDALIST_ID = "e2029b2f-f44a-462f-abc8-86c4bc74b818"
SAMPLE_APPROVAL_ID = "6cd3e433-10eb-4a3f-95fc-44b1ff72fa94"
NOA_AMAZON_OFFER_ID = "edf53455-f520-45b6-85bb-b7d41e10fdd0"
DENIED_HISTORY_IDS = (
    "7acc5009-ce9c-49a2-b732-a5e24d86c467",
    "2ea58c32-e109-4f04-95cb-26d35aa165d2",
)
AFFILIATE_SETTINGS_DDL = """CREATE TABLE affiliate_account_settings (
    service_name TEXT PRIMARY KEY,
    affiliate_id TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
)"""


class ReconciliationBlocked(RuntimeError):
    """Raised whenever a fail-closed gate does not pass."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plan(
    source_database_sha256: str = PRODUCTION_SOURCE_SHA256,
) -> dict[str, Any]:
    return {
        "schema_version": "ebook_database_corrective_reconciliation_plan_v1",
        "source_database_sha256": source_database_sha256,
        "confirmed_difference_count_preserved": 22,
        "denied_difference_count_removed": 9,
        "test_comic": {
            "ebook_item_id": TEST_COMIC_ID,
            "required_before": {
                "title": "テストコミック 第1巻",
                "workflow_status": "READY",
                "review_status": "NOT_REVIEWED",
                "last_checked_at": "2026-07-21 13:55:14.421230",
                "updated_at": "2026-07-21 13:55:14.422216",
            },
            "required_after": {
                "workflow_status": "NEW",
                "review_status": "NOT_REVIEWED",
                "last_checked_at": None,
                "updated_at": "2026-07-13 12:01:28.804963",
            },
        },
        "delete_workflow_history": [
            {
                "id": DENIED_HISTORY_IDS[0],
                "ebook_item_id": TEST_COMIC_ID,
                "field_name": "workflow_status",
                "before_value": "NEW",
                "after_value": "REVIEW",
                "changed_by": "human:local_gui",
                "note": "Workflow status updated from local database GUI",
                "changed_at": "2026-07-21 13:40:19.527089",
            },
            {
                "id": DENIED_HISTORY_IDS[1],
                "ebook_item_id": TEST_COMIC_ID,
                "field_name": "workflow_status",
                "before_value": "REVIEW",
                "after_value": "READY",
                "changed_by": "human:local_gui",
                "note": "Workflow status updated from local database GUI",
                "changed_at": "2026-07-21 13:55:14.422837",
            },
        ],
        "drop_table": {
            "name": "affiliate_account_settings",
            "required_ddl": AFFILIATE_SETTINGS_DDL,
            "required_rows": [
                {"service_name": "amazon", "affiliate_id": None, "enabled": 0},
                {"service_name": "dmm", "affiliate_id": None, "enabled": 0},
                {
                    "service_name": "rakuten_kobo",
                    "affiliate_id": None,
                    "enabled": 0,
                },
            ],
        },
        "required_after_counts": {
            "ebook_items": 4,
            "store_offers": 6,
            "workflow_history": 15,
            "workflow_approval_requests": 2,
        },
        "production_database_exchange": False,
        "old_baseline_restore": False,
    }


def plan_sha256(plan: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(plan))


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def normalize_sqlite_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"blob_hex": value.hex()}
    return value


def rows_sha256(
    connection: sqlite3.Connection,
    query: str,
    parameters: Iterable[Any] = (),
) -> str:
    cursor = connection.execute(query, tuple(parameters))
    columns = [entry[0] for entry in cursor.description or ()]
    rows = [
        [normalize_sqlite_value(value) for value in row]
        for row in cursor.fetchall()
    ]
    return sha256_bytes(canonical_json_bytes({"columns": columns, "rows": rows}))


def user_tables(connection: sqlite3.Connection) -> list[str]:
    return [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def table_sha256(connection: sqlite3.Connection, table_name: str) -> str:
    info = connection.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    primary_key_columns = [
        str(row[1])
        for row in sorted(info, key=lambda row: int(row[5]))
        if int(row[5]) > 0
    ]
    order = primary_key_columns or [str(row[1]) for row in info]
    order_sql = ", ".join(quote_identifier(column) for column in order)
    return rows_sha256(
        connection,
        f"SELECT * FROM {quote_identifier(table_name)} ORDER BY {order_sql}",
    )


def logical_manifest(connection: sqlite3.Connection) -> dict[str, Any]:
    tables = user_tables(connection)
    schema_rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    return {
        "schema_sha256": sha256_bytes(
            canonical_json_bytes(
                [[normalize_sqlite_value(value) for value in row] for row in schema_rows]
            )
        ),
        "tables": {name: table_sha256(connection, name) for name in tables},
    }


def schema_except_table_sha256(
    connection: sqlite3.Connection,
    excluded_table: str,
) -> str:
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' AND tbl_name <> ? "
        "ORDER BY type, name",
        (excluded_table,),
    ).fetchall()
    return sha256_bytes(
        canonical_json_bytes(
            [[normalize_sqlite_value(value) for value in row] for row in rows]
        )
    )


def preserved_subset_hashes(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        "ebook_items_except_test_comic": rows_sha256(
            connection,
            "SELECT * FROM ebook_items WHERE id <> ? ORDER BY id",
            (TEST_COMIC_ID,),
        ),
        "workflow_history_except_denied": rows_sha256(
            connection,
            "SELECT * FROM workflow_history WHERE id NOT IN (?, ?) ORDER BY id",
            DENIED_HISTORY_IDS,
        ),
        "store_offers": table_sha256(connection, "store_offers"),
        "workflow_approval_requests": table_sha256(
            connection, "workflow_approval_requests"
        ),
        "alembic_version": table_sha256(connection, "alembic_version"),
    }


def fetch_one_dict(
    connection: sqlite3.Connection,
    query: str,
    parameters: Iterable[Any] = (),
) -> dict[str, Any] | None:
    cursor = connection.execute(query, tuple(parameters))
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [entry[0] for entry in cursor.description or ()]
    return dict(zip(columns, row))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconciliationBlocked(message)


def validate_preconditions(
    connection: sqlite3.Connection,
    plan: dict[str, Any],
) -> dict[str, Any]:
    before = plan["test_comic"]["required_before"]
    item = fetch_one_dict(
        connection,
        "SELECT * FROM ebook_items WHERE id = ?",
        (TEST_COMIC_ID,),
    )
    require(item is not None, "test comic row is missing")
    for field, expected in before.items():
        require(item.get(field) == expected, f"test comic precondition mismatch: {field}")

    for expected in plan["delete_workflow_history"]:
        history = fetch_one_dict(
            connection,
            "SELECT * FROM workflow_history WHERE id = ?",
            (expected["id"],),
        )
        require(history is not None, f"denied history is missing: {expected['id']}")
        for field, value in expected.items():
            require(
                history.get(field) == value,
                f"history precondition mismatch: {expected['id']}:{field}",
            )

    schema = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        ("affiliate_account_settings",),
    ).fetchone()
    require(schema is not None, "affiliate settings table is missing")
    require(schema[0] == AFFILIATE_SETTINGS_DDL, "affiliate settings DDL mismatch")
    affiliate_rows = [
        tuple(row)
        for row in connection.execute(
            "SELECT service_name, affiliate_id, enabled "
            "FROM affiliate_account_settings ORDER BY service_name"
        ).fetchall()
    ]
    required_rows = [
        (entry["service_name"], entry["affiliate_id"], entry["enabled"])
        for entry in plan["drop_table"]["required_rows"]
    ]
    require(affiliate_rows == required_rows, "affiliate settings rows mismatch")

    counts = {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in (
            "ebook_items",
            "store_offers",
            "workflow_history",
            "workflow_approval_requests",
        )
    }
    require(counts == {
        "ebook_items": 4,
        "store_offers": 6,
        "workflow_history": 17,
        "workflow_approval_requests": 2,
    }, "source table counts mismatch")
    version = [
        tuple(row)
        for row in connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
    ]
    require(version == [("29962ac6d9a5",)], "alembic_version mismatch")

    sample = fetch_one_dict(connection, "SELECT * FROM ebook_items WHERE id=?", (SAMPLE_ID,))
    require(
        sample is not None
        and sample.get("workflow_status") == "READY"
        and sample.get("review_status") == "APPROVED",
        "sample approval state mismatch",
    )
    sample_approval = fetch_one_dict(
        connection,
        "SELECT * FROM workflow_approval_requests WHERE id=?",
        (SAMPLE_APPROVAL_ID,),
    )
    require(
        sample_approval is not None
        and sample_approval.get("ebook_item_id") == SAMPLE_ID
        and sample_approval.get("status") == "APPROVED",
        "sample approval request mismatch",
    )
    noa = fetch_one_dict(connection, "SELECT * FROM ebook_items WHERE id=?", (NOA_ID,))
    require(noa is not None and noa.get("workflow_status") == "PUBLISHED", "Noa state mismatch")
    noa_offer = fetch_one_dict(
        connection,
        "SELECT * FROM store_offers WHERE id=?",
        (NOA_AMAZON_OFFER_ID,),
    )
    require(
        noa_offer is not None
        and noa_offer.get("ebook_item_id") == NOA_ID
        and noa_offer.get("store_item_id") == "B0H3N85PC4"
        and "tag=ktkr77-22" in str(noa_offer.get("affiliate_url") or ""),
        "Noa Amazon offer mismatch",
    )
    medalist = fetch_one_dict(
        connection, "SELECT * FROM ebook_items WHERE id=?", (MEDALIST_ID,)
    )
    require(
        medalist is not None and medalist.get("workflow_status") == "PUBLISHED",
        "Medalist state mismatch",
    )
    return {"counts": counts, "preserved_subset_hashes": preserved_subset_hashes(connection)}


def validate_postconditions(
    connection: sqlite3.Connection,
    plan: dict[str, Any],
    before_subset_hashes: dict[str, str],
) -> dict[str, Any]:
    item = fetch_one_dict(
        connection, "SELECT * FROM ebook_items WHERE id=?", (TEST_COMIC_ID,)
    )
    require(item is not None, "test comic missing after reconciliation")
    for field, expected in plan["test_comic"]["required_after"].items():
        require(item.get(field) == expected, f"test comic postcondition mismatch: {field}")

    remaining = connection.execute(
        "SELECT COUNT(*) FROM workflow_history WHERE id IN (?, ?)",
        DENIED_HISTORY_IDS,
    ).fetchone()[0]
    require(remaining == 0, "denied workflow history remains")
    affiliate_exists = connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        ("affiliate_account_settings",),
    ).fetchone()[0]
    require(affiliate_exists == 0, "affiliate settings table remains")

    counts = {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in plan["required_after_counts"]
    }
    require(counts == plan["required_after_counts"], "post-reconciliation counts mismatch")
    after_subset_hashes = preserved_subset_hashes(connection)
    require(
        after_subset_hashes == before_subset_hashes,
        "a preserved logical row set changed",
    )
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    require(integrity == "ok", "integrity_check failed")
    require(quick == "ok", "quick_check failed")
    lv999 = connection.execute(
        "SELECT COUNT(*) FROM ebook_items "
        "WHERE upper(COALESCE(title, '')) LIKE '%LV999%'"
    ).fetchone()[0]
    require(lv999 == 0, "LV999 row found")
    return {
        "counts": counts,
        "integrity_check": integrity,
        "quick_check": quick,
        "lv999_count": int(lv999),
        "preserved_subset_hashes": after_subset_hashes,
    }


def sidecar_state(database_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for suffix in ("-wal", "-shm", "-journal"):
        path = Path(str(database_path) + suffix)
        result[suffix] = {
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else 0,
        }
    return result


def validate_sidecars(database_path: Path) -> dict[str, Any]:
    state = sidecar_state(database_path)
    require(state["-wal"]["size"] == 0, "non-empty WAL requires separate reconciliation")
    require(
        state["-journal"]["size"] == 0,
        "non-empty rollback journal requires separate reconciliation",
    )
    return state


def port_is_listening(port: int = 8765) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(0.15)
        return client.connect_ex(("127.0.0.1", port)) == 0


def gui_process_is_running(repo_root: Path) -> bool:
    pid_file = repo_root / "run" / "new_release_gui.pid"
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if pid > 0 and Path(f"/proc/{pid}").exists():
                return True
        except (OSError, ValueError):
            return True
    proc = Path("/proc")
    if proc.is_dir():
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                command = (entry / "cmdline").read_bytes().replace(b"\x00", b" ")
            except (OSError, PermissionError):
                continue
            if b"new_release_multistore_app.py" in command:
                return True
    return False


def default_gui_probe(repo_root: Path) -> bool:
    return port_is_listening(8765) or gui_process_is_running(repo_root)


def load_approval(
    approval_path: Path,
    database_path: Path,
    database_sha256: str,
    expected_plan_sha256: str,
) -> tuple[dict[str, Any], str]:
    require(approval_path.is_file(), "approval file is required")
    raw = approval_path.read_bytes()
    try:
        approval = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReconciliationBlocked("approval file is not valid JSON") from exc
    require(isinstance(approval, dict), "approval must be a JSON object")
    required = {
        "schema_version": "ebook_database_corrective_reconciliation_approval_v1",
        "decision": "APPROVE_PRODUCTION_EXECUTION",
        "production_execution_approved": True,
        "database_path": str(database_path.resolve()),
        "database_sha256": database_sha256,
        "corrective_plan_sha256": expected_plan_sha256,
    }
    for field, expected in required.items():
        require(approval.get(field) == expected, f"approval binding mismatch: {field}")
    for field in ("approval_id", "approved_by", "approved_at", "single_use_nonce"):
        require(bool(str(approval.get(field) or "").strip()), f"approval field missing: {field}")
    return approval, sha256_bytes(raw)


def copy_backup(database_path: Path, backup_directory: Path, source_sha: str) -> Path:
    backup_directory.mkdir(parents=True, exist_ok=True)
    backup_path = backup_directory / f"{database_path.name}.pre_reconciliation.{source_sha}.db"
    require(not backup_path.exists(), "pre-execution backup already exists")
    shutil.copy2(database_path, backup_path)
    require(sha256_file(backup_path) == source_sha, "backup SHA mismatch")
    for suffix in ("-wal", "-shm"):
        source_sidecar = Path(str(database_path) + suffix)
        if source_sidecar.exists():
            shutil.copy2(source_sidecar, Path(str(backup_path) + suffix))
    return backup_path


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    require(not path.exists(), "evidence output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    require(not temporary.exists(), "temporary evidence path already exists")
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def open_read_only(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{database_path.resolve()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def apply_reconciliation(
    connection: sqlite3.Connection,
    plan: dict[str, Any],
) -> None:
    cursor = connection.execute(
        "UPDATE ebook_items SET workflow_status=?, last_checked_at=NULL, updated_at=? "
        "WHERE id=? AND title=? AND workflow_status=? AND review_status=? "
        "AND last_checked_at=? AND updated_at=?",
        (
            "NEW",
            "2026-07-13 12:01:28.804963",
            TEST_COMIC_ID,
            "テストコミック 第1巻",
            "READY",
            "NOT_REVIEWED",
            "2026-07-21 13:55:14.421230",
            "2026-07-21 13:55:14.422216",
        ),
    )
    require(cursor.rowcount == 1, "test comic update did not affect exactly one row")
    deleted = 0
    for expected in plan["delete_workflow_history"]:
        cursor = connection.execute(
            "DELETE FROM workflow_history WHERE id=? AND ebook_item_id=? "
            "AND field_name=? AND before_value=? AND after_value=? "
            "AND changed_by=? AND note=? AND changed_at=?",
            tuple(expected[field] for field in (
                "id", "ebook_item_id", "field_name", "before_value",
                "after_value", "changed_by", "note", "changed_at",
            )),
        )
        require(cursor.rowcount == 1, f"history delete mismatch: {expected['id']}")
        deleted += cursor.rowcount
    require(deleted == 2, "history delete count mismatch")
    connection.execute("DROP TABLE affiliate_account_settings")


def run_reconciliation(
    *,
    database_path: Path,
    repo_root: Path,
    execute: bool,
    approval_path: Path | None = None,
    backup_directory: Path | None = None,
    evidence_output: Path | None = None,
    plan: dict[str, Any] | None = None,
    gui_probe: Callable[[Path], bool] = default_gui_probe,
) -> dict[str, Any]:
    try:
        assert_database_target_allowed(
            database_path,
            operation="corrective reconciliation runner",
        )
    except ProductionDatabaseAccessBlocked as exc:
        raise ReconciliationBlocked(str(exc)) from exc
    database_path = database_path.resolve()
    plan = plan or build_plan()
    expected_plan_sha = plan_sha256(plan)
    require(database_path.is_file(), "database path is not a regular file")
    sidecars_before = validate_sidecars(database_path)
    source_sha = sha256_file(database_path)
    require(
        source_sha == plan["source_database_sha256"],
        "database SHA does not match the corrective plan",
    )

    with open_read_only(database_path) as read_connection:
        preconditions = validate_preconditions(read_connection, plan)
        before_manifest = logical_manifest(read_connection)
        preserved_schema_sha = schema_except_table_sha256(
            read_connection,
            "affiliate_account_settings",
        )

    if not execute:
        return {
            "result": "PASS",
            "mode": "DRY_RUN",
            "ready_for_separate_approval": True,
            "database_path": str(database_path),
            "database_sha256": source_sha,
            "corrective_plan_sha256": expected_plan_sha,
            "preconditions": preconditions,
            "sidecars": sidecars_before,
            "production_execution_performed": False,
        }

    require(approval_path is not None, "--execute requires --approval-file")
    require(backup_directory is not None, "--execute requires --backup-directory")
    require(evidence_output is not None, "--execute requires --evidence-output")
    require(not evidence_output.exists(), "evidence output already exists")
    require(not gui_probe(repo_root), "GUI process or port 8765 is active")
    approval, approval_sha = load_approval(
        approval_path.resolve(), database_path, source_sha, expected_plan_sha
    )
    validate_sidecars(database_path)
    backup_path = copy_backup(database_path, backup_directory.resolve(), source_sha)

    connection = sqlite3.connect(str(database_path), isolation_level=None, timeout=0)
    connection.row_factory = sqlite3.Row
    committed = False
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        require(sha256_file(database_path) == source_sha, "database changed before transaction")
        inside = validate_preconditions(connection, plan)
        require(
            inside["preserved_subset_hashes"] == preconditions["preserved_subset_hashes"],
            "logical source changed before transaction",
        )
        apply_reconciliation(connection, plan)
        validate_postconditions(
            connection,
            plan,
            preconditions["preserved_subset_hashes"],
        )
        connection.execute("COMMIT")
        committed = True
    except Exception:
        if not committed and connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()

    sidecars_after = sidecar_state(database_path)
    require(sidecars_after["-wal"]["size"] == 0, "post-commit WAL is not empty")
    reconciled_sha = sha256_file(database_path)
    require(reconciled_sha != source_sha, "database file SHA did not change")
    with open_read_only(database_path) as read_connection:
        postconditions = validate_postconditions(
            read_connection,
            plan,
            preconditions["preserved_subset_hashes"],
        )
        after_manifest = logical_manifest(read_connection)

    for table in before_manifest["tables"]:
        if table in {
            "affiliate_account_settings",
            "ebook_items",
            "workflow_history",
        }:
            continue
        require(
            before_manifest["tables"][table] == after_manifest["tables"][table],
            f"preserved table changed: {table}",
        )
    require(
        "affiliate_account_settings" not in after_manifest["tables"],
        "affiliate settings table remains in logical manifest",
    )
    require(
        after_manifest["schema_sha256"] == preserved_schema_sha,
        "a non-affiliate schema definition changed",
    )
    evidence = {
        "schema_version": "ebook_database_corrective_reconciliation_evidence_v1",
        "result": "PASS",
        "mode": "EXECUTED_APPROVED_ONE_SHOT",
        "database_path": str(database_path),
        "database_sha256_before": source_sha,
        "database_sha256_after": reconciled_sha,
        "corrective_plan_sha256": expected_plan_sha,
        "approval_file": str(approval_path.resolve()),
        "approval_file_sha256": approval_sha,
        "approval_id": approval["approval_id"],
        "backup_path": str(backup_path),
        "backup_sha256": sha256_file(backup_path),
        "before_manifest": before_manifest,
        "after_manifest": after_manifest,
        "preserved_schema_sha256": preserved_schema_sha,
        "postconditions": postconditions,
        "sidecars_before": sidecars_before,
        "sidecars_after": sidecars_after,
        "production_database_exchange_performed": False,
        "old_baseline_restore_performed": False,
    }
    atomic_write_json(evidence_output.resolve(), evidence)
    return evidence


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-file", type=Path)
    parser.add_argument("--backup-directory", type=Path)
    parser.add_argument("--evidence-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_reconciliation(
            database_path=args.database,
            repo_root=args.repo_root.resolve(),
            execute=bool(args.execute),
            approval_path=args.approval_file,
            backup_directory=args.backup_directory,
            evidence_output=args.evidence_output,
        )
    except ReconciliationBlocked as exc:
        print(json.dumps({
            "result": "BLOCKED",
            "reason": str(exc),
            "production_execution_performed": False,
        }, ensure_ascii=False, sort_keys=True))
        return 2
    except Exception as exc:
        print(json.dumps({
            "result": "FAIL",
            "reason": f"{type(exc).__name__}: {exc}",
            "production_execution_performed": False,
        }, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
