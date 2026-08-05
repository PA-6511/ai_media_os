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
    XR11FinalGateDesignError,
    run_x_r11_final_gate_design,
)
from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    run_x_r9,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    run_x_r10,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


APPROVED_AT = (
    "2026-07-17T23:00:00+09:00"
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
) -> dict[str, Path | str]:
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
        output_root=tmp_path / "x_r10_output",
        token_root=tmp_path / "x_r10_tokens",
        x_fb_storage_root=(
            generation_x_fb_root
        ),
    )

    return {
        "database": database,
        "approval_request_id": (
            seed["approval_request_id"]
        ),
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
        "initialize_request": request_path,
        "normal_x_fb_root": (
            normal_x_fb_root
        ),
    }


def execute(
    tmp_path: Path,
    fixture: dict[str, Path | str],
    *,
    output_name: str = "final_gate",
    initialize_request: Path | None = None,
    source_database: Path | None = None,
) -> dict:
    return run_x_r11_final_gate_design(
        source_database_path=(
            source_database
            or Path(fixture["database"])
        ),
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=(
            tmp_path / output_name
        ),
        normal_x_fb_root=Path(
            fixture["normal_x_fb_root"]
        ),
        approval_request_id=str(
            fixture["approval_request_id"]
        ),
        approval_pack_path=Path(
            fixture["approval_pack"]
        ),
        preflight_lock_path=Path(
            fixture["preflight_lock"]
        ),
        approval_token_path=Path(
            fixture["approval_token"]
        ),
        initialize_request_path=(
            initialize_request
            or Path(
                fixture[
                    "initialize_request"
                ]
            )
        ),
        database_scope="PYTEST_ISOLATED",
    )


def test_final_gate_design_passes(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    database_before = Path(
        fixture["database"]
    ).read_bytes()

    result = execute(
        tmp_path,
        fixture,
    )

    database_after = Path(
        fixture["database"]
    ).read_bytes()

    assert result["status"] == (
        "PASS_FINAL_GATE_DESIGN_"
        "READY_NO_EXECUTION"
    )
    assert result[
        "candidate_revalidated"
    ] is True
    assert result[
        "approval_pack_verified"
    ] is True
    assert result[
        "preflight_lock_verified"
    ] is True
    assert result[
        "approval_token_verified"
    ] is True
    assert result[
        "initialize_request_verified"
    ] is True
    assert result[
        "target_paths_fixed"
    ] is True
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
    assert database_before == database_after

    design = json.loads(
        Path(
            result["final_gate_design_path"]
        ).read_text(encoding="utf-8")
    )

    assert design[
        "required_final_approval_label"
    ] == FINAL_APPROVAL_LABEL
    assert design[
        "final_approval_label_consumed"
    ] is False
    assert design[
        "execution_contract"
    ][
        "maximum_record_count"
    ] == 1
    assert design[
        "failure_policy"
    ]["automatic_retry_allowed"] is False
    assert design[
        "failure_policy"
    ][
        "rollback_after_normal_current_write"
    ] == "NO_AUTOMATIC_DELETE"


def test_tampered_initialize_request_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    tampered_path = (
        tmp_path / "tampered_request.json"
    )
    request = json.loads(
        Path(
            fixture["initialize_request"]
        ).read_text(encoding="utf-8")
    )

    request["generated_text"] = (
        "改ざんされた下書き"
    )

    tampered_path.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11FinalGateDesignError,
        match=(
            "initialize request differs"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            output_name="tampered_request_run",
            initialize_request=tampered_path,
        )


def test_existing_normal_current_blocks_gate(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    pack = json.loads(
        Path(
            fixture["approval_pack"]
        ).read_text(encoding="utf-8")
    )

    current_path = (
        Path(fixture["normal_x_fb_root"])
        / "exchange/input/x_post_feedback"
        / pack["feedback_id"]
        / "current.json"
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
        XR11FinalGateDesignError,
        match=(
            "normal X-FB current.json "
            "already exists"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            output_name="existing_current_run",
        )


def test_consumed_token_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = build_fixture(tmp_path)

    token_path = Path(
        fixture["approval_token"]
    )
    token = json.loads(
        token_path.read_text(
            encoding="utf-8"
        )
    )

    token["token_state"] = (
        "CONSUMED_BY_TEST"
    )

    token_path.write_text(
        json.dumps(
            token,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR11FinalGateDesignError,
        match=(
            "approval token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    ):
        execute(
            tmp_path,
            fixture,
            output_name="consumed_token_run",
        )


def test_no_candidate_creates_no_gate(
    tmp_path: Path,
) -> None:
    database = tmp_path / "empty.db"
    normal_x_fb_root = (
        tmp_path / "normal_x_fb"
    )

    create_database(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_x_fb_root,
        repository_root=Path.cwd(),
    )

    result = run_x_r11_final_gate_design(
        source_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=(
            tmp_path / "no_candidate"
        ),
        normal_x_fb_root=(
            normal_x_fb_root
        ),
        database_scope="PYTEST_EMPTY",
    )

    assert result["status"] == (
        "PASS_READ_ONLY_NO_ELIGIBLE_"
        "CANDIDATE_NO_FINAL_GATE"
    )
    assert result["candidate_count"] == 0
    assert result[
        "final_gate_design_created"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False


def test_output_inside_normal_x_fb_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "empty.db"
    normal_x_fb_root = (
        tmp_path / "normal_x_fb"
    )

    create_database(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_x_fb_root,
        repository_root=Path.cwd(),
    )

    forbidden_output = (
        normal_x_fb_root
        / "exchange/logs"
        / "x_r11_design"
    )

    with pytest.raises(
        XR11FinalGateDesignError,
        match=(
            "output_root must not be inside "
            "normal X-FB storage"
        ),
    ):
        run_x_r11_final_gate_design(
            source_database_path=database,
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            output_root=forbidden_output,
            normal_x_fb_root=(
                normal_x_fb_root
            ),
            database_scope="PYTEST_EMPTY",
        )
