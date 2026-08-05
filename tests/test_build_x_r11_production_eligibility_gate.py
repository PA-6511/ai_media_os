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
from scripts.build_x_r11_production_eligibility_gate import (
    XR11ProductionEligibilityError,
    run_x_r11_production_eligibility_gate,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


def create_database(path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{path}"
    )

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def run_gate(
    tmp_path: Path,
    *,
    database: Path,
    normal_x_fb_root: Path,
    name: str,
) -> dict:
    return run_x_r11_production_eligibility_gate(
        source_database_path=database,
        expected_production_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=tmp_path / name,
        normal_x_fb_root=normal_x_fb_root,
    )


def test_no_candidate_returns_no_go(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
        repository_root=Path.cwd(),
    )

    database_before = database.read_bytes()

    result = run_gate(
        tmp_path,
        database=database,
        normal_x_fb_root=normal_root,
        name="no_candidate",
    )

    assert result["status"] == (
        "PASS_PRODUCTION_READ_ONLY_"
        "NO_ELIGIBLE_CANDIDATE"
    )
    assert result[
        "eligible_candidate_count"
    ] == 0
    assert result[
        "eligibility_pack_created"
    ] is False
    assert result[
        "approval_pack_created"
    ] is False
    assert result[
        "approval_token_created"
    ] is False
    assert result[
        "final_approval_certificate_created"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"
    assert database.read_bytes() == (
        database_before
    )


def test_one_candidate_creates_eligibility_pack(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)
    seed_isolated_candidate(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
        repository_root=Path.cwd(),
    )

    database_before = database.read_bytes()

    result = run_gate(
        tmp_path,
        database=database,
        normal_x_fb_root=normal_root,
        name="one_candidate",
    )

    assert result["status"] == (
        "PASS_PRODUCTION_ELIGIBILITY_"
        "PACK_READY_NO_EXECUTION"
    )
    assert result[
        "eligible_candidate_count"
    ] == 1
    assert result[
        "candidate_revalidated"
    ] is True
    assert result[
        "wordpress_status_revalidated"
    ] == "DRAFT"
    assert result[
        "wordpress_host_revalidated"
    ] is True
    assert result[
        "x_fb_dry_run_status"
    ] == "PASS_DRY_RUN_NO_WRITE"
    assert result[
        "fixed_target_paths_verified"
    ] is True
    assert result[
        "approval_pack_created"
    ] is False
    assert result[
        "approval_token_created"
    ] is False
    assert result[
        "final_approval_certificate_created"
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
    assert database.read_bytes() == (
        database_before
    )

    pack_path = Path(
        result["eligibility_pack_path"]
    )
    request_path = Path(
        result["initialize_request_path"]
    )

    assert pack_path.is_file()
    assert request_path.is_file()

    pack = json.loads(
        pack_path.read_text(
            encoding="utf-8"
        )
    )

    assert pack["database_scope"] == (
        "PRODUCTION_READ_ONLY"
    )
    assert pack["approval_state"] == (
        "NOT_APPROVED_FOR_PRODUCTION_"
        "CANDIDATE_PREFLIGHT_PACK"
    )
    assert pack[
        "approval_label_consumed"
    ] is False
    assert pack[
        "approval_pack_created"
    ] is False
    assert pack[
        "execution_allowed"
    ] is False
    assert pack[
        "normal_x_fb_write_allowed"
    ] is False
    assert pack[
        "fixed_target_paths"
    ]["paths_fixed"] is True
    assert pack[
        "fixed_target_paths"
    ][
        "path_substitution_allowed"
    ] is False


def test_multiple_candidates_fail_closed(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)

    seed_isolated_candidate(database)
    seed_isolated_candidate(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
        repository_root=Path.cwd(),
    )

    result = run_gate(
        tmp_path,
        database=database,
        normal_x_fb_root=normal_root,
        name="multiple",
    )

    assert result["status"] == (
        "BLOCKED_MULTIPLE_ELIGIBLE_"
        "PRODUCTION_CANDIDATES"
    )
    assert result[
        "eligible_candidate_count"
    ] >= 2
    assert result["fail_closed"] is True
    assert result[
        "human_selection_allowed"
    ] is False
    assert result[
        "automatic_selection_allowed"
    ] is False
    assert result[
        "authorized_next_phase"
    ] is None
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False
    assert result[
        "production_status"
    ] == "NO_GO"


def test_wrong_database_path_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "database.db"
    expected = tmp_path / "expected.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)
    create_database(expected)

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
        repository_root=Path.cwd(),
    )

    with pytest.raises(
        XR11ProductionEligibilityError,
        match=(
            "source database must exactly match "
            "the fixed production database path"
        ),
    ):
        run_x_r11_production_eligibility_gate(
            source_database_path=database,
            expected_production_database_path=(
                expected
            ),
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            output_root=(
                tmp_path / "wrong_database"
            ),
            normal_x_fb_root=normal_root,
        )


def test_existing_current_record_blocks_gate(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)

    seed = seed_isolated_candidate(
        database
    )

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
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

    preview = (
        XDraftFeedbackRegistrationService()
        .generation_service
        .generate(
            read_result
            .adapter_result
            .x_draft_input
        )
    )

    current_path = (
        normal_root
        / "exchange/input/x_post_feedback"
        / preview.feedback_id
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
        XR11ProductionEligibilityError,
        match=(
            "normal X-FB current.json "
            "already exists"
        ),
    ):
        run_gate(
            tmp_path,
            database=database,
            normal_x_fb_root=normal_root,
            name="existing_current",
        )
