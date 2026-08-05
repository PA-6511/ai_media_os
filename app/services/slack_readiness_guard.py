from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import sqlite3
import stat
from typing import Mapping


READINESS_DATABASE_PATH = Path(
    "/var/lib/ai-media-os-slack-readiness/"
    "ebook_affiliate_readiness.db"
)

PRODUCTION_DATABASE_PATH = Path(
    "/home/deploy/ai_media_os/"
    "data/database/ebook_affiliate.db"
)

EXPECTED_DATABASE_URL = (
    f"sqlite:///{READINESS_DATABASE_PATH}"
)

REQUIRED_TABLES = frozenset(
    {
        "ebook_items",
        "workflow_approval_requests",
    }
)


class SlackReadinessGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlackReadinessGuardConfig:
    bot_token: str = field(repr=False)
    app_token: str = field(repr=False)

    database_backend: str
    database_url: str
    database_path: Path

    team_id: str
    channel_id: str
    approver_user_ids: frozenset[str]

    mode: str
    production_database_allowed: bool = False


def _required(
    values: Mapping[str, str],
    name: str,
) -> str:
    value = str(
        values.get(name, "")
    ).strip()

    if not value:
        raise SlackReadinessGuardError(
            f"{name}: MISSING"
        )

    return value


def _validate_sqlite_database(
    path: Path,
) -> None:
    try:
        connection = sqlite3.connect(
            f"file:{path}?mode=rw",
            uri=True,
        )
    except sqlite3.Error as exc:
        raise SlackReadinessGuardError(
            "Readiness database cannot be opened "
            "in read/write mode"
        ) from exc

    try:
        quick_check = connection.execute(
            "PRAGMA quick_check"
        ).fetchone()

        if (
            quick_check is None
            or quick_check[0] != "ok"
        ):
            raise SlackReadinessGuardError(
                "Readiness database quick_check failed"
            )

        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        table_names = {
            str(row[0])
            for row in table_rows
        }

        missing_tables = (
            REQUIRED_TABLES - table_names
        )

        if missing_tables:
            names = ", ".join(
                sorted(missing_tables)
            )

            raise SlackReadinessGuardError(
                "Readiness database is missing "
                f"required tables: {names}"
            )
    finally:
        connection.close()


def validate_slack_readiness_environment(
    values: Mapping[str, str],
    *,
    readiness_database_path: Path = (
        READINESS_DATABASE_PATH
    ),
    production_database_path: Path = (
        PRODUCTION_DATABASE_PATH
    ),
    expected_database_url: str = (
        EXPECTED_DATABASE_URL
    ),
) -> SlackReadinessGuardConfig:
    database_backend = _required(
        values,
        "DATABASE_BACKEND",
    ).lower()

    database_url = _required(
        values,
        "DATABASE_URL",
    )

    mode = _required(
        values,
        "SLACK_APPROVAL_MODE",
    ).upper()

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

    raw_approvers = _required(
        values,
        "SLACK_APPROVER_USER_IDS",
    )

    approvers = frozenset(
        value.strip()
        for value in raw_approvers.split(",")
        if value.strip()
    )

    if database_backend != "sqlite":
        raise SlackReadinessGuardError(
            "DATABASE_BACKEND must be sqlite"
        )

    if database_url != expected_database_url:
        raise SlackReadinessGuardError(
            "DATABASE_URL must point exactly to "
            "the authorized readiness database"
        )

    if mode != "DRY_RUN":
        raise SlackReadinessGuardError(
            "SLACK_APPROVAL_MODE must remain DRY_RUN"
        )

    live_confirmation = str(
        values.get(
            "SLACK_APPROVAL_LIVE_CONFIRM",
            "",
        )
    ).strip()

    if live_confirmation:
        raise SlackReadinessGuardError(
            "SLACK_APPROVAL_LIVE_CONFIRM must "
            "be empty in readiness mode"
        )

    if not bot_token.startswith("xoxb-"):
        raise SlackReadinessGuardError(
            "SLACK_BOT_TOKEN prefix is invalid"
        )

    if not app_token.startswith("xapp-"):
        raise SlackReadinessGuardError(
            "SLACK_APP_TOKEN prefix is invalid"
        )

    if not team_id.startswith("T"):
        raise SlackReadinessGuardError(
            "Slack workspace ID is invalid"
        )

    if not channel_id.startswith("C"):
        raise SlackReadinessGuardError(
            "Slack channel ID is invalid"
        )

    if not approvers:
        raise SlackReadinessGuardError(
            "Slack approver list is empty"
        )

    if not all(
        value.startswith("U")
        for value in approvers
    ):
        raise SlackReadinessGuardError(
            "Slack approver ID is invalid"
        )

    if readiness_database_path.is_symlink():
        raise SlackReadinessGuardError(
            "Readiness database must not be "
            "a symbolic link"
        )

    if not readiness_database_path.is_file():
        raise SlackReadinessGuardError(
            "Readiness database is missing"
        )

    if not production_database_path.is_file():
        raise SlackReadinessGuardError(
            "Production database is missing"
        )

    resolved_readiness = (
        readiness_database_path.resolve(
            strict=True
        )
    )

    resolved_production = (
        production_database_path.resolve(
            strict=True
        )
    )

    if resolved_readiness == resolved_production:
        raise SlackReadinessGuardError(
            "Readiness database resolves to "
            "the production database"
        )

    if os.path.samefile(
        resolved_readiness,
        resolved_production,
    ):
        raise SlackReadinessGuardError(
            "Readiness database is the "
            "production database"
        )

    database_stat = resolved_readiness.stat()

    database_mode = stat.S_IMODE(
        database_stat.st_mode
    )

    if database_mode != 0o600:
        raise SlackReadinessGuardError(
            "Readiness database mode must be 600"
        )

    if database_stat.st_uid != os.geteuid():
        raise SlackReadinessGuardError(
            "Readiness database owner does not "
            "match the service user"
        )

    if database_stat.st_gid != os.getegid():
        raise SlackReadinessGuardError(
            "Readiness database group does not "
            "match the service group"
        )

    parent = resolved_readiness.parent

    parent_mode = stat.S_IMODE(
        parent.stat().st_mode
    )

    if parent_mode != 0o700:
        raise SlackReadinessGuardError(
            "Readiness database directory "
            "mode must be 700"
        )

    _validate_sqlite_database(
        resolved_readiness
    )

    return SlackReadinessGuardConfig(
        bot_token=bot_token,
        app_token=app_token,
        database_backend=database_backend,
        database_url=database_url,
        database_path=resolved_readiness,
        team_id=team_id,
        channel_id=channel_id,
        approver_user_ids=approvers,
        mode=mode,
        production_database_allowed=False,
    )
