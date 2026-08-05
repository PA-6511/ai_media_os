from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

from app.services.slack_readiness_guard import (
    SlackReadinessGuardError,
    validate_slack_readiness_environment,
)


def create_sqlite_database(
    path: Path,
    *,
    include_required_tables: bool,
) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE database_marker (
                id INTEGER PRIMARY KEY
            )
            """
        )

        if include_required_tables:
            connection.execute(
                """
                CREATE TABLE ebook_items (
                    id TEXT PRIMARY KEY
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE
                workflow_approval_requests (
                    id TEXT PRIMARY KEY
                )
                """
            )


def prepare_paths(
    tmp_path: Path,
):
    readiness_dir = (
        tmp_path / "readiness"
    )

    readiness_dir.mkdir()
    readiness_dir.chmod(0o700)

    readiness = (
        readiness_dir / "readiness.db"
    )

    production = (
        tmp_path / "production.db"
    )

    create_sqlite_database(
        readiness,
        include_required_tables=True,
    )

    create_sqlite_database(
        production,
        include_required_tables=False,
    )

    readiness.chmod(0o600)
    production.chmod(0o600)

    database_url = (
        f"sqlite:///{readiness}"
    )

    return (
        readiness,
        production,
        database_url,
    )


def make_values(
    database_url: str,
    *,
    mode: str = "DRY_RUN",
    live_confirmation: str = "",
) -> dict[str, str]:
    return {
        "DATABASE_BACKEND": "sqlite",
        "DATABASE_URL": database_url,
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "SLACK_APP_TOKEN": "xapp-test-token",
        "SLACK_APPROVAL_TEAM_ID": "T123",
        "SLACK_APPROVAL_CHANNEL_ID": "C123",
        "SLACK_APPROVER_USER_IDS": "U123,U456",
        "SLACK_APPROVAL_MODE": mode,
        "SLACK_APPROVAL_LIVE_CONFIRM": (
            live_confirmation
        ),
    }


def test_valid_readiness_configuration(
    tmp_path: Path,
) -> None:
    (
        readiness,
        production,
        database_url,
    ) = prepare_paths(tmp_path)

    config = (
        validate_slack_readiness_environment(
            make_values(database_url),
            readiness_database_path=readiness,
            production_database_path=production,
            expected_database_url=database_url,
        )
    )

    assert config.mode == "DRY_RUN"
    assert (
        config.production_database_allowed
        is False
    )
    assert config.database_path == (
        readiness.resolve()
    )
    assert "xoxb-test-token" not in repr(config)
    assert "xapp-test-token" not in repr(config)


def test_live_mode_is_rejected(
    tmp_path: Path,
) -> None:
    (
        readiness,
        production,
        database_url,
    ) = prepare_paths(tmp_path)

    with pytest.raises(
        SlackReadinessGuardError
    ):
        validate_slack_readiness_environment(
            make_values(
                database_url,
                mode="LIVE",
            ),
            readiness_database_path=readiness,
            production_database_path=production,
            expected_database_url=database_url,
        )


def test_live_confirmation_is_rejected(
    tmp_path: Path,
) -> None:
    (
        readiness,
        production,
        database_url,
    ) = prepare_paths(tmp_path)

    with pytest.raises(
        SlackReadinessGuardError
    ):
        validate_slack_readiness_environment(
            make_values(
                database_url,
                live_confirmation=(
                    "I_UNDERSTAND_DB_WRITES"
                ),
            ),
            readiness_database_path=readiness,
            production_database_path=production,
            expected_database_url=database_url,
        )


def test_production_database_url_is_rejected(
    tmp_path: Path,
) -> None:
    (
        readiness,
        production,
        database_url,
    ) = prepare_paths(tmp_path)

    production_url = (
        f"sqlite:///{production}"
    )

    with pytest.raises(
        SlackReadinessGuardError
    ):
        validate_slack_readiness_environment(
            make_values(production_url),
            readiness_database_path=readiness,
            production_database_path=production,
            expected_database_url=database_url,
        )


def test_symbolic_link_is_rejected(
    tmp_path: Path,
) -> None:
    (
        readiness,
        production,
        database_url,
    ) = prepare_paths(tmp_path)

    symlink = (
        readiness.parent / "linked.db"
    )

    symlink.symlink_to(readiness)

    symlink_url = (
        f"sqlite:///{symlink}"
    )

    with pytest.raises(
        SlackReadinessGuardError
    ):
        validate_slack_readiness_environment(
            make_values(symlink_url),
            readiness_database_path=symlink,
            production_database_path=production,
            expected_database_url=symlink_url,
        )


def test_missing_required_table_is_rejected(
    tmp_path: Path,
) -> None:
    readiness_dir = (
        tmp_path / "readiness"
    )

    readiness_dir.mkdir()
    readiness_dir.chmod(0o700)

    readiness = (
        readiness_dir / "readiness.db"
    )

    production = (
        tmp_path / "production.db"
    )

    create_sqlite_database(
        readiness,
        include_required_tables=False,
    )

    create_sqlite_database(
        production,
        include_required_tables=False,
    )

    readiness.chmod(0o600)
    production.chmod(0o600)

    database_url = (
        f"sqlite:///{readiness}"
    )

    with pytest.raises(
        SlackReadinessGuardError
    ):
        validate_slack_readiness_environment(
            make_values(database_url),
            readiness_database_path=readiness,
            production_database_path=production,
            expected_database_url=database_url,
        )
