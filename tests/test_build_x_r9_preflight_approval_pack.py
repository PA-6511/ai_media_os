from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from scripts.build_x_r9_preflight_approval_pack import (
    XR9PreflightError,
    run_x_r9,
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


def test_x_r9_builds_non_executable_pack(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.db"
    output_root = tmp_path / "output"
    lock_root = tmp_path / "locks"
    x_fb_root = tmp_path / "x_fb"

    create_database(database)
    seed = seed_isolated_candidate(database)

    prepare_isolated_x_fb_root(
        isolated_root=x_fb_root,
        repository_root=Path.cwd(),
    )

    before = database.read_bytes()

    result = run_x_r9(
        source_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=output_root,
        lock_root=lock_root,
        x_fb_storage_root=x_fb_root,
        approval_request_id=(
            seed["approval_request_id"]
        ),
        database_scope="PYTEST_ISOLATED",
    )

    after = database.read_bytes()

    assert result["status"] == (
        "PASS_PREFLIGHT_APPROVAL_"
        "PACK_LOCKED_NO_EXECUTION"
    )
    assert result["execution_allowed"] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False
    assert result[
        "approval_label_consumed"
    ] is False
    assert result[
        "one_shot_lock_created"
    ] is True
    assert result[
        "current_record_written"
    ] is False
    assert result[
        "operation_result_written"
    ] is False
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert before == after

    pack = json.loads(
        Path(
            result["approval_pack_path"]
        ).read_text(encoding="utf-8")
    )
    lock = json.loads(
        Path(
            result["one_shot_lock_path"]
        ).read_text(encoding="utf-8")
    )
    preview = Path(
        result["diff_preview_path"]
    ).read_text(encoding="utf-8")

    assert pack["approval_state"] == (
        "NOT_APPROVED_FOR_X_FB_"
        "ONE_SHOT_RECORD"
    )
    assert pack["execution_allowed"] is False
    assert lock["lock_state"] == (
        "PREPARED_NOT_EXECUTABLE"
    )
    assert lock["execution_allowed"] is False
    assert "GENERATED_X_DRAFT" in preview
    assert "#PR" in preview


def test_duplicate_lock_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.db"
    lock_root = tmp_path / "locks"
    x_fb_root = tmp_path / "x_fb"

    create_database(database)
    seed = seed_isolated_candidate(database)

    prepare_isolated_x_fb_root(
        isolated_root=x_fb_root,
        repository_root=Path.cwd(),
    )

    common = {
        "source_database_path": database,
        "wordpress_base_url": (
            "https://books.example.jp"
        ),
        "lock_root": lock_root,
        "x_fb_storage_root": x_fb_root,
        "approval_request_id": (
            seed["approval_request_id"]
        ),
        "database_scope": "PYTEST_ISOLATED",
    }

    run_x_r9(
        output_root=tmp_path / "first",
        **common,
    )

    with pytest.raises(
        XR9PreflightError,
        match=(
            "one-shot preflight lock "
            "already exists"
        ),
    ):
        run_x_r9(
            output_root=tmp_path / "second",
            **common,
        )


def test_no_candidate_creates_no_lock(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.db"
    output_root = tmp_path / "output"
    lock_root = tmp_path / "locks"
    x_fb_root = tmp_path / "x_fb"

    create_database(database)

    prepare_isolated_x_fb_root(
        isolated_root=x_fb_root,
        repository_root=Path.cwd(),
    )

    result = run_x_r9(
        source_database_path=database,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=output_root,
        lock_root=lock_root,
        x_fb_storage_root=x_fb_root,
        database_scope="PYTEST_EMPTY",
    )

    assert result["status"] == (
        "PASS_READ_ONLY_NO_ELIGIBLE_"
        "CANDIDATE_NO_LOCK"
    )
    assert result[
        "one_shot_lock_created"
    ] is False
    assert not lock_root.exists()


def test_missing_database_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        XR9PreflightError,
        match="source database is missing",
    ):
        run_x_r9(
            source_database_path=(
                tmp_path / "missing.db"
            ),
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            output_root=tmp_path / "output",
            lock_root=tmp_path / "locks",
        )
