from types import SimpleNamespace
from unittest.mock import patch

import pytest

from dev_agent.slack_proposal_approval_adapter import (
    DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID,
    SlackProposalApprovalError,
    approve_slack_proposal,
    build_slack_proposal_approval_message,
)


PROPOSAL_ID = (
    "proposal_v1_" + "a" * 64
)


def config(
    mode: str = "LIVE",
):
    return SimpleNamespace(
        bot_token="xoxb-test",
        app_token="xapp-test",
        team_id="T123",
        channel_id="C123",
        approver_user_ids=frozenset(
            {"U123"}
        ),
        mode=mode,
        live_confirmed=(
            mode == "LIVE"
        ),
    )


def interaction(
    *,
    user_id: str = "U123",
):
    return SimpleNamespace(
        team_id="T123",
        channel_id="C123",
        user_id=user_id,
        message_ts="123.456",
        action_id=(
            DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
        ),
        action_value=PROPOSAL_ID,
    )


def valid_proposal() -> dict:
    return {
        "status": "VALID",
        "proposal_id": PROPOSAL_ID,
        "relative_path": "allowed.py",
        "old_text": "old",
        "new_text": "new",
        "before_sha256": "b" * 64,
        "current_sha256": "b" * 64,
        "proposal_state": "PENDING",
    }


def test_message_button_value_is_only_proposal_id():
    with patch(
        "dev_agent.slack_proposal_approval_adapter."
        "load_write_proposal",
        return_value=valid_proposal(),
    ):
        payload = (
            build_slack_proposal_approval_message(
                PROPOSAL_ID
            )
        )

    button = (
        payload["blocks"][-1]
        ["elements"][0]
    )

    assert (
        button["action_id"]
        == DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
    )
    assert button["value"] == PROPOSAL_ID
    assert button["value"].startswith(
        "proposal_v1_"
    )
    assert "old" not in button["value"]
    assert "new" not in button["value"]


def test_dry_run_does_not_mark_approved():
    with (
        patch(
            "dev_agent.slack_proposal_approval_adapter."
            "load_write_proposal",
            return_value=valid_proposal(),
        ),
        patch(
            "dev_agent.slack_proposal_approval_adapter."
            "mark_proposal_approved"
        ) as mark,
    ):
        result = approve_slack_proposal(
            interaction=interaction(),
            config=config("DRY_RUN"),
        )

    assert result.dry_run is True
    assert result.proposal_state == "PENDING"
    mark.assert_not_called()


def test_live_marks_proposal_approved():
    with (
        patch(
            "dev_agent.slack_proposal_approval_adapter."
            "load_write_proposal",
            return_value=valid_proposal(),
        ),
        patch(
            "dev_agent.slack_proposal_approval_adapter."
            "mark_proposal_approved",
            return_value={
                "status": "VALID",
                "proposal_id": PROPOSAL_ID,
                "proposal_state": "APPROVED",
            },
        ) as mark,
    ):
        result = approve_slack_proposal(
            interaction=interaction(),
            config=config("LIVE"),
        )

    assert result.dry_run is False
    assert result.proposal_state == "APPROVED"

    mark.assert_called_once_with(
        PROPOSAL_ID
    )


def test_unauthorized_user_is_rejected_before_load():
    with patch(
        "dev_agent.slack_proposal_approval_adapter."
        "load_write_proposal"
    ) as load:
        with pytest.raises(
            SlackProposalApprovalError
        ) as exc:
            approve_slack_proposal(
                interaction=interaction(
                    user_id="U999"
                ),
                config=config("LIVE"),
            )

    assert exc.value.code == "unauthorized_user"
    load.assert_not_called()
