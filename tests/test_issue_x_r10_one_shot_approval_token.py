from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    run_x_r9,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    XR10ApprovalTokenError,
    run_x_r10,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
)


APPROVED_AT = (
    "2026-07-17T22:00:00+09:00"
)


def create_database(path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{path}"
    )

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def build_x_r9_fixture(
    tmp_path: Path,
) -> tuple[dict, Path]:
    database = tmp_path / "source.db"
    x_fb_root = tmp_path / "x_fb"

    create_database(database)
    seed = seed_isolated_candidate(database)

    prepare_isolated_x_fb_root(
        isolated_root=x_fb_root,
        repository_root=Path.cwd(),
    )

    result = run_x_r9(
        source_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=tmp_path / "x_r9_output",
        lock_root=tmp_path / "x_r9_locks",
        x_fb_storage_root=x_fb_root,
        approval_request_id=(
            seed["approval_request_id"]
        ),
        database_scope="PYTEST_ISOLATED",
    )

    return result, x_fb_root


def issue_token(
    *,
    tmp_path: Path,
    x_r9_result: dict,
    x_fb_root: Path,
    approval_label: str = (
        REQUIRED_APPROVAL_LABEL
    ),
    approved_at: str = APPROVED_AT,
    output_name: str = "x_r10_output",
    token_root: Path | None = None,
) -> dict:
    return run_x_r10(
        approval_pack_path=Path(
            x_r9_result["approval_pack_path"]
        ),
        lock_path=Path(
            x_r9_result["one_shot_lock_path"]
        ),
        approval_label=approval_label,
        approved_by="human-owner",
        approved_at=approved_at,
        output_root=tmp_path / output_name,
        token_root=(
            token_root
            or tmp_path / "x_r10_tokens"
        ),
        x_fb_storage_root=x_fb_root,
    )


def test_x_r10_issues_non_executable_token(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )

    pack_path = Path(
        x_r9_result["approval_pack_path"]
    )
    lock_path = Path(
        x_r9_result["one_shot_lock_path"]
    )

    pack_before = pack_path.read_bytes()
    lock_before = lock_path.read_bytes()

    result = issue_token(
        tmp_path=tmp_path,
        x_r9_result=x_r9_result,
        x_fb_root=x_fb_root,
    )

    assert result["status"] == (
        "PASS_APPROVAL_TOKEN_ISSUED_"
        "NO_EXECUTION"
    )
    assert result[
        "approval_label_consumed"
    ] is True
    assert result[
        "preflight_lock_consumed"
    ] is False
    assert result[
        "execution_token_consumed"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert result[
        "current_record_written"
    ] is False
    assert result[
        "operation_result_written"
    ] is False

    token_path = Path(
        result["execution_token_path"]
    )

    assert token_path.is_file()

    token = json.loads(
        token_path.read_text(
            encoding="utf-8"
        )
    )

    assert token["token_state"] == (
        "ISSUED_NOT_CONSUMED"
    )
    assert token[
        "approval_label_consumed"
    ] is True
    assert token[
        "preflight_lock_consumed"
    ] is False
    assert token[
        "execution_token_consumed"
    ] is False
    assert token[
        "execution_allowed"
    ] is False
    assert token[
        "normal_x_fb_write_allowed"
    ] is False

    assert pack_path.read_bytes() == pack_before
    assert lock_path.read_bytes() == lock_before


def test_wrong_approval_label_is_rejected(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )

    with pytest.raises(
        XR10ApprovalTokenError,
        match="approval label must exactly match",
    ):
        issue_token(
            tmp_path=tmp_path,
            x_r9_result=x_r9_result,
            x_fb_root=x_fb_root,
            approval_label=(
                "APPROVED_FOR_X_FB_RECORD"
            ),
        )


def test_tampered_approval_pack_is_rejected(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )

    pack_path = Path(
        x_r9_result["approval_pack_path"]
    )
    pack = json.loads(
        pack_path.read_text(
            encoding="utf-8"
        )
    )

    pack["generated_text"] = (
        pack["generated_text"]
        + "\n改ざん"
    )

    pack_path.write_text(
        json.dumps(
            pack,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR10ApprovalTokenError,
        match="approval pack tampering detected",
    ):
        issue_token(
            tmp_path=tmp_path,
            x_r9_result=x_r9_result,
            x_fb_root=x_fb_root,
        )


def test_tampered_lock_digest_is_rejected(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )

    lock_path = Path(
        x_r9_result["one_shot_lock_path"]
    )
    lock = json.loads(
        lock_path.read_text(
            encoding="utf-8"
        )
    )

    lock[
        "approval_pack_digest_sha256"
    ] = "0" * 64

    lock_path.write_text(
        json.dumps(
            lock,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        XR10ApprovalTokenError,
        match=(
            "one-shot lock digest does not "
            "match approval pack"
        ),
    ):
        issue_token(
            tmp_path=tmp_path,
            x_r9_result=x_r9_result,
            x_fb_root=x_fb_root,
        )


def test_duplicate_token_issue_is_rejected(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )
    token_root = tmp_path / "tokens"

    issue_token(
        tmp_path=tmp_path,
        x_r9_result=x_r9_result,
        x_fb_root=x_fb_root,
        output_name="first_output",
        token_root=token_root,
    )

    with pytest.raises(
        XR10ApprovalTokenError,
        match="approval token already exists",
    ):
        issue_token(
            tmp_path=tmp_path,
            x_r9_result=x_r9_result,
            x_fb_root=x_fb_root,
            output_name="second_output",
            token_root=token_root,
        )


def test_timezone_less_approved_at_is_rejected(
    tmp_path: Path,
) -> None:
    x_r9_result, x_fb_root = (
        build_x_r9_fixture(tmp_path)
    )

    with pytest.raises(
        XR10ApprovalTokenError,
        match=(
            "approved_at must include timezone"
        ),
    ):
        issue_token(
            tmp_path=tmp_path,
            x_r9_result=x_r9_result,
            x_fb_root=x_fb_root,
            approved_at="2026-07-17T22:00:00",
        )
