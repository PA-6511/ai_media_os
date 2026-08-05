from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import EbookItem


ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_ROOT = (
    ROOT
    / "exchange"
    / "candidates"
    / "slack_worker_release_rebinding"
    / "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133"
    / "tst-5d-w2b-workflow-post-id-integrity"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


repository_module = _load_module(
    "tst_5d_w2b_repository_candidate",
    CANDIDATE_ROOT / "workflow_state_repository_candidate.py",
)

migration_module = _load_module(
    "tst_5d_w2b_migration_candidate",
    CANDIDATE_ROOT / "migration_candidate.py",
)


@pytest.fixture
def isolated_database(tmp_path):
    database_path = tmp_path / "w2b-candidate.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    try:
        yield engine, factory
    finally:
        engine.dispose()


def _item(
    source_item_id: str,
    *,
    post_id: str | None = None,
    workflow_status: str = "READY",
    wordpress_status: str = "NOT_CREATED",
) -> EbookItem:
    return EbookItem(
        source_name="tst-5d-w2b-candidate",
        source_item_id=source_item_id,
        title=f"W2B candidate {source_item_id}",
        item_type="tankobon",
        workflow_status=workflow_status,
        review_status="APPROVED",
        wordpress_status=wordpress_status,
        wordpress_post_id=post_id,
        publish_ready=False,
        is_excluded=False,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1"),
        (12345, "12345"),
        ("1", "1"),
        ("12345", "12345"),
        ("9" * 20, "9" * 20),
    ],
)
def test_candidate_accepts_approved_contract_values(
    isolated_database,
    value,
    expected,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item(f"VALID-{expected}")
        session.add(item)
        session.commit()

        changed = repository_module.WorkflowStateRepository(
            session
        ).set_wordpress_post_id(
            item,
            value,
            changed_by="human:test",
        )
        session.commit()

        assert changed is True
        assert item.wordpress_post_id == expected


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        0,
        -1,
        "",
        " ",
        " 1",
        "1 ",
        "+1",
        "-1",
        "1.0",
        "abc",
        "０１２３",
        "00123",
        "9" * 21,
        1.5,
    ],
)
def test_candidate_rejects_invalid_contract_values(
    isolated_database,
    value,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item("INVALID")
        session.add(item)
        session.commit()

        with pytest.raises(
            repository_module.WorkflowStateRepositoryError
        ):
            repository_module.WorkflowStateRepository(
                session
            ).set_wordpress_post_id(
                item,
                value,
                changed_by="human:test",
            )

        session.rollback()
        session.refresh(item)
        assert item.wordpress_post_id is None


def test_candidate_same_binding_is_idempotent(
    isolated_database,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item("IDEMPOTENT", post_id="12345")
        session.add(item)
        session.commit()

        checked_at = item.last_checked_at
        wordpress_updated_at = item.wordpress_updated_at

        changed = repository_module.WorkflowStateRepository(
            session
        ).set_wordpress_post_id(
            item,
            "12345",
            changed_by="human:test",
        )

        assert changed is False
        assert item.last_checked_at == checked_at
        assert item.wordpress_updated_at == wordpress_updated_at


def test_candidate_rejects_cross_workflow_duplicate(
    isolated_database,
):
    _, factory = isolated_database

    with factory() as session:
        item_a = _item("DUP-A", post_id="12345")
        item_b = _item("DUP-B")
        session.add_all([item_a, item_b])
        session.commit()

        with pytest.raises(
            repository_module.WordPressPostIdAlreadyBoundError
        ):
            repository_module.WorkflowStateRepository(
                session
            ).set_wordpress_post_id(
                item_b,
                "12345",
                changed_by="human:test",
            )

        session.rollback()
        session.refresh(item_b)
        assert item_b.wordpress_post_id is None


@pytest.mark.parametrize("replacement", ["200", None])
def test_candidate_rejects_rebinding_and_clearing(
    isolated_database,
    replacement,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item("BOUND", post_id="100")
        session.add(item)
        session.commit()

        with pytest.raises(
            repository_module.WordPressPostIdRebindForbiddenError
        ):
            repository_module.WorkflowStateRepository(
                session
            ).set_wordpress_post_id(
                item,
                replacement,
                changed_by="human:test",
            )

        session.rollback()
        session.refresh(item)
        assert item.wordpress_post_id == "100"


def test_candidate_rejects_published_rebinding(
    isolated_database,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item(
            "PUBLISHED",
            post_id="100",
            workflow_status="PUBLISHED",
            wordpress_status="PUBLISHED",
        )
        session.add(item)
        session.commit()

        with pytest.raises(
            repository_module.WordPressPostIdRebindForbiddenError
        ):
            repository_module.WorkflowStateRepository(
                session
            ).set_wordpress_post_id(
                item,
                "200",
                changed_by="human:test",
            )

        session.rollback()
        session.refresh(item)
        assert item.wordpress_post_id == "100"


def test_candidate_migration_accepts_valid_rows_and_nulls(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add_all(
            [
                _item("NULL-A"),
                _item("NULL-B"),
                _item("VALID-A", post_id="123"),
                _item("VALID-B", post_id="456"),
            ]
        )
        session.commit()

    with engine.begin() as connection:
        migration_module.upgrade(connection)

        indexes = connection.exec_driver_sql(
            "PRAGMA index_list('ebook_items')"
        ).all()

    assert migration_module.UNIQUE_INDEX_NAME in {
        row[1] for row in indexes
    }


def test_candidate_migration_rejects_duplicate_rows(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add_all(
            [
                _item("DUP-MIG-A", post_id="777"),
                _item("DUP-MIG-B", post_id="777"),
            ]
        )
        session.commit()

    with engine.begin() as connection:
        with pytest.raises(
            migration_module.WordPressPostIdMigrationPreflightError
        ):
            migration_module.upgrade(connection)


@pytest.mark.parametrize(
    "invalid_value",
    [
        "00123",
        "9" * 21,
        "１２３",
        "123 ",
        " 123",
        "abc",
    ],
)
def test_candidate_migration_rejects_invalid_rows(
    isolated_database,
    invalid_value,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(
            _item(
                f"INVALID-MIG-{len(invalid_value)}",
                post_id=invalid_value,
            )
        )
        session.commit()

    with engine.begin() as connection:
        with pytest.raises(
            migration_module.WordPressPostIdMigrationPreflightError
        ):
            migration_module.upgrade(connection)


def test_candidate_unique_index_rejects_late_duplicate(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(_item("INDEX-A", post_id="888"))
        session.commit()

    with engine.begin() as connection:
        migration_module.upgrade(connection)

    with factory() as session:
        session.add(_item("INDEX-B", post_id="888"))

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_candidate_migration_downgrade_removes_index(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(_item("DOWNGRADE", post_id="999"))
        session.commit()

    with engine.begin() as connection:
        migration_module.upgrade(connection)
        migration_module.downgrade(connection)

        indexes = connection.exec_driver_sql(
            "PRAGMA index_list('ebook_items')"
        ).all()

    assert migration_module.UNIQUE_INDEX_NAME not in {
        row[1] for row in indexes
    }


def test_candidate_production_source_is_not_imported():
    assert (
        repository_module.__file__
        and "exchange/candidates" in repository_module.__file__
    )


def test_candidate_migration_uses_no_production_database_path():
    source = (
        CANDIDATE_ROOT / "migration_candidate.py"
    ).read_text(encoding="utf-8")

    assert "data/database/ebook_affiliate.db" not in source
    assert "/home/deploy/ai_media_os/data" not in source
