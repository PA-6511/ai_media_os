from __future__ import annotations

import importlib.util
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import EbookItem
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
    WorkflowStateRepositoryError,
    WordPressPostIdAlreadyBoundError,
    WordPressPostIdItemNotPersistedError,
    WordPressPostIdRebindForbiddenError,
    WordPressPostIdTooLongError,
    WordPressPostIdUniquenessConflictError,
)


ROOT = Path(__file__).resolve().parents[2]

MIGRATION_PATH = (
    ROOT
    / "migrations"
    / "versions"
    / "00241611109d_add_unique_wordpress_post_id.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "tst_5d_w2b_fix1_migration",
        MIGRATION_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration()


@pytest.fixture
def isolated_database(tmp_path):
    database_path = tmp_path / "w2b-fix1.db"
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
        source_name="tst-5d-w2b-fix1-integration",
        source_item_id=source_item_id,
        title=f"W2B FIX1 {source_item_id}",
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
def test_integrated_source_accepts_contract_values(
    isolated_database,
    value,
    expected,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item(f"VALID-{expected}")
        session.add(item)
        session.commit()

        changed = WorkflowStateRepository(
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
        "１２３",
        "00123",
        1.5,
    ],
)
def test_integrated_source_rejects_invalid_values_before_identity(
    value,
):
    repository = object.__new__(
        WorkflowStateRepository
    )

    with pytest.raises(
        WorkflowStateRepositoryError,
        match="positive integer",
    ):
        repository.set_wordpress_post_id(
            SimpleNamespace(
                wordpress_post_id=None
            ),
            value,
            changed_by="human:test",
        )


def test_integrated_source_rejects_over_20_digits():
    repository = object.__new__(
        WorkflowStateRepository
    )

    with pytest.raises(
        WordPressPostIdTooLongError
    ):
        repository.set_wordpress_post_id(
            SimpleNamespace(
                wordpress_post_id=None
            ),
            "9" * 21,
            changed_by="human:test",
        )


def test_integrated_source_requires_persisted_item():
    repository = object.__new__(
        WorkflowStateRepository
    )

    with pytest.raises(
        WordPressPostIdItemNotPersistedError
    ):
        repository.set_wordpress_post_id(
            SimpleNamespace(
                wordpress_post_id=None
            ),
            "321",
            changed_by="human:test",
        )


def test_integrated_source_duplicate_fails_closed(
    isolated_database,
):
    _, factory = isolated_database

    with factory() as session:
        item_a = _item("DUP-A", post_id="12345")
        item_b = _item("DUP-B")

        session.add_all([item_a, item_b])
        session.commit()

        with pytest.raises(
            WordPressPostIdAlreadyBoundError
        ):
            WorkflowStateRepository(
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
def test_integrated_source_rejects_rebind_and_clear(
    isolated_database,
    replacement,
):
    _, factory = isolated_database

    with factory() as session:
        item = _item("BOUND", post_id="100")
        session.add(item)
        session.commit()

        with pytest.raises(
            WordPressPostIdRebindForbiddenError
        ):
            WorkflowStateRepository(
                session
            ).set_wordpress_post_id(
                item,
                replacement,
                changed_by="human:test",
            )

        session.rollback()
        session.refresh(item)

        assert item.wordpress_post_id == "100"


def test_integrated_source_same_id_is_noop_without_identity():
    repository = object.__new__(
        WorkflowStateRepository
    )

    changed = repository.set_wordpress_post_id(
        SimpleNamespace(
            wordpress_post_id="321"
        ),
        "321",
        changed_by="human:test",
    )

    assert changed is False


def test_integrated_source_maps_integrity_error():
    class FailingSession:
        no_autoflush = nullcontext()

        @staticmethod
        def scalar(_statement):
            return None

        @staticmethod
        def flush():
            raise IntegrityError(
                "INSERT",
                {},
                RuntimeError("unique conflict"),
            )

    repository = object.__new__(
        WorkflowStateRepository
    )
    repository.session = FailingSession()

    item = SimpleNamespace(
        id="persisted-item",
        wordpress_post_id=None,
        last_checked_at=None,
        wordpress_updated_at=None,
    )

    with pytest.raises(
        WordPressPostIdUniquenessConflictError
    ):
        repository.set_wordpress_post_id(
            item,
            "555",
            changed_by="human:test",
        )


def test_migration_accepts_valid_rows_and_nulls(
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
        migration.apply_with_connection(connection)

        indexes = connection.exec_driver_sql(
            "PRAGMA index_list('ebook_items')"
        ).all()

    assert migration.INDEX_NAME in {
        row[1] for row in indexes
    }


def test_migration_rejects_duplicate_preimage(
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
            RuntimeError,
            match=migration.MIGRATION_PREFLIGHT_ERROR,
        ):
            migration.apply_with_connection(connection)


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
def test_migration_rejects_invalid_preimage(
    isolated_database,
    invalid_value,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(
            _item(
                f"INVALID-{len(invalid_value)}",
                post_id=invalid_value,
            )
        )
        session.commit()

    with engine.begin() as connection:
        with pytest.raises(
            RuntimeError,
            match=migration.MIGRATION_PREFLIGHT_ERROR,
        ):
            migration.apply_with_connection(connection)


def test_unique_index_rejects_late_duplicate(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(_item("INDEX-A", post_id="888"))
        session.commit()

    with engine.begin() as connection:
        migration.apply_with_connection(connection)

    with factory() as session:
        session.add(_item("INDEX-B", post_id="888"))

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_migration_downgrade_helper(
    isolated_database,
):
    engine, factory = isolated_database

    with factory() as session:
        session.add(_item("DOWNGRADE", post_id="999"))
        session.commit()

    with engine.begin() as connection:
        migration.apply_with_connection(connection)
        migration.remove_with_connection(connection)

        indexes = connection.exec_driver_sql(
            "PRAGMA index_list('ebook_items')"
        ).all()

    assert migration.INDEX_NAME not in {
        row[1] for row in indexes
    }
