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
    XR11FinalApprovalError,
    run_x_r11_final_approval_protocol,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


APPROVED_AT = (
    "2026-07-17T23:30:00+09:00"
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

    return {
        "final_gate_result": (
            final_gate_output
            / "x_r11_final_gate_result.json"
        ),
        "final_gate_design": Path(
            final_gate_result[
                "final_gate_design_path"
            ]
        ),
        "normal_x_fb_root": (
            normal_x_fb_root
        ),
    }


def issue_certificate(
    tmp_path: Path,
    fixture: dict[str, Path],
    *,
    approval_label: str = (
        FINAL_APPROVAL_LABEL
    ),
    approved_at: str = APPROVED_AT,
    output_name: str = "approval_output",
    certificate_root: Path | None = None,
) -> dict:
    return run_x_r11_final_approval_protocol(
        final_gate_result_path=(
            fixture["final_gate_result"]
        ),
        final_gate_design_path=(
            fixture["final_gate_design"]
        ),
        final_approval_label=(
            approval_label
        ),
        approved_by="human-owner",
        approved_at=approved_at,
        output_root=(
            tmp_path / output_name
        ),
        certificate_root=(
            certificate_root
            or tmp_path / "certificates"
        ),
        normal_x_fb_root=(
            fixture["normal_x_fb_root"]
        ),
    )


def test_final_approval_certificate_issued(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    result = issue_certificate(
        tmp_path,
        fixture,
    )

    assert result["status"] == (
        "PASS_FINAL_APPROVAL_CERTIFICATE_"
        "ISSUED_NO_EXECUTION"
    )
    assert result[
        "final_approval_label_consumed"
    ] is True
    assert result[
        "certificate_consumed"
    ] is False
    assert result[
        "execution_token_consumed"
    ] is False
    assert result[
        "preflight_lock_consumed"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False
    assert result[
        "current_record_written"
    ] is False
    assert result[
        "operation_result_written"
    ] is False
    assert result[
        "normal_x_fb_storage_modified"
    ] is False

    certificate = json.loads(
        Path(
            result[
                "final_approval_certificate_path"
            ]
        ).read_text(encoding="utf-8")
    )

    assert certificate[
        "certificate_state"
    ] == "ISSUED_NOT_CONSUMED"
    assert certificate[
        "certificate_scope"
    ] == "ISOLATED_PROTOCOL_VALIDATION_ONLY"
    assert certificate[
        "final_execution_still_requires_explicit_command"
    ] is True


def test_wrong_final_label_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    with pytest.raises(
        XR11FinalApprovalError,
        match=(
            "final approval label must exactly "
            "match"
        ),
    ):
        issue_certificate(
            tmp_path,
            fixture,
            approval_label=(
                "APPROVED_FOR_X_R11_WRITE"
            ),
        )


def test_tampered_design_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    design_path = fixture[
        "final_gate_design"
    ]

    design = json.loads(
        design_path.read_text(
            encoding="utf-8"
        )
    )
    design[
        "final_approval_state"
    ] = "APPROVED_BY_ATTACKER"

    design_path.write_text(
        json.dumps(
            design,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11FinalApprovalError,
        match=(
            "final-gate approval state "
            "is invalid"
        ),
    ):
        issue_certificate(
            tmp_path,
            fixture,
        )


def test_duplicate_certificate_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)
    certificate_root = (
        tmp_path / "certificates"
    )

    issue_certificate(
        tmp_path,
        fixture,
        output_name="first_output",
        certificate_root=certificate_root,
    )

    with pytest.raises(
        XR11FinalApprovalError,
        match=(
            "final approval certificate "
            "already exists"
        ),
    ):
        issue_certificate(
            tmp_path,
            fixture,
            output_name="second_output",
            certificate_root=(
                certificate_root
            ),
        )


def test_existing_current_blocks_certificate(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    design = json.loads(
        fixture[
            "final_gate_design"
        ].read_text(encoding="utf-8")
    )

    current_path = Path(
        design["target_paths"][
            "current_record_path"
        ]
    )
    current_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    current_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11FinalApprovalError,
        match=(
            "normal X-FB current.json "
            "already exists"
        ),
    ):
        issue_certificate(
            tmp_path,
            fixture,
        )


def test_timezone_less_approval_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    with pytest.raises(
        XR11FinalApprovalError,
        match=(
            "approved_at must include timezone"
        ),
    ):
        issue_certificate(
            tmp_path,
            fixture,
            approved_at=(
                "2026-07-17T23:30:00"
            ),
        )
