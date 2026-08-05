from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)


def create_session(tmp_path):
    database_path = tmp_path / "approval_schema.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_workflow_approval_table_columns(tmp_path) -> None:
    engine, session = create_session(tmp_path)

    try:
        columns = {
            column["name"]
            for column in inspect(engine).get_columns(
                "workflow_approval_requests"
            )
        }

        expected = {
            "id",
            "ebook_item_id",
            "approval_type",
            "expected_current_status",
            "requested_status",
            "status",
            "request_nonce_hash",
            "requested_by",
            "requested_at",
            "expires_at",
            "decided_by",
            "decided_at",
            "decision_note",
            "slack_team_id",
            "slack_channel_id",
            "slack_message_ts",
            "created_at",
            "updated_at",
        }

        assert expected <= columns
    finally:
        session.close()


def test_workflow_approval_default_status(tmp_path) -> None:
    _, session = create_session(tmp_path)

    try:
        item = EbookItem(
            source_name="pytest",
            source_item_id="APPROVAL-SCHEMA-001",
            title="Approval Schema Test",
            item_type="tankobon",
            workflow_status="REVIEW",
        )

        session.add(item)
        session.flush()

        now = datetime.now(timezone.utc)

        request = WorkflowApprovalRequest(
            ebook_item_id=item.id,
            approval_type="REVIEW_READY",
            expected_current_status="REVIEW",
            requested_status="READY",
            request_nonce_hash="a" * 64,
            requested_by="pytest",
            requested_at=now,
            expires_at=now + timedelta(hours=1),
        )

        session.add(request)
        session.commit()
        session.refresh(request)

        assert request.status == "PENDING"
    finally:
        session.close()
