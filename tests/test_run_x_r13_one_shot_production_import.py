from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Callable

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from scripts import run_x_r13_one_shot_production_import as runner


GATE_DIGEST_FIELD = (
    "x_r13_production_import_approval_"
    "gate_digest_sha256"
)

APPROVAL_DIGEST_FIELD = (
    "x_r13_production_import_execution_"
    "approval_certificate_digest_sha256"
)


def write_signed_json(
    path: Path,
    payload: dict[str, Any],
    digest_field: str,
) -> dict[str, Any]:
    value = {
        **payload,
        digest_field: runner.canonical_digest(
            payload
        ),
    }

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return value


def base_row() -> dict[str, str]:
    return {
        "source_name": "rakuten_kobo",
        "source_item_id": "4310000887411",
        "title": "メダリスト",
        "normalized_title": "メダリスト",
        "volume_label": "第15巻",
        "author_name": "つるまいかだ",
        "publisher_name": "講談社",
        "release_date": "2026-07-22",
        "item_type": "tankobon",
        "store_name": "rakuten_kobo",
        "store_item_id": "4310000887411",
        "product_url": (
            "https://books.rakuten.co.jp/"
            "rk/a4c432a967ca32a4ae2331dd5c4cd8a8/"
        ),
        "affiliate_url": (
            "https://hb.afl.rakuten.co.jp/"
            "hgc/test/"
        ),
        "price_yen": "",
        "discount_rate": "",
        "point_rate": "",
    }


def build_case(
    tmp_path: Path,
    *,
    row_overrides: dict[str, str] | None = None,
    permission_overrides: (
        dict[str, bool] | None
    ) = None,
    state_overrides: (
        dict[str, bool] | None
    ) = None,
    seed: Callable[[Any], None] | None = None,
    database_sha_override: str | None = None,
) -> tuple[runner.RunPaths, Any]:
    database_path = tmp_path / "database.sqlite"

    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        future=True,
    )

    Base.metadata.create_all(engine)

    if seed is not None:
        seed(engine)

    gate_path = tmp_path / "gate.json"

    gate_payload = {
        "phase": (
            "X-R13-PRODUCTION-IMPORT-"
            "APPROVAL-GATE-PREP"
        ),
        "status": (
            "READY_X_R13_MEDALIST_15_"
            "PRODUCTION_IMPORT_GATE_BLOCKED_"
            "PENDING_RUNNER_CONTRACT_AUDIT"
        ),
        "gate_state": (
            "BLOCKED_PENDING_"
            "IMPORTER_CONTRACT_AUDIT"
        ),
        "current_state": {
            "gate_open": False,
            "production_import_executed": False,
        },
        "approval_contract": {
            "production_import_approval_"
            "requestable": False,
        },
        "runner_contract_requirements": {
            "manual_raw_sql_runner_allowed": (
                False
            ),
        },
        "production_status": "NO_GO",
    }

    gate = write_signed_json(
        gate_path,
        gate_payload,
        GATE_DIGEST_FIELD,
    )

    gate_digest = gate[GATE_DIGEST_FIELD]

    policy_path = tmp_path / "policy.json"

    policy_payload = {
        "phase": (
            "X-R13-ONE-SHOT-"
            "PRODUCTION-IMPORT-POLICY"
        ),
        "policy_version": "TEST",
        "execution_default": "BLOCKED",
        "candidate": {
            "source_name": "rakuten_kobo",
            "store_name": "rakuten_kobo",
            "store_item_id": "4310000887411",
            "title": "メダリスト",
            "volume_label": "第15巻",
            "item_type": "tankobon",
        },
        "source_binding": {
            "production_import_gate_"
            "digest_sha256": gate_digest,
            "source_interface_digest_sha256": (
                "test-interface-digest"
            ),
        },
        "runtime_contract": {
            "gate_digest_field": (
                GATE_DIGEST_FIELD
            ),
            "required_gate_status": (
                gate_payload["status"]
            ),
            "required_gate_state": (
                gate_payload["gate_state"]
            ),
            "approval_digest_field": (
                APPROVAL_DIGEST_FIELD
            ),
            "required_approval_status": (
                "PASS_X_R13_MEDALIST_15_"
                "PRODUCTION_IMPORT_EXECUTION_"
                "APPROVAL_ISSUED"
            ),
            "required_approval_state": (
                "APPROVED_FOR_X_R13_"
                "MEDALIST_15_PRODUCTION_"
                "IMPORT_EXECUTION_ONLY"
            ),
        },
        "safety": {
            "candidate_count_limit": 1,
            "database_sha_precondition_required": (
                True
            ),
            "nonempty_wal_block_required": True,
            "duplicate_source_item_check_"
            "required": True,
            "duplicate_store_item_check_"
            "required": True,
            "transaction_required": True,
            "rollback_on_failure_required": True,
            "post_write_foreign_key_check_"
            "required": True,
            "post_write_integrity_check_"
            "required": True,
            "automatic_retry_allowed": False,
            "reexecution_allowed": False,
            "approval_reuse_allowed": False,
            "manual_raw_sql_allowed": False,
            "temporary_database_copy_allowed": (
                False
            ),
            "x_r11_runner_reexecution_allowed": (
                False
            ),
            "external_api_call_allowed": False,
            "credential_read_allowed": False,
            "failure_action": "STOP",
        },
        "production_status": "NO_GO",
    }

    write_signed_json(
        policy_path,
        policy_payload,
        "policy_digest_sha256",
    )

    row = base_row()

    if row_overrides:
        row.update(row_overrides)

    permissions = {
        "gate_open_for_this_execution": True,
        "production_import_execution_allowed": (
            True
        ),
        "production_database_write_allowed": True,
        "candidate_binding_allowed": True,
        "candidate_import_allowed": True,
        "single_candidate_only": True,
        "approval_reuse_allowed": False,
        "automatic_retry_allowed": False,
        "x_r11_runner_reexecution_allowed": False,
        "manual_raw_sql_runner_allowed": False,
        "temporary_database_copy_allowed": False,
        "external_api_call_allowed": False,
        "credential_read_allowed": False,
    }

    if permission_overrides:
        permissions.update(
            permission_overrides
        )

    state = {
        "production_import_approval_issued": True,
        "human_approval_consumed": False,
        "production_import_executed": False,
    }

    if state_overrides:
        state.update(state_overrides)

    database_sha = (
        database_sha_override
        if database_sha_override is not None
        else runner.sha256_file(
            database_path
        )
    )

    approval_path = tmp_path / "approval.json"

    approval_payload = {
        "phase": (
            "X-R13-PRODUCTION-IMPORT-"
            "EXECUTION-APPROVAL-ISSUANCE"
        ),
        "status": (
            "PASS_X_R13_MEDALIST_15_"
            "PRODUCTION_IMPORT_EXECUTION_"
            "APPROVAL_ISSUED"
        ),
        "approval_id": "test-approval",
        "approval_state": (
            "APPROVED_FOR_X_R13_MEDALIST_15_"
            "PRODUCTION_IMPORT_EXECUTION_ONLY"
        ),
        "source_binding": {
            "gate_digest_sha256": gate_digest,
            "production_database_sha256": (
                database_sha
            ),
        },
        "permissions": permissions,
        "current_state": state,
        "candidate": {
            "canonical_import_row": row,
        },
        "production_status": "NO_GO",
    }

    write_signed_json(
        approval_path,
        approval_payload,
        APPROVAL_DIGEST_FIELD,
    )

    paths = runner.RunPaths(
        policy=policy_path,
        gate_pack=gate_path,
        approval_certificate=approval_path,
        database=database_path,
        execution_claim=(
            tmp_path / "claim.json"
        ),
        result_pack=(
            tmp_path / "result.json"
        ),
        report=tmp_path / "report.md",
        consumption_lock=(
            tmp_path / "consumption.json"
        ),
    )

    return paths, engine


