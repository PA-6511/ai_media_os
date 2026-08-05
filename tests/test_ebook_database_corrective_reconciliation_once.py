from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from scripts import run_ebook_database_corrective_reconciliation_once as runner


def create_source_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE ebook_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            workflow_status TEXT NOT NULL,
            review_status TEXT NOT NULL,
            last_checked_at TEXT,
            updated_at TEXT NOT NULL,
            preserved_marker TEXT NOT NULL
        );
        CREATE TABLE store_offers (
            id TEXT PRIMARY KEY,
            ebook_item_id TEXT NOT NULL,
            store_name TEXT NOT NULL,
            store_item_id TEXT NOT NULL,
            product_url TEXT,
            affiliate_url TEXT,
            last_checked_at TEXT NOT NULL
        );
        CREATE TABLE workflow_approval_requests (
            id TEXT PRIMARY KEY,
            ebook_item_id TEXT NOT NULL,
            approval_type TEXT NOT NULL,
            status TEXT NOT NULL,
            request_nonce_hash TEXT NOT NULL
        );
        CREATE TABLE workflow_history (
            id TEXT PRIMARY KEY,
            ebook_item_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            before_value TEXT,
            after_value TEXT,
            changed_by TEXT NOT NULL,
            note TEXT,
            changed_at TEXT NOT NULL
        );
        CREATE TABLE alembic_version (
            version_num TEXT PRIMARY KEY
        );
        """
    )
    connection.execute(runner.AFFILIATE_SETTINGS_DDL)
    connection.executemany(
        "INSERT INTO ebook_items VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                runner.TEST_COMIC_ID,
                "テストコミック 第1巻",
                "READY",
                "NOT_REVIEWED",
                "2026-07-21 13:55:14.421230",
                "2026-07-21 13:55:14.422216",
                "test-comic-preserved",
            ),
            (runner.SAMPLE_ID, "サンプル作品", "READY", "APPROVED", "sample-check", "sample-update", "sample-preserved"),
            (runner.NOA_ID, "のあ先輩はともだち。", "PUBLISHED", "NOT_REVIEWED", "noa-check", "noa-update", "noa-preserved"),
            (runner.MEDALIST_ID, "メダリスト", "PUBLISHED", "APPROVED", "medalist-check", "medalist-update", "medalist-preserved"),
        ],
    )
    offers = [
        (
            runner.NOA_AMAZON_OFFER_ID,
            runner.NOA_ID,
            "amazon",
            "B0H3N85PC4",
            "https://www.amazon.co.jp/dp/B0H3N85PC4",
            "https://www.amazon.co.jp/dp/B0H3N85PC4/ref=nosim?tag=ktkr77-22",
            "2026-07-21 14:23:47.427241",
        )
    ]
    offers.extend(
        (
            f"offer-{index}",
            runner.MEDALIST_ID,
            "store",
            f"item-{index}",
            f"https://example.test/{index}",
            None,
            f"2026-07-19 00:00:0{index}",
        )
        for index in range(1, 6)
    )
    connection.executemany("INSERT INTO store_offers VALUES (?, ?, ?, ?, ?, ?, ?)", offers)
    connection.executemany(
        "INSERT INTO workflow_approval_requests VALUES (?, ?, ?, ?, ?)",
        [
            (runner.SAMPLE_APPROVAL_ID, runner.SAMPLE_ID, "REVIEW_READY", "APPROVED", "sample-token-hash"),
            ("baseline-approval", runner.MEDALIST_ID, "REVIEW_READY", "APPROVED", "baseline-token-hash"),
        ],
    )
    history_rows = [
        (
            runner.DENIED_HISTORY_IDS[0],
            runner.TEST_COMIC_ID,
            "workflow_status",
            "NEW",
            "REVIEW",
            "human:local_gui",
            "Workflow status updated from local database GUI",
            "2026-07-21 13:40:19.527089",
        ),
        (
            runner.DENIED_HISTORY_IDS[1],
            runner.TEST_COMIC_ID,
            "workflow_status",
            "REVIEW",
            "READY",
            "human:local_gui",
            "Workflow status updated from local database GUI",
            "2026-07-21 13:55:14.422837",
        ),
    ]
    for prefix, item_id, count in (
        ("sample", runner.SAMPLE_ID, 4),
        ("noa", runner.NOA_ID, 4),
        ("medalist", runner.MEDALIST_ID, 7),
    ):
        for index in range(count):
            history_rows.append(
                (
                    f"{prefix}-history-{index}",
                    item_id,
                    "workflow_status",
                    f"before-{index}",
                    f"after-{index}",
                    "preserved:actor",
                    f"preserved {prefix} {index}",
                    f"2026-07-20 00:00:{index:02d}",
                )
            )
    connection.executemany("INSERT INTO workflow_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)", history_rows)
    connection.execute("INSERT INTO alembic_version VALUES ('29962ac6d9a5')")
    connection.executemany(
        "INSERT INTO affiliate_account_settings VALUES (?, NULL, 0, ?)",
        [
            ("amazon", "2026-07-21 14:42:08"),
            ("dmm", "2026-07-21 14:42:08"),
            ("rakuten_kobo", "2026-07-21 14:42:08"),
        ],
    )
    connection.commit()
    connection.close()


def build_bound_plan(database_path: Path) -> dict[str, object]:
    return runner.build_plan(runner.sha256_file(database_path))


def write_approval(path: Path, database_path: Path, plan: dict[str, object], **overrides: object) -> None:
    payload: dict[str, object] = {
        "schema_version": "ebook_database_corrective_reconciliation_approval_v1",
        "approval_id": "test-approval-id",
        "decision": "APPROVE_PRODUCTION_EXECUTION",
        "production_execution_approved": True,
        "database_path": str(database_path.resolve()),
        "database_sha256": runner.sha256_file(database_path),
        "corrective_plan_sha256": runner.plan_sha256(plan),
        "approved_by": "human:test-reviewer",
        "approved_at": "2026-07-23T00:00:00+09:00",
        "single_use_nonce": "test-single-use-nonce",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def execute_fixture(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan)
    result = runner.run_reconciliation(
        database_path=database,
        repo_root=tmp_path,
        execute=True,
        approval_path=approval,
        backup_directory=tmp_path / "backups",
        evidence_output=tmp_path / "evidence.json",
        plan=plan,
        gui_probe=lambda _root: False,
    )
    return database, result


def scalar(database: Path, query: str, parameters: tuple[object, ...] = ()) -> object:
    with sqlite3.connect(database) as connection:
        return connection.execute(query, parameters).fetchone()[0]


def test_default_mode_is_read_only_dry_run(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    before = runner.sha256_file(database)
    result = runner.run_reconciliation(
        database_path=database,
        repo_root=tmp_path,
        execute=False,
        plan=build_bound_plan(database),
    )
    assert result["mode"] == "DRY_RUN"
    assert result["production_execution_performed"] is False
    assert runner.sha256_file(database) == before


def test_expected_nine_differences_are_reconciled(tmp_path: Path) -> None:
    database, result = execute_fixture(tmp_path)
    assert result["result"] == "PASS"
    assert scalar(database, "SELECT workflow_status FROM ebook_items WHERE id=?", (runner.TEST_COMIC_ID,)) == "NEW"
    assert scalar(database, "SELECT last_checked_at IS NULL FROM ebook_items WHERE id=?", (runner.TEST_COMIC_ID,)) == 1
    assert scalar(database, "SELECT COUNT(*) FROM workflow_history") == 15
    assert scalar(database, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='affiliate_account_settings'") == 0


def test_test_comic_non_target_columns_are_unchanged(tmp_path: Path) -> None:
    database, _ = execute_fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT title, review_status, preserved_marker, updated_at FROM ebook_items WHERE id=?",
            (runner.TEST_COMIC_ID,),
        ).fetchone()
    assert row == (
        "テストコミック 第1巻",
        "NOT_REVIEWED",
        "test-comic-preserved",
        "2026-07-13 12:01:28.804963",
    )


def test_only_two_denied_history_rows_are_removed(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    with sqlite3.connect(database) as connection:
        before_hash = runner.rows_sha256(
            connection,
            "SELECT * FROM workflow_history WHERE id NOT IN (?, ?) ORDER BY id",
            runner.DENIED_HISTORY_IDS,
        )
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan)
    runner.run_reconciliation(
        database_path=database,
        repo_root=tmp_path,
        execute=True,
        approval_path=approval,
        backup_directory=tmp_path / "backups",
        evidence_output=tmp_path / "evidence.json",
        plan=plan,
        gui_probe=lambda _root: False,
    )
    with sqlite3.connect(database) as connection:
        after_hash = runner.rows_sha256(connection, "SELECT * FROM workflow_history ORDER BY id")
    assert after_hash == before_hash


def test_confirmed_rows_and_states_are_preserved(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    with sqlite3.connect(database) as connection:
        before = runner.preserved_subset_hashes(connection)
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan)
    runner.run_reconciliation(
        database_path=database,
        repo_root=tmp_path,
        execute=True,
        approval_path=approval,
        backup_directory=tmp_path / "backups",
        evidence_output=tmp_path / "evidence.json",
        plan=plan,
        gui_probe=lambda _root: False,
    )
    with sqlite3.connect(database) as connection:
        after = runner.preserved_subset_hashes(connection)
    assert after == before
    assert scalar(database, "SELECT status FROM workflow_approval_requests WHERE id=?", (runner.SAMPLE_APPROVAL_ID,)) == "APPROVED"
    assert scalar(database, "SELECT workflow_status FROM ebook_items WHERE id=?", (runner.NOA_ID,)) == "PUBLISHED"
    assert scalar(database, "SELECT workflow_status FROM ebook_items WHERE id=?", (runner.MEDALIST_ID,)) == "PUBLISHED"


def test_noa_amazon_offer_is_preserved(tmp_path: Path) -> None:
    database, _ = execute_fixture(tmp_path)
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT store_item_id, affiliate_url FROM store_offers WHERE id=?",
            (runner.NOA_AMAZON_OFFER_ID,),
        ).fetchone()
    assert row == (
        "B0H3N85PC4",
        "https://www.amazon.co.jp/dp/B0H3N85PC4/ref=nosim?tag=ktkr77-22",
    )


def test_precondition_mismatch_stops_before_any_write(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE ebook_items SET title='unexpected' WHERE id=?", (runner.TEST_COMIC_ID,))
        connection.commit()
    before = runner.sha256_file(database)
    with pytest.raises(runner.ReconciliationBlocked, match="title"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=False,
            plan=runner.build_plan(before),
        )
    assert runner.sha256_file(database) == before


def test_database_sha_mismatch_is_rejected(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    with pytest.raises(runner.ReconciliationBlocked, match="database SHA"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=False,
            plan=runner.build_plan("0" * 64),
        )


def test_execute_without_approval_is_rejected(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    before = runner.sha256_file(database)
    with pytest.raises(runner.ReconciliationBlocked, match="approval-file"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=True,
            backup_directory=tmp_path / "backups",
            evidence_output=tmp_path / "evidence.json",
            plan=build_bound_plan(database),
            gui_probe=lambda _root: False,
        )
    assert runner.sha256_file(database) == before


@pytest.mark.parametrize("field,value", [
    ("database_sha256", "0" * 64),
    ("corrective_plan_sha256", "f" * 64),
])
def test_approval_sha_bindings_are_enforced(tmp_path: Path, field: str, value: str) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan, **{field: value})
    before = runner.sha256_file(database)
    with pytest.raises(runner.ReconciliationBlocked, match="approval binding"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=True,
            approval_path=approval,
            backup_directory=tmp_path / "backups",
            evidence_output=tmp_path / "evidence.json",
            plan=plan,
            gui_probe=lambda _root: False,
        )
    assert runner.sha256_file(database) == before


def test_gui_active_rejects_execution(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan)
    before = runner.sha256_file(database)
    with pytest.raises(runner.ReconciliationBlocked, match="GUI process"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=True,
            approval_path=approval,
            backup_directory=tmp_path / "backups",
            evidence_output=tmp_path / "evidence.json",
            plan=plan,
            gui_probe=lambda _root: True,
        )
    assert runner.sha256_file(database) == before


def test_nonempty_wal_rejects_execution(tmp_path: Path) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    Path(str(database) + "-wal").write_bytes(b"unreconciled")
    with pytest.raises(runner.ReconciliationBlocked, match="non-empty WAL"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=False,
            plan=build_bound_plan(database),
        )


def test_second_execution_is_rejected(tmp_path: Path) -> None:
    database, _ = execute_fixture(tmp_path)
    with pytest.raises(runner.ReconciliationBlocked, match="database SHA"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=False,
            plan=runner.build_plan("0" * 64),
        )


def test_exception_inside_transaction_rolls_back_all_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "fixture.db"
    create_source_database(database)
    plan = build_bound_plan(database)
    approval = tmp_path / "approval.json"
    write_approval(approval, database, plan)
    before = runner.sha256_file(database)

    def fail_after_partial_update(connection: sqlite3.Connection, _plan: dict[str, object]) -> None:
        connection.execute(
            "UPDATE ebook_items SET workflow_status='NEW' WHERE id=?",
            (runner.TEST_COMIC_ID,),
        )
        raise RuntimeError("injected failure")

    monkeypatch.setattr(runner, "apply_reconciliation", fail_after_partial_update)
    with pytest.raises(RuntimeError, match="injected failure"):
        runner.run_reconciliation(
            database_path=database,
            repo_root=tmp_path,
            execute=True,
            approval_path=approval,
            backup_directory=tmp_path / "backups",
            evidence_output=tmp_path / "evidence.json",
            plan=plan,
            gui_probe=lambda _root: False,
        )
    assert runner.sha256_file(database) == before
    assert scalar(database, "SELECT workflow_status FROM ebook_items WHERE id=?", (runner.TEST_COMIC_ID,)) == "READY"
    assert scalar(database, "SELECT COUNT(*) FROM workflow_history") == 17
    assert scalar(database, "SELECT COUNT(*) FROM sqlite_master WHERE name='affiliate_account_settings'") == 1


def test_success_writes_verified_backup_and_atomic_evidence(tmp_path: Path) -> None:
    database, result = execute_fixture(tmp_path)
    evidence = tmp_path / "evidence.json"
    backup = Path(str(result["backup_path"]))
    assert evidence.is_file()
    assert backup.is_file()
    assert result["backup_sha256"] == result["database_sha256_before"]
    assert result["database_sha256_after"] == runner.sha256_file(database)
    assert json.loads(evidence.read_text(encoding="utf-8"))["result"] == "PASS"
