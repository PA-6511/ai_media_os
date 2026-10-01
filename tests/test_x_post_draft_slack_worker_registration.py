from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
)
from app.services.x_post_draft_slack_preset_service import (
    X_POST_DRAFT_OPEN_ACTION_ID,
    X_POST_DRAFT_VIEW_CALLBACK_ID,
)
from scripts.run_slack_approval_socket import (
    build_app,
)


class FakeApp:
    def __init__(
        self,
        *,
        token,
    ):
        self.token = token
        self.actions = {}
        self.views = {}

    def action(
        self,
        action_id,
    ):
        def decorate(fn):
            self.actions[
                action_id
            ] = fn
            return fn

        return decorate

    def view(
        self,
        callback_id,
    ):
        def decorate(fn):
            self.views[
                callback_id
            ] = fn
            return fn

        return decorate


def test_worker_registers_x_draft_preset_handlers():
    config = SlackApprovalSocketConfig(
        bot_token="xoxb-test",
        app_token="xapp-test",
        team_id="TTEST",
        channel_id="CTEST",
        approver_user_ids=frozenset(
            {"UTEST"}
        ),
        mode="LIVE",
        live_confirmed=True,
    )

    app = build_app(
        config,
        app_factory=FakeApp,
    )

    assert (
        X_POST_DRAFT_OPEN_ACTION_ID
        in app.actions
    )

    assert (
        X_POST_DRAFT_VIEW_CALLBACK_ID
        in app.views
    )