def database_counts(
    engine: Any,
) -> tuple[int, int]:
    with Session(engine) as session:
        item_count = session.scalar(
            select(func.count()).select_from(
                EbookItem
            )
        )

        offer_count = session.scalar(
            select(func.count()).select_from(
                StoreOffer
            )
        )

    return int(item_count), int(offer_count)


def test_repository_policy_contract() -> None:
    repository = (
        Path(__file__).resolve().parents[1]
    )

    policy_path = (
        repository
        / "config"
        / "x_r13_one_shot_production_import_policy.json"
    )

    policy = runner.load_json(policy_path)

    runner.validate_digest(
        policy,
        "policy_digest_sha256",
        "repository policy",
    )

    runner.validate_policy(policy)

    assert (
        policy["candidate"]["store_item_id"]
        == "4310000887411"
    )

    assert (
        policy["candidate"]["item_type"]
        == "tankobon"
    )


def test_successful_single_candidate_import(
    tmp_path: Path,
) -> None:
    paths, engine = build_case(tmp_path)

    result = runner.run_import(paths)

    assert result["summary"]["processed"] == 1
    assert result["summary"]["created"] == 1
    assert (
        result["summary"]["offer_created"]
        == 1
    )

    assert database_counts(engine) == (1, 1)

    assert (
        result["post_write_verification"][
            "foreign_key_failure_count"
        ]
        == 0
    )

    assert (
        result["post_write_verification"][
            "integrity_check"
        ]
        == "ok"
    )

    claim = json.loads(
        paths.execution_claim.read_text(
            encoding="utf-8"
        )
    )

    assert claim["claim_state"] == "CLAIMED"
    assert "execution_completed" not in claim

    consumption = json.loads(
        paths.consumption_lock.read_text(
            encoding="utf-8"
        )
    )

    assert consumption["approval_consumed"] is True
    assert (
        consumption["production_import_executed"]
        is False
    )

    completion = json.loads(
        paths.completion_lock.read_text(
            encoding="utf-8"
        )
    )

    assert completion["execution_completed"] is True
    assert completion["reexecution_allowed"] is False


