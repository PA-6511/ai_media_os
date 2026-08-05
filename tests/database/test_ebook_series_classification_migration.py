from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC = ROOT / ".venv" / "bin" / "alembic"
REVISION = "f6c8d2a4b1e9"
PREVIOUS_REVISION = "e4b7c9d2a6f1"


def _run_alembic(database_path: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "PYTHONPATH": str(ROOT),
        }
    )
    subprocess.run(
        [str(ALEMBIC), *arguments],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_existing_row_upgrade_unique_rule_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "classification-migration.db"
    _run_alembic(database_path, "upgrade", PREVIOUS_REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ebook_items "
                "(id, source_name, source_item_id, title, item_type, "
                "workflow_status, wordpress_status, x_status, affiliate_status, "
                "image_status, review_status, publish_ready, is_excluded, "
                "created_at, updated_at) VALUES "
                "('item-1', 'test', 'source-1', '作品 第1巻', 'tankobon', "
                "'NEW', 'NOT_CREATED', 'NOT_CREATED', 'UNCHECKED', 'UNCHECKED', "
                "'NOT_REVIEWED', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()

    _run_alembic(database_path, "upgrade", REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        columns = {
            column["name"]
            for column in inspector.get_columns("ebook_items")
        }
        assert {
            "is_single_episode",
            "is_split_edition",
            "classification_source",
        } <= columns
        assert "ebook_series_classification_rules" in inspector.get_table_names()
        indexes = {
            index["name"]: index
            for index in inspector.get_indexes(
                "ebook_series_classification_rules"
            )
        }
        assert indexes[
            "ux_ebook_series_classification_rules_series_key"
        ]["unique"] == 1
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT is_single_episode, is_split_edition, "
                    "classification_source FROM ebook_items WHERE id='item-1'"
                )
            ).one() == (None, None, None)
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == REVISION
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                values = {
                    "id": "rule-1",
                    "series_key": "same-key",
                    "source_item": "item-1",
                }
                statement = text(
                    "INSERT INTO ebook_series_classification_rules "
                    "(id, series_key, normalized_base_title, "
                    "normalized_author_name, normalized_publisher_name, "
                    "is_single_episode, is_split_edition, source_ebook_item_id, "
                    "active, created_at, updated_at) VALUES "
                    "(:id, :series_key, '作品', '著者', '出版社', 1, 0, "
                    ":source_item, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
                connection.execute(statement, values)
                values["id"] = "rule-2"
                connection.execute(statement, values)
    finally:
        engine.dispose()

    _run_alembic(database_path, "downgrade", PREVIOUS_REVISION)
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        assert "ebook_series_classification_rules" not in inspector.get_table_names()
        columns = {
            column["name"]
            for column in inspector.get_columns("ebook_items")
        }
        assert "is_single_episode" not in columns
        assert "is_split_edition" not in columns
        assert "classification_source" not in columns
    finally:
        engine.dispose()
