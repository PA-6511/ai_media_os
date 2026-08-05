from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
)
from app.services.x_draft_feedback_registration_service import (
    XDraftFeedbackRegistrationService,
)
from scripts.build_x_r11_final_gate_design import (
    FINAL_APPROVAL_LABEL,
    run_x_r11_final_gate_design,
)
from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    run_x_r9,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    run_x_r10,
)
from scripts.issue_x_r11_final_approval_certificate import (
    run_x_r11_final_approval_protocol,
)
from scripts.run_x_r11_write_runner_prep_isolated import (
    CONSUMED_CERTIFICATE_STATE,
    CONSUMED_LOCK_STATE,
    CONSUMED_TOKEN_STATE,
    XR11WriteRunnerPrepError,
    run_x_r11_write_runner_prep,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


APPROVED_AT = (
    "2026-07-17T23:45:00+09:00"
)


def create_database(path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{path}"
    )

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def build_fixture(
    tmp_path: Path,
) -> dict[str, Path]:
    database = tmp_path / "source.db"
    generation_x_fb_root = (
        tmp_path / "generation_x_fb"
    )
    normal_x_fb_root = (
        tmp_path / "normal_x_fb"
    )

    create_database(database)

    seed = seed_isolated_candidate(
        database
    )

    prepare_isolated_x_fb_root(
        isolated_root=generation_x_fb_root,
        repository_root=Path.cwd(),
    )
    prepare_isolated_x_fb_root(
        isolated_root=normal_x_fb_root,
        repository_root=Path.cwd(),
    )

    engine = create_engine(
        f"sqlite:///{database}"
    )

    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            read_result = (
                WorkflowApprovedXDraftReadService(
                    session,
                    wordpress_base_url=(
                        "https://books.example.jp"
                    ),
                )
                .read_and_adapt(
                    seed["approval_request_id"]
                )
            )
    finally:
        engine.dispose()

    registration = (
        XDraftFeedbackRegistrationService()
        .dry_run_register(
            (
                read_result
                .adapter_result
                .x_draft_input
            ),
            storage_root=(
                generation_x_fb_root
            ),
        )
    )

    initialize_request_path = (
        tmp_path / "initialize_request.json"
    )

    initialize_request_path.write_text(
        json.dumps(
            registration.initialize_request,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    x_r9_result = run_x_r9(
        source_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=tmp_path / "x_r9_output",
        lock_root=tmp_path / "x_r9_locks",
        x_fb_storage_root=(
            generation_x_fb_root
        ),
        approval_request_id=(
            seed["approval_request_id"]
        ),
        database_scope="PYTEST_ISOLATED",
    )

    x_r10_result = run_x_r10(
        approval_pack_path=Path(
            x_r9_result["approval_pack_path"]
        ),
        lock_path=Path(
            x_r9_result["one_shot_lock_path"]
        ),
        approval_label=(
            REQUIRED_APPROVAL_LABEL
        ),
        approved_by="human-owner",
        approved_at=APPROVED_AT,
        output_root=tmp_path / "x_r10_output",
        token_root=tmp_path / "x_r10_tokens",
        x_fb_storage_root=(
            generation_x_fb_root
        ),
    )

    final_gate_output = (
        tmp_path / "final_gate_output"
    )

    final_gate_result = (
        run_x_r11_final_gate_design(
            source_database_path=database,
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            output_root=final_gate_output,
            normal_x_fb_root=(
                normal_x_fb_root
            ),
            approval_request_id=(
                seed["approval_request_id"]
            ),
            approval_pack_path=Path(
                x_r9_result[
                    "approval_pack_path"
                ]
            ),
            preflight_lock_path=Path(
                x_r9_result[
                    "one_shot_lock_path"
                ]
            ),
            approval_token_path=Path(
                x_r10_result[
                    "execution_token_path"
                ]
            ),
            initialize_request_path=(
                initialize_request_path
            ),
            database_scope="PYTEST_ISOLATED",
        )
    )

    final_gate_result_path = (
        final_gate_output
        / "x_r11_final_gate_result.json"
    )
    final_gate_design_path = Path(
        final_gate_result[
            "final_gate_design_path"
        ]
    )

    final_approval_result = (
        run_x_r11_final_approval_protocol(
            final_gate_result_path=(
                final_gate_result_path
            ),
            final_gate_design_path=(
                final_gate_design_path
            ),
            final_approval_label=(
                FINAL_APPROVAL_LABEL
            ),
            approved_by="human-owner",
            approved_at=APPROVED_AT,
            output_root=(
                tmp_path / "final_approval_output"
            ),
            certificate_root=(
                tmp_path / "certificates"
            ),
            normal_x_fb_root=(
                normal_x_fb_root
            ),
        )
    )

    return {
        "final_gate_result": (
            final_gate_result_path
        ),
        "final_gate_design": (
            final_gate_design_path
        ),
        "certificate": Path(
            final_approval_result[
                "final_approval_certificate_path"
            ]
        ),
        "normal_x_fb_root": (
            normal_x_fb_root
        ),
    }


def execute(
    tmp_path: Path,
    fixture: dict[str, Path],
    *,
    name: str,
    certificate: Path | None = None,
    fault_injection: str | None = None,
) -> dict:
    return run_x_r11_write_runner_prep(
        final_gate_result_path=(
            fixture["final_gate_result"]
        ),
        final_gate_design_path=(
            fixture["final_gate_design"]
        ),
        final_approval_certificate_path=(
            certificate
            or fixture["certificate"]
        ),
        run_root=tmp_path / name,
        evidence_path=(
            tmp_path / f"{name}_evidence.json"
        ),
        normal_x_fb_root=(
            fixture["normal_x_fb_root"]
        ),
        fault_injection=fault_injection,
    )


def test_write_runner_prep_rehearsal_passes(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    certificate_before = fixture[
        "certificate"
    ].read_bytes()

    result = execute(
        tmp_path,
        fixture,
        name="success",
    )

    assert result["status"] == (
        "PASS_ISOLATED_FINAL_WRITE_"
        "RUNNER_REHEARSAL"
    )
    assert result[
        "transaction_state"
    ] == "COMMITTED"
    assert result[
        "isolated_current_record_written"
    ] is True
    assert result[
        "isolated_operation_result_written"
    ] is True
    assert result[
        "certificate_consumed"
    ] is True
    assert result[
        "execution_token_consumed"
    ] is True
    assert result[
        "preflight_lock_consumed"
    ] is True
    assert result[
        "shared_transaction_id_verified"
    ] is True
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert result[
        "production_execution"
    ] is False

    consumed_certificate = json.loads(
        Path(
            result["consumed_certificate_path"]
        ).read_text(encoding="utf-8")
    )
    consumed_token = json.loads(
        Path(
            result["consumed_token_path"]
        ).read_text(encoding="utf-8")
    )
    consumed_lock = json.loads(
        Path(
            result["consumed_lock_path"]
        ).read_text(encoding="utf-8")
    )

    assert consumed_certificate[
        "certificate_state"
    ] == CONSUMED_CERTIFICATE_STATE
    assert consumed_token[
        "token_state"
    ] == CONSUMED_TOKEN_STATE
    assert consumed_lock[
        "lock_state"
    ] == CONSUMED_LOCK_STATE

    assert fixture[
        "certificate"
    ].read_bytes() == certificate_before


def test_consumed_certificate_cannot_be_reused(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    first = execute(
        tmp_path,
        fixture,
        name="first",
    )

    with pytest.raises(
        XR11WriteRunnerPrepError,
        match=(
            "final approval certificate state "
            "must be ISSUED_NOT_CONSUMED"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="second",
            certificate=Path(
                first[
                    "consumed_certificate_path"
                ]
            ),
        )


def test_tampered_certificate_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    tampered_path = (
        tmp_path / "tampered_certificate.json"
    )

    certificate = json.loads(
        fixture["certificate"].read_text(
            encoding="utf-8"
        )
    )

    certificate["approved_by"] = "attacker"

    tampered_path.write_text(
        json.dumps(
            certificate,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11WriteRunnerPrepError,
        match=(
            "final approval certificate "
            "tampering detected"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="tampered",
            certificate=tampered_path,
        )


def test_production_scope_certificate_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    invalid_path = (
        tmp_path / "production_certificate.json"
    )

    certificate = json.loads(
        fixture["certificate"].read_text(
            encoding="utf-8"
        )
    )

    certificate["certificate_scope"] = (
        "PRODUCTION_APPROVAL_NO_EXECUTION"
    )

    invalid_path.write_text(
        json.dumps(
            certificate,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11WriteRunnerPrepError,
        match=(
            "certificate scope must be "
            "ISOLATED_PROTOCOL_VALIDATION_ONLY"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="production_scope",
            certificate=invalid_path,
        )


@pytest.mark.parametrize(
    "checkpoint",
    [
        "AFTER_X_FB_WRITE",
        "AFTER_TOKEN_REPLACE",
    ],
)
def test_fault_injection_rolls_back(
    tmp_path: Path,
    checkpoint: str,
) -> None:
    fixture = build_fixture(tmp_path)
    run_root = (
        tmp_path / f"fault_{checkpoint}"
    )

    with pytest.raises(
        XR11WriteRunnerPrepError,
        match=f"FAULT_INJECTION:{checkpoint}",
    ):
        run_x_r11_write_runner_prep(
            final_gate_result_path=(
                fixture["final_gate_result"]
            ),
            final_gate_design_path=(
                fixture["final_gate_design"]
            ),
            final_approval_certificate_path=(
                fixture["certificate"]
            ),
            run_root=run_root,
            evidence_path=(
                tmp_path
                / f"{checkpoint}_evidence.json"
            ),
            normal_x_fb_root=(
                fixture["normal_x_fb_root"]
            ),
            fault_injection=checkpoint,
        )

    rollback = json.loads(
        (
            run_root
            / "transaction/rollback_result.json"
        ).read_text(encoding="utf-8")
    )
    journal = json.loads(
        (
            run_root
            / "transaction/journal.json"
        ).read_text(encoding="utf-8")
    )
    restored_certificate = json.loads(
        (
            run_root
            / (
                "artifacts/"
                "final_approval_certificate.json"
            )
        ).read_text(encoding="utf-8")
    )
    restored_token = json.loads(
        (
            run_root
            / "artifacts/approval_token.json"
        ).read_text(encoding="utf-8")
    )
    restored_lock = json.loads(
        (
            run_root
            / "artifacts/preflight_lock.json"
        ).read_text(encoding="utf-8")
    )

    assert rollback["status"] == (
        "ROLLBACK_COMPLETED"
    )
    assert journal["state"] == (
        "ROLLED_BACK"
    )
    assert rollback[
        "isolated_current_record_exists"
    ] is False
    assert rollback[
        "isolated_operation_result_exists"
    ] is False
    assert restored_certificate[
        "certificate_state"
    ] == "ISSUED_NOT_CONSUMED"
    assert restored_token[
        "token_state"
    ] == "ISSUED_NOT_CONSUMED"
    assert restored_lock[
        "lock_state"
    ] == "PREPARED_NOT_EXECUTABLE"