def test_duplicate_source_item_rejected(
    tmp_path: Path,
) -> None:
    def seed(engine: Any) -> None:
        with Session(engine) as session:
            session.add(
                EbookItem(
                    source_name="rakuten_kobo",
                    source_item_id="4310000887411",
                    title="Existing",
                    item_type="tankobon",
                )
            )
            session.commit()

    paths, _ = build_case(
        tmp_path,
        seed=seed,
    )

    with pytest.raises(
        runner.RunnerError,
        match="duplicate source identity",
    ):
        runner.run_import(paths)

    assert not paths.execution_claim.exists()


def test_duplicate_store_item_rejected(
    tmp_path: Path,
) -> None:
    def seed(engine: Any) -> None:
        with Session(engine) as session:
            item = EbookItem(
                source_name="other",
                source_item_id="other-1",
                title="Other",
                item_type="tankobon",
            )

            session.add(item)
            session.flush()

            session.add(
                StoreOffer(
                    ebook_item_id=item.id,
                    store_name="rakuten_kobo",
                    store_item_id="4310000887411",
                )
            )

            session.commit()

    paths, _ = build_case(
        tmp_path,
        seed=seed,
    )

    with pytest.raises(
        runner.RunnerError,
        match="duplicate store item",
    ):
        runner.run_import(paths)

    assert not paths.execution_claim.exists()


def test_approval_reuse_rejected(
    tmp_path: Path,
) -> None:
    paths, _ = build_case(tmp_path)

    paths.consumption_lock.write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        runner.RunnerError,
        match="one-shot output already exists",
    ):
        runner.run_import(paths)


def test_existing_execution_claim_rejected(
    tmp_path: Path,
) -> None:
    paths, _ = build_case(tmp_path)

    paths.execution_claim.write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        runner.RunnerError,
        match="one-shot output already exists",
    ):
        runner.run_import(paths)


def test_nonempty_wal_rejected(
    tmp_path: Path,
) -> None:
    paths, engine = build_case(tmp_path)
    engine.dispose()

    wal_path = Path(
        str(paths.database) + "-wal"
    )

    wal_path.write_bytes(
        b"not-empty"
    )

    with pytest.raises(
        runner.RunnerError,
        match="non-empty WAL",
    ):
        runner.run_import(paths)


def test_database_sha_mismatch_rejected(
    tmp_path: Path,
) -> None:
    paths, _ = build_case(
        tmp_path,
        database_sha_override=(
            "0" * 64
        ),
    )

    with pytest.raises(
        runner.RunnerError,
        match="database SHA",
    ):
        runner.run_import(paths)

    assert not paths.execution_claim.exists()


def test_failure_rolls_back_database(
    tmp_path: Path,
) -> None:
    paths, engine = build_case(
        tmp_path,
        row_overrides={
            "discount_rate": "101",
        },
    )

    with pytest.raises(Exception):
        runner.run_import(paths)

    assert database_counts(engine) == (0, 0)
    assert paths.execution_claim.is_file()
    assert paths.consumption_lock.is_file()
    assert not paths.result_pack.exists()
    assert not paths.completion_lock.exists()


def test_unapproved_execution_rejected(
    tmp_path: Path,
) -> None:
    paths, _ = build_case(
        tmp_path,
        permission_overrides={
            "production_import_execution_allowed": (
                False
            ),
        },
    )

    with pytest.raises(
        runner.RunnerError,
        match="required approval permission",
    ):
        runner.run_import(paths)

    assert not paths.execution_claim.exists()


def test_x_r11_runner_invocation_forbidden() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_x_r13_one_shot_production_import.py"
    )

    source = source_path.read_text(
        encoding="utf-8"
    )

    assert "scripts.run_x_r11" not in source
    assert "run_x_r11_one_shot_import" not in source
    assert "subprocess" not in source


def test_external_api_calls_forbidden() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_x_r13_one_shot_production_import.py"
    )

    tree = ast.parse(
        source_path.read_text(
            encoding="utf-8"
        )
    )

    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(
                alias.name
                for alias in node.names
            )

        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(
                node.module or ""
            )

    for forbidden in (
        "requests",
        "httpx",
        "urllib.request",
        "socket",
        "aiohttp",
    ):
        assert forbidden not in imported_modules


def test_credential_file_reads_forbidden() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_x_r13_one_shot_production_import.py"
    )

    source = source_path.read_text(
        encoding="utf-8"
    ).lower()

    assert "/etc/ai-media-os" not in source
    assert "credential.env" not in source
    assert "service_account.json" not in source
