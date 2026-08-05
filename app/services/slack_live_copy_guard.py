from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import stat
from typing import Mapping


LIVE_CONFIRM_VALUE = "I_UNDERSTAND_DB_WRITES"


class SlackLiveCopyGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlackLiveCopyGuardConfig:
    bot_token: str = field(repr=False)
    app_token: str = field(repr=False)

    database_url: str
    database_path: Path

    team_id: str
    channel_id: str
    approver_user_ids: frozenset[str]

    mode: str
    live_confirmed: bool
    send_confirmed: bool


def _required(
    values: Mapping[str, str],
    name: str,
) -> str:
    value = str(
        values.get(name, "")
    ).strip()

    if not value:
        raise SlackLiveCopyGuardError(
            f"{name}: MISSING"
        )

    return value


def validate_slack_live_copy_environment(
    values: Mapping[str, str],
    *,
    expected_database_url: str,
    expected_database_path: Path,
    production_database_path: Path,
    require_send_confirmation: bool = False,
    send_confirmation_name: str = "",
    send_confirmation_value: str = "",
) -> SlackLiveCopyGuardConfig:
    database_backend = _required(
        values,
        "DATABASE_BACKEND",
    )

    database_url = _required(
        values,
        "DATABASE_URL",
    )

    mode = _required(
        values,
        "SLACK_APPROVAL_MODE",
    ).upper()

    live_confirmation = _required(
        values,
        "SLACK_APPROVAL_LIVE_CONFIRM",
    )

    bot_token = _required(
        values,
        "SLACK_BOT_TOKEN",
    )

    app_token = _required(
        values,
        "SLACK_APP_TOKEN",
    )

    team_id = _required(
        values,
        "SLACK_APPROVAL_TEAM_ID",
    )

    channel_id = _required(
        values,
        "SLACK_APPROVAL_CHANNEL_ID",
    )

    approvers_raw = _required(
        values,
        "SLACK_APPROVER_USER_IDS",
    )

    approvers = frozenset(
        value.strip()
        for value in approvers_raw.split(",")
        if value.strip()
    )

    if database_backend != "sqlite":
        raise SlackLiveCopyGuardError(
            "DATABASE_BACKEND must be sqlite"
        )

    if database_url != expected_database_url:
        raise SlackLiveCopyGuardError(
            "DATABASE_URL does not point to "
            "the authorized 5F copy database"
        )

    expected_database_path = (
        expected_database_path.resolve()
    )

    production_database_path = (
        production_database_path.resolve()
    )

    if not expected_database_path.is_file():
        raise SlackLiveCopyGuardError(
            "Authorized 5F copy database is missing"
        )

    file_mode = stat.S_IMODE(
        expected_database_path.stat().st_mode
    )

    if file_mode != 0o600:
        raise SlackLiveCopyGuardError(
            "5F copy database mode must be 600"
        )

    if not production_database_path.is_file():
        raise SlackLiveCopyGuardError(
            "Production database is missing"
        )

    if os.path.samefile(
        expected_database_path,
        production_database_path,
    ):
        raise SlackLiveCopyGuardError(
            "Copy database resolves to production DB"
        )

    if mode != "LIVE":
        raise SlackLiveCopyGuardError(
            "SLACK_APPROVAL_MODE must be LIVE "
            "for the isolated 5F test"
        )

    if live_confirmation != LIVE_CONFIRM_VALUE:
        raise SlackLiveCopyGuardError(
            "LIVE database-write confirmation "
            "is missing"
        )

    if not bot_token.startswith("xoxb-"):
        raise SlackLiveCopyGuardError(
            "SLACK_BOT_TOKEN prefix is invalid"
        )

    if not app_token.startswith("xapp-"):
        raise SlackLiveCopyGuardError(
            "SLACK_APP_TOKEN prefix is invalid"
        )

    if not team_id.startswith("T"):
        raise SlackLiveCopyGuardError(
            "Slack workspace ID is invalid"
        )

    if not channel_id.startswith("C"):
        raise SlackLiveCopyGuardError(
            "Slack channel ID is invalid"
        )

    if not approvers:
        raise SlackLiveCopyGuardError(
            "Slack approver list is empty"
        )

    if not all(
        value.startswith("U")
        for value in approvers
    ):
        raise SlackLiveCopyGuardError(
            "Slack approver ID is invalid"
        )

    send_confirmed = False

    if require_send_confirmation:
        if not send_confirmation_name:
            raise SlackLiveCopyGuardError(
                "Send confirmation name is missing"
            )

        supplied_confirmation = str(
            values.get(
                send_confirmation_name,
                "",
            )
        ).strip()

        if (
            supplied_confirmation
            != send_confirmation_value
        ):
            raise SlackLiveCopyGuardError(
                "Explicit one-message send "
                "confirmation is missing"
            )

        send_confirmed = True

    return SlackLiveCopyGuardConfig(
        bot_token=bot_token,
        app_token=app_token,
        database_url=database_url,
        database_path=expected_database_path,
        team_id=team_id,
        channel_id=channel_id,
        approver_user_ids=approvers,
        mode=mode,
        live_confirmed=True,
        send_confirmed=send_confirmed,
    )
