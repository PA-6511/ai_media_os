from __future__ import annotations

from pathlib import Path

import pytest

from app.services.slack_live_copy_guard import (
    SlackLiveCopyGuardError,
    validate_slack_live_copy_environment,
)


def make_values(
    *,
    database_url: str,
    mode: str = "LIVE",
    live_confirm: str = (
        "I_UNDERSTAND_DB_WRITES"
    ),
    send_confirm: str = (
        "SEND_ONE_SLACK_LIVE_COPY_MESSAGE"
    ),
) -> dict[str, str]:
    return {
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": database_url,
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "SLACK_APP_TOKEN": "xapp-test-token",
        "SLACK_APPROVAL_TEAM_ID": "T123",
        "SLACK_APPROVAL_CHANNEL_ID": "C123",
        "SLACK_APPROVER_USER_IDS": "U123",
        "SLACK_APPROVAL_MODE": mode,
        "SLACK_APPROVAL_LIVE_CONFIRM": (
            live_confirm
        ),
        "SLACK_5F_SEND_CONFIRM": send_confirm,
    }


def prepare_databases(tmp_path: Path):
    production = tmp_path / "production.db"
    copy_database = tmp_path / "copy.db"

    production.write_bytes(b"production")
    copy_database.write_bytes(b"copy")

    production.chmod(0o600)
    copy_database.chmod(0o600)

    database_url = (
        f"sqlite:///{copy_database}"
    )

    return (
        production,
        copy_database,
        database_url,
    )


def test_valid_live_copy_configuration(
    tmp_path: Path,
) -> None:
    (
        production,
        copy_database,
        database_url,
    ) = prepare_databases(tmp_path)

    config = validate_slack_live_copy_environment(
        make_values(
            database_url=database_url
        ),
        expected_database_url=database_url,
        expected_database_path=copy_database,
        production_database_path=production,
        require_send_confirmation=True,
        send_confirmation_name=(
            "SLACK_5F_SEND_CONFIRM"
        ),
        send_confirmation_value=(
            "SEND_ONE_SLACK_LIVE_COPY_MESSAGE"
        ),
    )

    assert config.mode == "LIVE"
    assert config.live_confirmed is True
    assert config.send_confirmed is True
    assert "xoxb-test-token" not in repr(config)
    assert "xapp-test-token" not in repr(config)


def test_dry_run_mode_is_rejected(
    tmp_path: Path,
) -> None:
    (
        production,
        copy_database,
        database_url,
    ) = prepare_databases(tmp_path)

    with pytest.raises(
        SlackLiveCopyGuardError
    ):
        validate_slack_live_copy_environment(
            make_values(
                database_url=database_url,
                mode="DRY_RUN",
            ),
            expected_database_url=database_url,
            expected_database_path=copy_database,
            production_database_path=production,
        )


def test_production_database_is_rejected(
    tmp_path: Path,
) -> None:
    (
        production,
        _copy_database,
        _database_url,
    ) = prepare_databases(tmp_path)

    production_url = (
        f"sqlite:///{production}"
    )

    with pytest.raises(
        SlackLiveCopyGuardError
    ):
        validate_slack_live_copy_environment(
            make_values(
                database_url=production_url
            ),
            expected_database_url=production_url,
            expected_database_path=production,
            production_database_path=production,
        )


def test_missing_send_confirmation_is_rejected(
    tmp_path: Path,
) -> None:
    (
        production,
        copy_database,
        database_url,
    ) = prepare_databases(tmp_path)

    values = make_values(
        database_url=database_url,
        send_confirm="",
    )

    with pytest.raises(
        SlackLiveCopyGuardError
    ):
        validate_slack_live_copy_environment(
            values,
            expected_database_url=database_url,
            expected_database_path=copy_database,
            production_database_path=production,
            require_send_confirmation=True,
            send_confirmation_name=(
                "SLACK_5F_SEND_CONFIRM"
            ),
            send_confirmation_value=(
                "SEND_ONE_SLACK_LIVE_COPY_MESSAGE"
            ),
        )
