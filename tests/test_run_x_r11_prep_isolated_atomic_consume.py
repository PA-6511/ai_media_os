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
from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    run_x_r9,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    run_x_r10,
)
from scripts.run_x_r11_prep_isolated_atomic_consume import (
    CONSUMED_LOCK_STATE,
    CONSUMED_TOKEN_STATE,
    XR11PrepError,
    run_x_r11_prep,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


APPROVED_AT = (
    "2026-07-17T22:30:00+09:00"
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
) -> dict[str, Path | dict]:
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

    request_path = (
        tmp_path / "initialize_request.json"
    )
    request_path.write_text(
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
            x_r9_result[
                "approval_pack_path"
            ]
        ),
        lock_path=Path(
            x_r9_result[
                "one_shot_lock_path"
            ]
        ),
        approval_label=(
            REQUIRED_APPROVAL_LABEL
        ),
        approved_by="human-owner",
        approved_at=APPROVED_AT,
        output_root=(
            tmp_path / "x_r10_output"
        ),
        token_root=(
            tmp_path / "x_r10_tokens"
        ),
        x_fb_storage_root=(
            generation_x_fb_root
        ),
    )

    return {
        "approval_pack": Path(
            x_r9_result[
                "approval_pack_path"
            ]
        ),
        "preflight_lock": Path(
            x_r9_result[
                "one_shot_lock_path"
            ]
        ),
        "approval_token": Path(
            x_r10_result[
                "execution_token_path"
            ]
        ),
        "initialize_request": (
            request_path
        ),
        "normal_x_fb_root": (
            normal_x_fb_root
        ),
    }


def execute(
    tmp_path: Path,
    fixture: dict[str, Path | dict],
    *,
    name: str,
    fault_injection: str | None = None,
    approval_pack: Path | None = None,
    preflight_lock: Path | None = None,
    approval_token: Path | None = None,
    initialize_request: Path | None = None,
) -> dict:
    return run_x_r11_prep(
        approval_pack_path=(
            approval_pack
            or fixture["approval_pack"]
        ),
        preflight_lock_path=(
            preflight_lock
            or fixture["preflight_lock"]
        ),
        approval_token_path=(
            approval_token
            or fixture["approval_token"]
        ),
        initialize_request_path=(
            initialize_request
            or fixture["initialize_request"]
        ),
        run_root=tmp_path / name,
        evidence_path=(
            tmp_path
            / f"{name}_evidence.json"
        ),
        normal_x_fb_root=(
            fixture["normal_x_fb_root"]
        ),
        fault_injection=fault_injection,
    )


def test_x_r11_prep_consumes_isolated_copies(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    original_token = Path(
        fixture["approval_token"]
    ).read_bytes()
    original_lock = Path(
        fixture["preflight_lock"]
    ).read_bytes()

    result = execute(
        tmp_path,
        fixture,
        name="success",
    )

    assert result["status"] == (
        "PASS_ISOLATED_ATOMIC_"
        "TOKEN_LOCK_CONSUMPTION"
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
        "execution_token_consumed"
    ] is True
    assert result[
        "preflight_lock_consumed"
    ] is True
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert result[
        "production_execution"
    ] is False

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

    assert consumed_token["token_state"] == (
        CONSUMED_TOKEN_STATE
    )
    assert consumed_token[
        "execution_token_consumed"
    ] is True
    assert consumed_lock["lock_state"] == (
        CONSUMED_LOCK_STATE
    )
    assert consumed_lock["consumed"] is True

    assert Path(
        fixture["approval_token"]
    ).read_bytes() == original_token
    assert Path(
        fixture["preflight_lock"]
    ).read_bytes() == original_lock


def test_consumed_token_cannot_be_reused(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    first = execute(
        tmp_path,
        fixture,
        name="first",
    )

    with pytest.raises(
        XR11PrepError,
        match=(
            "execution token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="second",
            approval_pack=Path(
                first[
                    "isolated_approval_pack_path"
                ]
            ),
            preflight_lock=Path(
                first["consumed_lock_path"]
            ),
            approval_token=Path(
                first["consumed_token_path"]
            ),
            initialize_request=Path(
                first[
                    "isolated_initialize_request_path"
                ]
            ),
        )


def test_tampered_token_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    tampered_path = (
        tmp_path / "tampered_token.json"
    )
    token = json.loads(
        Path(
            fixture["approval_token"]
        ).read_text(encoding="utf-8")
    )
    token["approved_by"] = "attacker"

    tampered_path.write_text(
        json.dumps(
            token,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11PrepError,
        match=(
            "execution token tampering "
            "detected"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="tampered_token_run",
            approval_token=tampered_path,
        )


def test_tampered_pack_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    tampered_path = (
        tmp_path / "tampered_pack.json"
    )
    pack = json.loads(
        Path(
            fixture["approval_pack"]
        ).read_text(encoding="utf-8")
    )
    pack["generated_text"] += "\n改ざん"

    tampered_path.write_text(
        json.dumps(
            pack,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11PrepError,
        match=(
            "approval pack tampering detected"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            name="tampered_pack_run",
            approval_pack=tampered_path,
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
        XR11PrepError,
        match=f"FAULT_INJECTION:{checkpoint}",
    ):
        run_x_r11_prep(
            approval_pack_path=Path(
                fixture["approval_pack"]
            ),
            preflight_lock_path=Path(
                fixture["preflight_lock"]
            ),
            approval_token_path=Path(
                fixture["approval_token"]
            ),
            initialize_request_path=Path(
                fixture["initialize_request"]
            ),
            run_root=run_root,
            evidence_path=(
                tmp_path
                / f"{checkpoint}_evidence.json"
            ),
            normal_x_fb_root=Path(
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
    assert restored_token["token_state"] == (
        "ISSUED_NOT_CONSUMED"
    )
    assert restored_lock["lock_state"] == (
        "PREPARED_NOT_EXECUTABLE"
    )
