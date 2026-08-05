from __future__ import annotations

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory


def create_session(tmp_path):
    database_path = tmp_path / "workflow_schema.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_workflow_columns_exist(tmp_path) -> None:
    engine, session = create_session(tmp_path)

    try:
        columns = {
            column["name"]
            for column in inspect(engine).get_columns("ebook_items")
        }

        expected = {
            "workflow_status",
            "wordpress_status",
            "wordpress_post_id",
            "wordpress_updated_at",
            "x_status",
            "x_post_id",
            "affiliate_status",
            "image_status",
            "review_status",
            "publish_ready",
            "last_error",
            "last_checked_at",
        }

        assert expected <= columns
    finally:
        session.close()


def test_workflow_defaults(tmp_path) -> None:
    _, session = create_session(tmp_path)

    try:
        item = EbookItem(
            source_name="test",
            source_item_id="WORKFLOW-001",
            title="Workflow Test",
            item_type="tankobon",
        )

        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.workflow_status == "NEW"
        assert item.wordpress_status == "NOT_CREATED"
        assert item.x_status == "NOT_CREATED"
        assert item.affiliate_status == "UNCHECKED"
        assert item.image_status == "UNCHECKED"
        assert item.review_status == "NOT_REVIEWED"
        assert item.publish_ready is False
    finally:
        session.close()


def test_workflow_history_relationship(tmp_path) -> None:
    _, session = create_session(tmp_path)

    try:
        item = EbookItem(
            source_name="test",
            source_item_id="WORKFLOW-002",
            title="History Test",
            item_type="tankobon",
        )

        item.workflow_history.append(
            WorkflowHistory(
                field_name="workflow_status",
                before_value="NEW",
                after_value="REVIEW",
                changed_by="human:test",
                note="review started",
            )
        )

        session.add(item)
        session.commit()

        histories = session.scalars(
            select(WorkflowHistory)
        ).all()

        assert len(histories) == 1
        assert histories[0].after_value == "REVIEW"
        assert histories[0].changed_by == "human:test"
    finally:
        session.close()
