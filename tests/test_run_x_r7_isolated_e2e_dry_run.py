from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from scripts.run_x_r7_isolated_e2e_dry_run import (
    XR7IsolatedE2EError,
    run_x_r7,
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


def test_x_r7_isolated_e2e_passes(
    tmp_path: Path,
) -> None:
    source_db = tmp_path / "source.db"
    run_root = tmp_path / "run"
    evidence_path = (
        tmp_path / "evidence.json"
    )

    create_source_database(source_db)

    source_before = source_db.read_bytes()

    result = run_x_r7(
        source_database_path=source_db,
        run_root=run_root,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        evidence_path=evidence_path,
    )

    source_after = source_db.read_bytes()

    assert result["status"] == (
        "PASS_ISOLATED_DATABASE_E2E_DRY_RUN"
    )
    assert result[
        "seeded_candidate_detected"
    ] is True
    assert result[
        "source_database_unchanged"
    ] is True
    assert result[
        "isolated_database_seed_write"
    ] is True
    assert result[
        "production_database_write"
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
    assert result["contains_pr"] is True
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
        XR7IsolatedE2EError,
        match="source database is missing",
    ):
        run_x_r7(
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
    source_db = tmp_path / "source.db"
    run_root = tmp_path / "run"

    create_source_database(source_db)

    run_root.mkdir()
    (
        run_root / "existing.txt"
    ).write_text(
        "existing",
        encoding="utf-8",
    )

    with pytest.raises(
        XR7IsolatedE2EError,
        match="run_root must be empty",
    ):
        run_x_r7(
            source_database_path=source_db,
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
    source_db = tmp_path / "source.db"

    create_source_database(source_db)

    with pytest.raises(
        XR7IsolatedE2EError,
        match=(
            "wordpress_base_url validation "
            "failed"
        ),
    ):
        run_x_r7(
            source_database_path=source_db,
            run_root=tmp_path / "run",
            wordpress_base_url=(
                "http://books.example.jp"
            ),
            evidence_path=(
                tmp_path / "evidence.json"
            ),
        )
