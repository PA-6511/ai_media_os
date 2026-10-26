from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
from sqlalchemy import DateTime, Integer, String, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC = ROOT / ".venv/bin/alembic"
PARENT_REVISION = "b17e4c9a2d60"
TARGET_REVISION = "d2e7c4a91b30"
TABLE = "amazon_x_tracking_id_pool"
EXPERIMENT_A = "a" * 64
VARIANT_A = "b" * 64


def run_alembic(database: Path, *arguments: str) -> None:
    environment = {
        **os.environ,
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": f"sqlite:///{database}",
        "PYTHONPATH": str(ROOT),
        "AI_MEDIA_OS_TESTING": "1",
    }
    result = subprocess.run(
        [str(ALEMBIC), *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def revision(connection) -> str:
    return connection.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one()


def insert_available(connection, *, row_id: str, tracking_id: str) -> None:
    connection.execute(
        text(
            f"INSERT INTO {TABLE} "
            "(id,tracking_id,status,registered_at) VALUES "
            "(:id,:tracking_id,'AVAILABLE',:registered_at)"
        ),
        {
            "id": row_id,
            "tracking_id": tracking_id,
            "registered_at": "2026-10-12 00:00:00+00:00",
        },
    )


def test_upgrade_contract_and_existing_schema_are_preserved(
    tmp_path: Path,
) -> None:
    database = tmp_path / "amazon-x-tracking-pool-schema.db"
    run_alembic(database, "upgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{database}")
    before = inspect(engine)
    representative_tables = {"ebook_items", "store_offers", "x_post_drafts"}
    assert representative_tables <= set(before.get_table_names())
    draft_columns_before = {
        column["name"] for column in before.get_columns("x_post_drafts")
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO x_post_drafts "
                "(id,source_type,source_id,generated_text,paid_partnership,"
                "status,created_at,updated_at) VALUES "
                "('migration-evidence','sale','migration-evidence','draft',"
                "1,'DRAFT','2026-10-12 00:00:00','2026-10-12 00:00:00')"
            )
        )
    engine.dispose()

    run_alembic(database, "upgrade", TARGET_REVISION)
    engine = create_engine(f"sqlite:///{database}")
    inspector = inspect(engine)
    assert inspector.has_table(TABLE)
    assert representative_tables <= set(inspector.get_table_names())
    assert {
        column["name"] for column in inspector.get_columns("x_post_drafts")
    } == draft_columns_before

    columns = {
        column["name"]: column for column in inspector.get_columns(TABLE)
    }
    assert set(columns) == {
        "id",
        "tracking_id",
        "status",
        "experiment_id",
        "variant_id",
        "wordpress_post_id",
        "registered_at",
        "assigned_at",
    }
    expected_types = {
        "id": (String, 36),
        "tracking_id": (String, 128),
        "status": (String, 16),
        "experiment_id": (String, 64),
        "variant_id": (String, 64),
        "wordpress_post_id": (Integer, None),
        "registered_at": (DateTime, None),
        "assigned_at": (DateTime, None),
    }
    for name, (type_class, length) in expected_types.items():
        assert isinstance(columns[name]["type"], type_class)
        if length is not None:
            assert columns[name]["type"].length == length
    assert {name: columns[name]["nullable"] for name in columns} == {
        "id": False,
        "tracking_id": False,
        "status": False,
        "experiment_id": True,
        "variant_id": True,
        "wordpress_post_id": True,
        "registered_at": False,
        "assigned_at": True,
    }
    assert inspector.get_pk_constraint(TABLE)["constrained_columns"] == ["id"]
    assert {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints(TABLE)
    } == {
        "uq_amazon_x_tracking_pool_tracking_id": ["tracking_id"],
        "uq_amazon_x_tracking_pool_variant_id": ["variant_id"],
    }
    assert {
        index["name"]: index["column_names"]
        for index in inspector.get_indexes(TABLE)
    } == {
        "ix_amazon_x_tracking_pool_experiment": ["experiment_id"],
        "ix_amazon_x_tracking_pool_status": ["status"],
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints(TABLE)
    } == {
        "ck_amazon_x_tracking_id_pool_"
        "ck_amazon_x_tracking_pool_tracking_id_not_blank",
        "ck_amazon_x_tracking_id_pool_ck_amazon_x_tracking_pool_status",
        "ck_amazon_x_tracking_id_pool_"
        "ck_amazon_x_tracking_pool_state_semantics",
    }
    with engine.connect() as connection:
        assert revision(connection) == TARGET_REVISION
        assert connection.execute(
            text(
                "SELECT generated_text FROM x_post_drafts "
                "WHERE id='migration-evidence'"
            )
        ).scalar_one() == "draft"
    engine.dispose()


def test_database_enforces_unique_and_lifecycle_constraints(
    tmp_path: Path,
) -> None:
    database = tmp_path / "amazon-x-tracking-pool-constraints.db"
    run_alembic(database, "upgrade", PARENT_REVISION)
    run_alembic(database, "upgrade", TARGET_REVISION)
    engine = create_engine(f"sqlite:///{database}")

    with engine.begin() as connection:
        insert_available(connection, row_id="available-1", tracking_id="x-sale-01")
        insert_available(connection, row_id="available-2", tracking_id="x-sale-02")
        connection.execute(
            text(
                f"INSERT INTO {TABLE} "
                "(id,tracking_id,status,experiment_id,variant_id,"
                "wordpress_post_id,registered_at,assigned_at) VALUES "
                "('assigned-1','x-sale-03','ASSIGNED',:experiment,:variant,"
                "3417,:registered_at,:assigned_at)"
            ),
            {
                "experiment": EXPERIMENT_A,
                "variant": VARIANT_A,
                "registered_at": "2026-10-12 00:00:00+00:00",
                "assigned_at": "2026-10-12 01:00:00+00:00",
            },
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            insert_available(
                connection,
                row_id="duplicate-tracking",
                tracking_id="x-sale-01",
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"INSERT INTO {TABLE} "
                    "(id,tracking_id,status,experiment_id,variant_id,"
                    "wordpress_post_id,registered_at,assigned_at) VALUES "
                    "('duplicate-variant','x-sale-04','ASSIGNED',:experiment,"
                    ":variant,3418,:registered_at,:assigned_at)"
                ),
                {
                    "experiment": EXPERIMENT_A,
                    "variant": VARIANT_A,
                    "registered_at": "2026-10-12 00:00:00+00:00",
                    "assigned_at": "2026-10-12 01:00:00+00:00",
                },
            )

    invalid_rows = (
        "('blank-tracking',' ','AVAILABLE',NULL,NULL,NULL,'2026-10-12',NULL)",
        "('bad-status','x-sale-05','UNKNOWN',NULL,NULL,NULL,'2026-10-12',NULL)",
        "('bad-state','x-sale-06','AVAILABLE',"
        f"'{EXPERIMENT_A}','{VARIANT_A}',3419,'2026-10-12','2026-10-12')",
    )
    for values in invalid_rows:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"INSERT INTO {TABLE} "
                        "(id,tracking_id,status,experiment_id,variant_id,"
                        "wordpress_post_id,registered_at,assigned_at) VALUES "
                        f"{values}"
                    )
                )

    with engine.connect() as connection:
        assert connection.execute(
            text(f"SELECT COUNT(*) FROM {TABLE} WHERE variant_id IS NULL")
        ).scalar_one() == 2
    engine.dispose()


def test_downgrade_removes_only_tracking_pool_schema(
    tmp_path: Path,
) -> None:
    database = tmp_path / "amazon-x-tracking-pool-downgrade.db"
    run_alembic(database, "upgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{database}")
    before_tables = set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO x_post_drafts "
                "(id,source_type,source_id,generated_text,paid_partnership,"
                "status,created_at,updated_at) VALUES "
                "('downgrade-evidence','sale','downgrade-evidence','draft',"
                "1,'DRAFT','2026-10-12 00:00:00','2026-10-12 00:00:00')"
            )
        )
    engine.dispose()

    run_alembic(database, "upgrade", TARGET_REVISION)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        insert_available(connection, row_id="discarded", tracking_id="x-sale-01")
    engine.dispose()

    run_alembic(database, "downgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{database}")
    inspector = inspect(engine)
    assert not inspector.has_table(TABLE)
    assert set(inspector.get_table_names()) == before_tables
    with engine.connect() as connection:
        assert revision(connection) == PARENT_REVISION
        assert connection.execute(
            text(
                "SELECT generated_text FROM x_post_drafts "
                "WHERE id='downgrade-evidence'"
            )
        ).scalar_one() == "draft"
    engine.dispose()
