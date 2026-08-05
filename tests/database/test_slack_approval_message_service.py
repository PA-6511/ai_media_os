from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.services.slack_approval_message_service import (
    SlackApprovalMessageError,
    SlackApprovalMessageService,
    decode_slack_approval_action,
    encode_slack_approval_action,
    redact_slack_approval_message,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalService,
)


def create_session(tmp_path) -> Session:
    database_path = (
        tmp_path / "slack_approval_message.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    Base.metadata.create_all(engine)

    return Session(engine)


def create_ticket(
    session: Session,
    *,
    source_item_id: str,
):
    item = EbookItem(
        source_name="pytest",
        source_item_id=source_item_id,
        title=f"Slack Approval {source_item_id}",
        item_type="tankobon",
        workflow_status="REVIEW",
        wordpress_status="DRAFT",
        x_status="DRAFT",
        affiliate_status="READY",
        image_status="READY",
        publish_ready=True,
    )

    session.add(item)
    session.commit()
    session.refresh(item)

    ticket = WorkflowApprovalService(
        session
    ).create_request(
        item_id=item.id,
        approval_type="REVIEW_READY",
        requested_by="block:ebook",
    )

    return item, ticket


def action_elements(payload: dict) -> list[dict]:
    return next(
        block["elements"]
        for block in payload["blocks"]
        if block["type"] == "actions"
    )


def test_action_value_round_trip() -> None:
    encoded = encode_slack_approval_action(
        request_id="request-001",
        token="secret-token",
        decision="APPROVE",
    )

    decoded = decode_slack_approval_action(
        encoded
    )

    assert decoded.request_id == "request-001"
    assert decoded.token == "secret-token"
    assert decoded.decision == "APPROVE"


def test_build_message_contains_three_decisions(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-001",
        )

        payload = SlackApprovalMessageService(
            session
        ).build_message(
            request_id=ticket.request_id,
            token=ticket.token,
        )

        elements = action_elements(payload)

        action_ids = {
            element["action_id"]
            for element in elements
        }

        decisions = {
            decode_slack_approval_action(
                element["value"]
            ).decision
            for element in elements
            if "value" in element
        }

        assert payload["text"]
        assert len(payload["blocks"]) <= 50
        assert action_ids == {
            "ebook_approval_approve",
            "ebook_approval_reject",
            "ebook_approval_hold",
        }
        assert decisions == {
            "APPROVE",
            "REJECT",
            "HOLD",
        }

        assert all(
            "confirm" in element
            for element in elements
        )


def test_redacted_message_contains_no_raw_token(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-002",
        )

        payload = SlackApprovalMessageService(
            session
        ).build_message(
            request_id=ticket.request_id,
            token=ticket.token,
        )

        redacted = redact_slack_approval_message(
            payload
        )

        raw_json = json.dumps(
            payload,
            ensure_ascii=False,
        )

        redacted_json = json.dumps(
            redacted,
            ensure_ascii=False,
        )

        assert ticket.token in raw_json
        assert ticket.token not in redacted_json
        assert "[REDACTED]" in redacted_json


def test_invalid_token_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-003",
        )

        with pytest.raises(
            SlackApprovalMessageError
        ) as error:
            SlackApprovalMessageService(
                session
            ).build_message(
                request_id=ticket.request_id,
                token="invalid-token",
            )

        assert error.value.code == "invalid_token"


def test_stale_workflow_state_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item, ticket = create_ticket(
            session,
            source_item_id="SLACK-004",
        )

        item.workflow_status = "HOLD"
        session.commit()

        with pytest.raises(
            SlackApprovalMessageError
        ) as error:
            SlackApprovalMessageService(
                session
            ).build_message(
                request_id=ticket.request_id,
                token=ticket.token,
            )

        assert (
            error.value.code
            == "stale_workflow_state"
        )


def test_non_pending_request_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-005",
        )

        WorkflowApprovalService(
            session
        ).decide_request(
            request_id=ticket.request_id,
            token=ticket.token,
            decision="REJECT",
            decided_by="human:pytest",
        )

        with pytest.raises(
            SlackApprovalMessageError
        ) as error:
            SlackApprovalMessageService(
                session
            ).build_message(
                request_id=ticket.request_id,
                token=ticket.token,
            )

        assert (
            error.value.code
            == "request_not_pending"
        )


def test_register_sent_message_persists_binding(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-006",
        )

        result = SlackApprovalMessageService(
            session
        ).register_sent_message(
            request_id=ticket.request_id,
            team_id="T123",
            channel_id="C123",
            message_ts="1720000000.000100",
        )

        session.expire_all()

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert result.created is True
        assert request is not None
        assert request.slack_team_id == "T123"
        assert request.slack_channel_id == "C123"
        assert (
            request.slack_message_ts
            == "1720000000.000100"
        )


def test_same_binding_is_idempotent_but_rebind_fails(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-007",
        )

        service = SlackApprovalMessageService(
            session
        )

        first = service.register_sent_message(
            request_id=ticket.request_id,
            team_id="T123",
            channel_id="C123",
            message_ts="1720000000.000200",
        )

        second = service.register_sent_message(
            request_id=ticket.request_id,
            team_id="T123",
            channel_id="C123",
            message_ts="1720000000.000200",
        )

        assert first.created is True
        assert second.created is False

        with pytest.raises(
            SlackApprovalMessageError
        ) as error:
            service.register_sent_message(
                request_id=ticket.request_id,
                team_id="T123",
                channel_id="C999",
                message_ts="1720000000.000300",
            )

        assert (
            error.value.code
            == "message_binding_failed"
        )


def test_optional_https_gui_button(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_ticket(
            session,
            source_item_id="SLACK-008",
        )

        service = SlackApprovalMessageService(
            session
        )

        payload = service.build_message(
            request_id=ticket.request_id,
            token=ticket.token,
            gui_url=(
                "https://example.invalid/"
                "database-search"
            ),
        )

        elements = action_elements(payload)

        gui_button = next(
            element
            for element in elements
            if element["action_id"]
            == "ebook_approval_open_gui"
        )

        assert gui_button["url"].startswith(
            "https://"
        )

        with pytest.raises(
            SlackApprovalMessageError
        ) as error:
            service.build_message(
                request_id=ticket.request_id,
                token=ticket.token,
                gui_url=(
                    "http://127.0.0.1:8766/"
                    "database-search"
                ),
            )

        assert error.value.code == "invalid_gui_url"
