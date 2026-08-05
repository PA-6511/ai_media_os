from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)


def create_session(tmp_path) -> Session:
    database_path = tmp_path / "workflow_state.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_item(session: Session) -> EbookItem:
    item = EbookItem(
        source_name="pytest",
        source_item_id="STATE-001",
        title="Workflow State Test",
        item_type="tankobon",
    )

    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_wordpress_status_records_history(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session)
        repository = WorkflowStateRepository(session)

        changed = repository.set_wordpress_status(
            item,
            "DRAFT",
            changed_by="pytest",
            note="WP draft created",
        )

        session.commit()
        session.refresh(item)

        history = session.scalars(
            select(WorkflowHistory).where(
                WorkflowHistory.field_name
                == "wordpress_status"
            )
        ).one()

        assert changed is True
        assert item.wordpress_status == "DRAFT"
        assert item.wordpress_updated_at is not None
        assert history.before_value == "NOT_CREATED"
        assert history.after_value == "DRAFT"


def test_review_and_publish_ready_updates(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session)
        repository = WorkflowStateRepository(session)

        repository.set_review_status(
            item,
            "APPROVED",
            changed_by="pytest",
        )

        repository.set_publish_ready(
            item,
            True,
            changed_by="pytest",
        )

        session.commit()
        session.refresh(item)

        assert item.review_status == "APPROVED"
        assert item.publish_ready is True


def test_invalid_enum_value_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session)
        repository = WorkflowStateRepository(session)

        with pytest.raises(ValueError):
            repository.set_x_status(
                item,
                "INVALID",
                changed_by="pytest",
            )


def test_same_value_does_not_create_history(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session)
        repository = WorkflowStateRepository(session)

        changed = repository.set_x_status(
            item,
            "NOT_CREATED",
            changed_by="pytest",
        )

        session.commit()

        histories = session.scalars(
            select(WorkflowHistory)
        ).all()

        assert changed is False
        assert histories == []


def test_last_error_can_be_set_and_cleared(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session)
        repository = WorkflowStateRepository(session)

        repository.set_last_error(
            item,
            "temporary failure",
            changed_by="pytest",
        )

        repository.set_last_error(
            item,
            None,
            changed_by="pytest",
        )

        session.commit()
        session.refresh(item)

        assert item.last_error is None

        histories = session.scalars(
            select(WorkflowHistory).where(
                WorkflowHistory.field_name
                == "last_error"
            )
        ).all()

        assert len(histories) == 2
