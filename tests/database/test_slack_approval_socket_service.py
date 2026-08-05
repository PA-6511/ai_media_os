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
    encode_slack_approval_action,
)
from app.services.slack_approval_socket_service import (
    SlackApprovalInteraction,
    SlackApprovalSocketConfig,
    SlackApprovalSocketError,
    SlackApprovalSocketService,
    parse_slack_approval_interaction,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalService,
)


def create_session(tmp_path) -> Session:
    database_path = (
        tmp_path / "slack_socket.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}"
    )

    Base.metadata.create_all(engine)

    return Session(engine)


def config_values(
    *,
    mode: str = "DRY_RUN",
    live_confirm: str = "",
) -> dict[str, str]:
    return {
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "SLACK_APP_TOKEN": "xapp-test-token",
        "SLACK_APPROVAL_TEAM_ID": "T123",
        "SLACK_APPROVAL_CHANNEL_ID": "C123",
        "SLACK_APPROVER_USER_IDS": "U123,U456",
        "SLACK_APPROVAL_MODE": mode,
        "SLACK_APPROVAL_LIVE_CONFIRM": (
            live_confirm
        ),
    }


def create_bound_ticket(
    session: Session,
    *,
    source_item_id: str,
):
    item = EbookItem(
        source_name="pytest",
        source_item_id=source_item_id,
        title=f"Socket Approval {source_item_id}",
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

    request = session.get(
        WorkflowApprovalRequest,
        ticket.request_id,
    )

    assert request is not None

    request.slack_team_id = "T123"
    request.slack_channel_id = "C123"
    request.slack_message_ts = (
        "1720000000.000100"
    )

    session.commit()

    return item, ticket


def interaction_for(
    *,
    request_id: str,
    token: str,
    decision: str = "APPROVE",
    action_id: str = (
        "ebook_approval_approve"
    ),
    team_id: str = "T123",
    channel_id: str = "C123",
    user_id: str = "U123",
    message_ts: str = (
        "1720000000.000100"
    ),
) -> SlackApprovalInteraction:
    return SlackApprovalInteraction(
        team_id=team_id,
        channel_id=channel_id,
        user_id=user_id,
        message_ts=message_ts,
        action_id=action_id,
        action_value=(
            encode_slack_approval_action(
                request_id=request_id,
                token=token,
                decision=decision,
            )
        ),
    )


def test_config_does_not_expose_tokens() -> None:
    config = (
        SlackApprovalSocketConfig.from_mapping(
            config_values()
        )
    )

    representation = repr(config)

    assert "xoxb-test-token" not in representation
    assert "xapp-test-token" not in representation
    assert config.mode == "DRY_RUN"


def test_live_mode_requires_confirmation() -> None:
    with pytest.raises(
        SlackApprovalSocketError
    ) as error:
        SlackApprovalSocketConfig.from_mapping(
            config_values(mode="LIVE")
        )

    assert (
        error.value.code
        == "live_not_confirmed"
    )


def test_parse_slack_interaction() -> None:
    value = encode_slack_approval_action(
        request_id="request-001",
        token="token-001",
        decision="APPROVE",
    )

    interaction = (
        parse_slack_approval_interaction(
            {
                "team": {"id": "T123"},
                "channel": {"id": "C123"},
                "user": {"id": "U123"},
                "container": {
                    "message_ts": (
                        "1720000000.000100"
                    )
                },
                "actions": [
                    {
                        "action_id": (
                            "ebook_approval_approve"
                        ),
                        "value": value,
                    }
                ],
            }
        )
    )

    assert interaction.team_id == "T123"
    assert interaction.channel_id == "C123"
    assert interaction.user_id == "U123"
    assert (
        interaction.message_ts
        == "1720000000.000100"
    )


def test_dry_run_does_not_mutate_database(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item, ticket = create_bound_ticket(
            session,
            source_item_id="SOCKET-001",
        )

        config = (
            SlackApprovalSocketConfig.from_mapping(
                config_values()
            )
        )

        result = SlackApprovalSocketService(
            session,
            config,
        ).process_interaction(
            interaction_for(
                request_id=ticket.request_id,
                token=ticket.token,
            )
        )

        session.expire_all()

        refreshed_item = session.get(
            EbookItem,
            item.id,
        )

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        assert result.dry_run is True
        assert result.code == "dry_run_no_mutation"
        assert (
            refreshed_item.workflow_status
            == "REVIEW"
        )
        assert request.status == "PENDING"


def test_unauthorized_user_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_bound_ticket(
            session,
            source_item_id="SOCKET-002",
        )

        config = (
            SlackApprovalSocketConfig.from_mapping(
                config_values()
            )
        )

        with pytest.raises(
            SlackApprovalSocketError
        ) as error:
            SlackApprovalSocketService(
                session,
                config,
            ).process_interaction(
                interaction_for(
                    request_id=ticket.request_id,
                    token=ticket.token,
                    user_id="U999",
                )
            )

        assert (
            error.value.code
            == "unauthorized_user"
        )


def test_message_binding_mismatch_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_bound_ticket(
            session,
            source_item_id="SOCKET-003",
        )

        config = (
            SlackApprovalSocketConfig.from_mapping(
                config_values()
            )
        )

        with pytest.raises(
            SlackApprovalSocketError
        ) as error:
            SlackApprovalSocketService(
                session,
                config,
            ).process_interaction(
                interaction_for(
                    request_id=ticket.request_id,
                    token=ticket.token,
                    message_ts=(
                        "1720000000.999999"
                    ),
                )
            )

        assert (
            error.value.code
            == "message_binding_mismatch"
        )


def test_action_decision_mismatch_is_rejected(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        _, ticket = create_bound_ticket(
            session,
            source_item_id="SOCKET-004",
        )

        config = (
            SlackApprovalSocketConfig.from_mapping(
                config_values()
            )
        )

        with pytest.raises(
            SlackApprovalSocketError
        ) as error:
            SlackApprovalSocketService(
                session,
                config,
            ).process_interaction(
                interaction_for(
                    request_id=ticket.request_id,
                    token=ticket.token,
                    decision="HOLD",
                    action_id=(
                        "ebook_approval_approve"
                    ),
                )
            )

        assert (
            error.value.code
            == "decision_mismatch"
        )


def test_live_approve_updates_database(
    tmp_path,
) -> None:
    with create_session(tmp_path) as session:
        item, ticket = create_bound_ticket(
            session,
            source_item_id="SOCKET-005",
        )

        config = (
            SlackApprovalSocketConfig.from_mapping(
                config_values(
                    mode="LIVE",
                    live_confirm=(
                        "I_UNDERSTAND_DB_WRITES"
                    ),
                )
            )
        )

        result = SlackApprovalSocketService(
            session,
            config,
        ).process_interaction(
            interaction_for(
                request_id=ticket.request_id,
                token=ticket.token,
            )
        )

        session.expire_all()

        refreshed_item = session.get(
            EbookItem,
            item.id,
        )

        request = session.get(
            WorkflowApprovalRequest,
            ticket.request_id,
        )

        serialized_payload = json.dumps(
            result.update_payload,
            ensure_ascii=False,
        )

        assert result.dry_run is False
        assert result.code == "decision_applied"
        assert (
            refreshed_item.workflow_status
            == "READY"
        )
        assert request.status == "APPROVED"
        assert ticket.token not in serialized_payload
        assert "承認済み" in serialized_payload
