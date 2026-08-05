from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
    WorkflowHistory,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalError,
    WorkflowApprovalService,
)


def create_session(tmp_path) -> Session:
    database_path = tmp_path / "approval_service.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_item(
    session: Session,
    *,
    source_item_id: str,
    workflow_status: str,
) -> EbookItem:
    item = EbookItem(
        source_name="pytest",
        source_item_id=source_item_id,
        title=f"Approval Test {source_item_id}",
        item_type="tankobon",
        workflow_status=workflow_status,
    )

    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_create_request_stores_hash_not_raw_token(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-001",
            workflow_status="REVIEW",
        )

        ticket = WorkflowApprovalService(
            session
        ).create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        session.refresh(item)

        assert request is not None
        assert request.status == "PENDING"
        assert request.request_nonce_hash != ticket.token
        assert len(request.request_nonce_hash) == 64
        assert item.review_status == "IN_REVIEW"


def test_duplicate_pending_request_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-002",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        with pytest.raises(
            WorkflowApprovalError
        ) as error:
            service.create_request(
                item_id=item.id,
                approval_type="REVIEW_READY",
                requested_by="block:ebook",
            )

        assert error.value.code == "duplicate_pending"


def test_approve_request_updates_workflow_and_review(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-003",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        result = service.decide_request(
            request_id=ticket.request_id,
            token=ticket.token,
            decision="APPROVE",
            decided_by="human:pytest",
        )

        session.expire_all()

        refreshed_item = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        histories = session.scalars(
            select(WorkflowHistory).where(
                WorkflowHistory.ebook_item_id == item.id
            )
        ).all()

        assert result.request_status == "APPROVED"
        assert refreshed_item.workflow_status == "READY"
        assert refreshed_item.review_status == "APPROVED"
        assert request.status == "APPROVED"

        fields = {
            history.field_name
            for history in histories
        }

        assert "workflow_status" in fields
        assert "review_status" in fields


def test_invalid_token_does_not_decide_request(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-004",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        with pytest.raises(
            WorkflowApprovalError
        ) as error:
            service.decide_request(
                request_id=ticket.request_id,
                token="invalid-token",
                decision="APPROVE",
                decided_by="human:pytest",
            )

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert error.value.code == "invalid_token"
        assert request.status == "PENDING"


def test_expired_request_is_marked_expired(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-005",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        now = datetime.now(timezone.utc)

        request.requested_at = (
            now - timedelta(minutes=2)
        )
        request.expires_at = (
            now - timedelta(minutes=1)
        )

        session.commit()

        with pytest.raises(
            WorkflowApprovalError
        ) as error:
            service.decide_request(
                request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
                decided_by="human:pytest",
            )

        session.expire_all()

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert error.value.code == "expired"
        assert request.status == "EXPIRED"


def test_stale_workflow_state_marks_request_failed(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-006",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        item.workflow_status = "HOLD"
        session.commit()

        with pytest.raises(
            WorkflowApprovalError
        ) as error:
            service.decide_request(
                request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
                decided_by="human:pytest",
            )

        session.expire_all()

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert error.value.code == "stale_state"
        assert request.status == "FAILED"


def test_reject_request_sets_review_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-007",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        service.decide_request(
            request_id=ticket.request_id,
            token=ticket.token,
            decision="REJECT",
            decided_by="human:pytest",
            note="Needs correction",
        )

        session.expire_all()

        refreshed_item = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert refreshed_item.workflow_status == "REVIEW"
        assert refreshed_item.review_status == "REJECTED"
        assert request.status == "REJECTED"


def test_hold_request_moves_workflow_to_hold(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            source_item_id="APPROVAL-008",
            workflow_status="REVIEW",
        )

        service = WorkflowApprovalService(session)

        ticket = service.create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by="block:ebook",
        )

        service.decide_request(
            request_id=ticket.request_id,
            token=ticket.token,
            decision="HOLD",
            decided_by="human:pytest",
        )

        session.expire_all()

        refreshed_item = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert refreshed_item.workflow_status == "HOLD"
        assert request.status == "HELD"
