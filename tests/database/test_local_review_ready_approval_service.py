from __future__ import annotations

from datetime import datetime, timedelta, timezone
import socket
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
    WorkflowHistory,
)
from app.services.local_review_ready_approval_service import (
    LocalReviewReadyApprovalError,
    LocalReviewReadyApprovalService,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalService,
)


def create_session(tmp_path) -> Session:
    database_path = tmp_path / "local_review_ready.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_item(
    session: Session,
    source_item_id: str,
    *,
    workflow_status: str = "REVIEW",
    review_status: str = "NOT_REVIEWED",
    is_excluded: bool = False,
) -> EbookItem:
    item = EbookItem(
        source_name="pytest",
        source_item_id=source_item_id,
        title=f"Approval {source_item_id}",
        item_type="tankobon",
        workflow_status=workflow_status,
        review_status=review_status,
        is_excluded=is_excluded,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def create_request(
    session: Session,
    item: EbookItem,
):
    return LocalReviewReadyApprovalService(
        session
    ).create_request(
        ebook_item_id=item.id,
        requested_by="human:pytest",
        ttl_minutes=60,
    ).ticket


def test_create_request_uses_formal_service_and_sets_pending(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-001")

        with patch.object(
            socket.socket,
            "connect",
            side_effect=AssertionError("network attempted"),
        ):
            ticket = create_request(session, item)

        session.refresh(item)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert request is not None
        assert request.ebook_item_id == item.id
        assert request.approval_type == "REVIEW_READY"
        assert request.expected_current_status == "REVIEW"
        assert request.requested_status == "READY"
        assert request.status == "PENDING"
        assert request.expires_at is not None
        assert request.request_nonce_hash != ticket.token
        assert ticket.token not in repr(request)
        assert item.workflow_status == "REVIEW"
        assert item.review_status == "IN_REVIEW"


def test_duplicate_pending_request_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-002")
        create_request(session, item)

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            create_request(session, item)

        assert error.value.code == "duplicate_pending"


def test_excluded_item_request_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            "LOCAL-003",
            is_excluded=True,
        )

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            create_request(session, item)

        assert error.value.code == "excluded_item"
        assert session.scalars(
            select(WorkflowApprovalRequest)
        ).all() == []


def test_approve_updates_request_review_and_workflow(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-004")
        ticket = create_request(session, item)

        with patch.object(
            socket.socket,
            "connect",
            side_effect=AssertionError("network attempted"),
        ):
            result = LocalReviewReadyApprovalService(
                session
            ).decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
                decided_by="human:pytest",
                note="Approved locally",
            )

        session.expire_all()
        refreshed = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )
        fields = {
            history.field_name
            for history in session.scalars(
                select(WorkflowHistory).where(
                    WorkflowHistory.ebook_item_id == item.id
                )
            )
        }

        assert result.request_status == "APPROVED"
        assert request is not None
        assert request.status == "APPROVED"
        assert request.decided_at is not None
        assert refreshed is not None
        assert refreshed.review_status == "APPROVED"
        assert refreshed.workflow_status == "READY"
        assert refreshed.publish_ready is False
        assert refreshed.wordpress_status == "NOT_CREATED"
        assert refreshed.x_status == "NOT_CREATED"
        assert {"review_status", "workflow_status"} <= fields


def test_approve_is_atomic_when_commit_fails(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-005")
        ticket = create_request(session, item)

        with patch.object(
            session,
            "commit",
            side_effect=RuntimeError("forced commit failure"),
        ):
            with pytest.raises(RuntimeError):
                LocalReviewReadyApprovalService(
                    session
                ).decide_request(
                    ebook_item_id=item.id,
                    approval_request_id=ticket.request_id,
                    token=ticket.token,
                    decision="APPROVE",
                )

        session.expire_all()
        refreshed = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert refreshed is not None
        assert refreshed.workflow_status == "REVIEW"
        assert refreshed.review_status == "IN_REVIEW"
        assert request is not None
        assert request.status == "PENDING"


def test_reject_uses_existing_service_behavior(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-006")
        ticket = create_request(session, item)

        LocalReviewReadyApprovalService(session).decide_request(
            ebook_item_id=item.id,
            approval_request_id=ticket.request_id,
            token=ticket.token,
            decision="REJECT",
            note="Needs correction",
        )

        session.expire_all()
        refreshed = session.get(EbookItem, item.id)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert refreshed is not None
        assert refreshed.workflow_status == "REVIEW"
        assert refreshed.review_status == "REJECTED"
        assert request is not None
        assert request.status == "REJECTED"


def test_expired_request_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-007")
        ticket = create_request(session, item)
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )
        now = datetime.now(timezone.utc)
        request.requested_at = now - timedelta(minutes=2)
        request.expires_at = now - timedelta(minutes=1)
        session.commit()

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            LocalReviewReadyApprovalService(
                session
            ).decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
            )

        session.expire_all()
        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )
        assert error.value.code == "expired"
        assert request is not None
        assert request.status == "EXPIRED"


def test_request_id_cannot_be_reused_for_another_item(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-008-A")
        other = create_item(session, "LOCAL-008-B")
        ticket = create_request(session, item)

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            LocalReviewReadyApprovalService(
                session
            ).decide_request(
                ebook_item_id=other.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
            )

        assert error.value.code == "request_item_mismatch"


def test_invalid_decision_and_double_approve_are_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-009")
        ticket = create_request(session, item)
        service = LocalReviewReadyApprovalService(session)

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as invalid:
            service.decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="HOLD",
            )

        assert invalid.value.code == "invalid_decision"

        service.decide_request(
            ebook_item_id=item.id,
            approval_request_id=ticket.request_id,
            token=ticket.token,
            decision="APPROVE",
        )

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as duplicate:
            service.decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
            )

        assert duplicate.value.code == "already_decided"


def test_non_review_ready_request_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(
            session,
            "LOCAL-010",
            workflow_status="READY",
            review_status="IN_REVIEW",
        )
        ticket = WorkflowApprovalService(session).create_request(
            item_id=item.id,
            approval_type="PUBLISH_SCHEDULE",
            requested_by="human:pytest",
        )

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            LocalReviewReadyApprovalService(
                session
            ).decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
            )

        assert error.value.code == "invalid_approval_type"


def test_excluded_item_decision_is_rejected(tmp_path) -> None:
    with create_session(tmp_path) as session:
        item = create_item(session, "LOCAL-011")
        ticket = create_request(session, item)
        item.is_excluded = True
        session.commit()

        with pytest.raises(
            LocalReviewReadyApprovalError
        ) as error:
            LocalReviewReadyApprovalService(
                session
            ).decide_request(
                ebook_item_id=item.id,
                approval_request_id=ticket.request_id,
                token=ticket.token,
                decision="APPROVE",
            )

        assert error.value.code == "excluded_item"
