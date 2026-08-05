from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from scripts.run_x_r8_isolated_x_fb_write import (
    XR8IsolatedWriteError,
    run_x_r8,
)


def create_source_database(
    path: Path,
) -> None:
    engine = create_engine(
        f"sqlite:///{path}"
    )

    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def test_x_r8_isolated_write_passes(
    tmp_path: Path,
) -> None:
    source_database = (
        tmp_path / "source.db"
    )
    run_root = tmp_path / "run"
    evidence_path = (
        tmp_path / "evidence.json"
    )

    create_source_database(
        source_database
    )

    source_before = (
        source_database.read_bytes()
    )

    result = run_x_r8(
        source_database_path=(
            source_database
        ),
        run_root=run_root,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        evidence_path=evidence_path,
    )

    source_after = (
        source_database.read_bytes()
    )

    assert result["status"] == (
        "PASS_ISOLATED_DATABASE_TO_X_FB_WRITE"
    )
    assert result[
        "seeded_candidate_detected"
    ] is True
    assert result[
        "current_record_written"
    ] is True
    assert result[
        "operation_result_written"
    ] is True
    assert result[
        "archive_created"
    ] is False
    assert result[
        "duplicate_initialize_rejected"
    ] is True
    assert result[
        "current_unchanged_after_duplicate"
    ] is True
    assert result[
        "source_database_unchanged"
    ] is True
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert result[
        "production_database_write"
    ] is False
    assert result["contains_pr"] is True

    assert Path(
        result["current_record_path"]
    ).is_file()
    assert Path(
        result["operation_result_path"]
    ).is_file()

    assert source_before == source_after
    assert evidence_path.is_file()

    evidence = json.loads(
        evidence_path.read_text(
            encoding="utf-8"
        )
    )

    assert evidence == result


def test_missing_source_database_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        XR8IsolatedWriteError,
        match="source database is missing",
    ):
        run_x_r8(
            source_database_path=(
                tmp_path / "missing.db"
            ),
            run_root=tmp_path / "run",
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            evidence_path=(
                tmp_path / "evidence.json"
            ),
        )


def test_nonempty_run_root_is_rejected(
    tmp_path: Path,
) -> None:
    source_database = (
        tmp_path / "source.db"
    )
    run_root = tmp_path / "run"

    create_source_database(
        source_database
    )

    run_root.mkdir()
    (
        run_root / "existing.txt"
    ).write_text(
        "existing",
        encoding="utf-8",
    )

    with pytest.raises(
        XR8IsolatedWriteError,
        match="run_root must be empty",
    ):
        run_x_r8(
            source_database_path=(
                source_database
            ),
            run_root=run_root,
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            evidence_path=(
                tmp_path / "evidence.json"
            ),
        )


def test_invalid_wordpress_base_url_is_rejected(
    tmp_path: Path,
) -> None:
    source_database = (
        tmp_path / "source.db"
    )

    create_source_database(
        source_database
    )

    with pytest.raises(
        XR8IsolatedWriteError,
        match=(
            "wordpress_base_url validation "
            "failed"
        ),
    ):
        run_x_r8(
            source_database_path=(
                source_database
            ),
            run_root=tmp_path / "run",
            wordpress_base_url=(
                "http://books.example.jp"
            ),
            evidence_path=(
                tmp_path / "evidence.json"
            ),
        )
