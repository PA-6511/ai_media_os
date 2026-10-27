from types import SimpleNamespace

from dev_agent.slack_proposal_approval_adapter import (
    DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID,
)
from scripts import run_slack_approval_socket as runner


class FakeApp:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.actions = {}

    def action(self, action_id):
        def register(handler):
            self.actions[action_id] = handler
            return handler

        return register

    def view(self, callback_id):
        def register(handler):
            return handler

        return register


def test_dev_agent_proposal_action_registered():
    config = SimpleNamespace(
        bot_token="xoxb-test",
        app_token="xapp-test",
        team_id="T123",
        channel_id="C123",
        approver_user_ids=frozenset({"U123"}),
        mode="DRY_RUN",
        live_confirmed=False,
    )

    app = runner.build_app(
        config,
        app_factory=FakeApp,
    )

    assert (
        DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
        in app.actions
    )

    handler = app.actions[
        DEV_AGENT_PROPOSAL_APPROVE_ACTION_ID
    ]

    assert callable(handler)
    assert (
        handler.__name__
        == "handle_dev_agent_proposal_action"
    )
