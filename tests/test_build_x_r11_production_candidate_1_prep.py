from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from scripts.build_x_r11_production_candidate_1_prep import (
    XR11ProductionCandidatePrepError,
    run_x_r11_production_candidate_1_prep,
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


def run_prep(
    tmp_path: Path,
    *,
    database: Path,
    normal_root: Path,
    output_name: str,
) -> dict:
    return run_x_r11_production_candidate_1_prep(
        source_database_path=database,
        expected_production_database_path=(
            database
        ),
        wordpress_base_url=(
            "https://books.example.jp"
        ),
        output_root=(
            tmp_path / output_name
        ),
        normal_x_fb_root=normal_root,
    )


def test_no_candidate_reports_no_eligible(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    normal_root = tmp_path / "normal_x_fb"

    create_database(database)

    prepare_isolated_x_fb_root(
        isolated_root=normal_root,
        repository_root=Path.cwd(),
    )

    result = run_prep(
        tmp_path,
        database=database,
        normal_root=normal_root,
        output_name="no_candidate",
    )

    assert result["status"] == (
        "PASS_CANDIDATE_PREP_"
        "NO_ELIGIBLE_PRODUCTION_CANDIDATE"
    )
    assert result[
        "repository_eligible_candidate_count"
    ] == 0
    assert result[
        "candidate_selected"
    ] is False
    assert result[
        "normal_x_fb_write_allowed"
    ] is False


def test_one_candidate_requires_human_selection(
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

    result = run_prep(
        tmp_path,
        database=database,
        normal_root=normal_root,
        output_name="one_candidate",
    )

    assert result["status"] == (
        "PASS_CANDIDATE_PREP_"
        "ONE_ELIGIBLE_REVIEW_REQUIRED"
    )
    assert result[
        "repository_eligible_candidate_count"
    ] == 1
    assert result[
        "human_selection_required"
    ] is True
    assert result[
        "automatic_selection_allowed"
    ] is False
    assert result[
        "candidate_selected"
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

    result = run_prep(
        tmp_path,
        database=database,
        normal_root=normal_root,
        output_name="multiple",
    )

    assert result["status"] == (
        "BLOCKED_MULTIPLE_ELIGIBLE_"
        "PRODUCTION_CANDIDATES"
    )
    assert result[
        "repository_eligible_candidate_count"
    ] >= 2
    assert result[
        "automatic_selection_allowed"
    ] is False


def test_database_and_x_fb_remain_unchanged(
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

    result = run_prep(
        tmp_path,
        database=database,
        normal_root=normal_root,
        output_name="unchanged",
    )

    assert database.read_bytes() == (
        database_before
    )
    assert result[
        "source_database_unchanged"
    ] is True
    assert result[
        "normal_x_fb_storage_modified"
    ] is False
    assert result["database_write"] is False
    assert result["wordpress_write"] is False


def test_wrong_database_path_is_rejected(
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
        XR11ProductionCandidatePrepError,
        match=(
            "source database must exactly match "
            "the fixed production database path"
        ),
    ):
        run_x_r11_production_candidate_1_prep(
            source_database_path=database,
            expected_production_database_path=(
                expected
            ),
            wordpress_base_url=(
                "https://books.example.jp"
            ),
            output_root=(
                tmp_path / "wrong_path"
            ),
            normal_x_fb_root=normal_root,
        )
