from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory
from app.services.workflow_action_service import (
    WorkflowActionError,
    execute_workflow_action,
    get_workflow_action_token,
    safe_database_return_path,
)


def create_session(tmp_path) -> Session:
    database_path = tmp_path / "workflow_action.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_item(
    session: Session,
    *,
    source_item_id: str,
    workflow_status: str = "NEW",
) -> EbookItem:
    item = EbookItem(
        source_name="pytest",
        source_item_id=source_item_id,
        title=f"Workflow Test {source_item_id}",
        item_type="tankobon",
        workflow_status=workflow_status,
    )

    session.add(item)
    session.commit()
    session.refresh(item)

    return item


def test_execute_workflow_action_updates_and_records_history(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="ACTION-001",
        )

        result = execute_workflow_action(
            session,
            item_id=item.id,
            new_status="REVIEW",
            csrf_token=get_workflow_action_token(),
        )

        session.refresh(item)

        histories = session.scalars(
            select(WorkflowHistory)
        ).all()

        assert result.before_status == "NEW"
        assert result.after_status == "REVIEW"
        assert item.workflow_status == "REVIEW"
        assert len(histories) == 1
        assert histories[0].before_value == "NEW"
        assert histories[0].after_value == "REVIEW"
        assert histories[0].changed_by == "human:local_gui"


def test_invalid_token_is_rejected_without_change(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="ACTION-002",
        )

        with pytest.raises(WorkflowActionError) as error:
            execute_workflow_action(
                session,
                item_id=item.id,
                new_status="REVIEW",
                csrf_token="invalid-token",
            )

        session.refresh(item)

        assert error.value.code == "invalid_token"
        assert item.workflow_status == "NEW"


def test_invalid_gui_target_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="ACTION-003",
        )

        with pytest.raises(WorkflowActionError) as error:
            execute_workflow_action(
                session,
                item_id=item.id,
                new_status="ERROR",
                csrf_token=get_workflow_action_token(),
            )

        assert error.value.code == "invalid_target"


def test_illegal_transition_rolls_back(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="ACTION-004",
        )

        with pytest.raises(WorkflowActionError) as error:
            execute_workflow_action(
                session,
                item_id=item.id,
                new_status="PUBLISHED",
                csrf_token=get_workflow_action_token(),
            )

        session.refresh(item)

        histories = session.scalars(
            select(WorkflowHistory)
        ).all()

        assert error.value.code == "invalid_transition"
        assert item.workflow_status == "NEW"
        assert histories == []


def test_missing_item_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        with pytest.raises(WorkflowActionError) as error:
            execute_workflow_action(
                session,
                item_id="missing-item",
                new_status="REVIEW",
                csrf_token=get_workflow_action_token(),
            )

        assert error.value.code == "item_not_found"


def test_review_to_ready_requires_formal_approval(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="ACTION-REVIEW-READY-GUARD",
            workflow_status="REVIEW",
        )

        with pytest.raises(WorkflowActionError) as error:
            execute_workflow_action(
                session,
                item_id=item.id,
                new_status="READY",
                csrf_token=get_workflow_action_token(),
            )

        session.refresh(item)
        histories = session.scalars(
            select(WorkflowHistory).where(
                WorkflowHistory.ebook_item_id == item.id
            )
        ).all()

        assert (
            error.value.code
            == "REVIEW_READY_REQUIRES_APPROVAL"
        )
        assert item.workflow_status == "REVIEW"
        assert item.review_status == "NOT_REVIEWED"
        assert histories == []


def test_safe_database_return_path() -> None:
    assert (
        safe_database_return_path(
            "/database-search?keyword=test"
        )
        == "/database-search?keyword=test"
    )

    assert (
        safe_database_return_path(
            "https://example.com/database-search"
        )
        == "/database-search"
    )

    assert (
        safe_database_return_path("/other")
        == "/database-search"
    )
