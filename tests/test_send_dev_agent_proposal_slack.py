from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.send_dev_agent_proposal_slack import (
    DevAgentProposalSlackSendError,
    send_dev_agent_proposal,
)


PROPOSAL_ID = (
    "proposal_v1_" + "a" * 64
)


def config(
    *,
    mode: str = "LIVE",
    confirmed: bool = True,
):
    return SimpleNamespace(
        bot_token="xoxb-test",
        team_id="T123",
        channel_id="C123",
        mode=mode,
        live_confirmed=confirmed,
    )


def pending_proposal():
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


def payload():
    return {
        "text": "approval",
        "blocks": [],
        "unfurl_links": False,
        "unfurl_media": False,
    }


def test_live_pending_proposal_is_sent():
    client = Mock()

    client.chat_postMessage.return_value = {
        "ok": True,
        "channel": "C123",
        "ts": "123.456",
    }

    with (
        patch(
            "scripts.send_dev_agent_proposal_slack."
            "load_write_proposal",
            return_value=pending_proposal(),
        ),
        patch(
            "scripts.send_dev_agent_proposal_slack."
            "build_slack_proposal_approval_message",
            return_value=payload(),
        ) as build,
    ):
        result = send_dev_agent_proposal(
            client=client,
            config=config(),
            proposal_id=PROPOSAL_ID,
        )

    assert result.proposal_id == PROPOSAL_ID
    assert result.proposal_state == "PENDING"
    assert result.channel_id == "C123"
    assert result.message_ts == "123.456"

    build.assert_called_once_with(
        PROPOSAL_ID
    )

    client.chat_postMessage.assert_called_once_with(
        channel="C123",
        **payload(),
    )


def test_dry_run_mode_cannot_send():
    client = Mock()

    with patch(
        "scripts.send_dev_agent_proposal_slack."
        "load_write_proposal",
        return_value=pending_proposal(),
    ) as load:
        with pytest.raises(
            DevAgentProposalSlackSendError
        ) as exc:
            send_dev_agent_proposal(
                client=client,
                config=config(
                    mode="DRY_RUN",
                    confirmed=False,
                ),
                proposal_id=PROPOSAL_ID,
            )

    assert (
        exc.value.code
        == "live_send_not_enabled"
    )
    load.assert_called_once_with(
        PROPOSAL_ID
    )
    client.chat_postMessage.assert_not_called()


def test_invalid_proposal_is_not_sent():
    client = Mock()

    with patch(
        "scripts.send_dev_agent_proposal_slack."
        "load_write_proposal",
        return_value={
            "status": "DENIED",
            "reason": (
                "STALE_PROPOSAL_SOURCE_CHANGED"
            ),
        },
    ):
        with pytest.raises(
            DevAgentProposalSlackSendError
        ) as exc:
            send_dev_agent_proposal(
                client=client,
                config=config(),
                proposal_id=PROPOSAL_ID,
            )

    assert (
        exc.value.code
        == "STALE_PROPOSAL_SOURCE_CHANGED"
    )
    client.chat_postMessage.assert_not_called()


def test_non_pending_proposal_is_not_sent():
    client = Mock()

    approved = pending_proposal()
    approved["proposal_state"] = "APPROVED"

    with patch(
        "scripts.send_dev_agent_proposal_slack."
        "load_write_proposal",
        return_value=approved,
    ):
        with pytest.raises(
            DevAgentProposalSlackSendError
        ) as exc:
            send_dev_agent_proposal(
                client=client,
                config=config(),
                proposal_id=PROPOSAL_ID,
            )

    assert (
        exc.value.code
        == "PROPOSAL_NOT_PENDING"
    )
    client.chat_postMessage.assert_not_called()


def test_invalid_slack_binding_is_rejected():
    client = Mock()

    client.chat_postMessage.return_value = {
        "ok": True,
        "channel": "C999",
        "ts": "123.456",
    }

    with (
        patch(
            "scripts.send_dev_agent_proposal_slack."
            "load_write_proposal",
            return_value=pending_proposal(),
        ),
        patch(
            "scripts.send_dev_agent_proposal_slack."
            "build_slack_proposal_approval_message",
            return_value=payload(),
        ),
    ):
        with pytest.raises(
            DevAgentProposalSlackSendError
        ) as exc:
            send_dev_agent_proposal(
                client=client,
                config=config(),
                proposal_id=PROPOSAL_ID,
            )

    assert (
        exc.value.code
        == "invalid_slack_response"
    )
