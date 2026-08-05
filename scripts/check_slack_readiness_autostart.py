from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
from typing import Mapping


if __package__ in {None, ""}:
    repository_root = (
        Path(__file__).resolve().parents[1]
    )

    sys.path.insert(
        0,
        str(repository_root),
    )


from app.services.slack_autostart_gate import (  # noqa: E402
    AUTOSTART_GATE_PATH,
    REPOSITORY_ROOT,
    SlackAutostartGateError,
    resolve_repository_commit,
    validate_slack_autostart_gate,
)
from app.services.slack_readiness_guard import (  # noqa: E402
    EXPECTED_DATABASE_URL,
    SlackReadinessGuardError,
    validate_slack_readiness_environment,
)


DEFAULT_ENV_FILE = Path(
    "/etc/ai-media-os/slack.env"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check Slack readiness health and "
            "fail-closed autostart approval."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--check-health",
        action="store_true",
    )

    group.add_argument(
        "--check-autostart",
        action="store_true",
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
    )

    parser.add_argument(
        "--gate-file",
        type=Path,
        default=AUTOSTART_GATE_PATH,
    )

    parser.add_argument(
        "--repository-root",
        type=Path,
        default=REPOSITORY_ROOT,
    )

    return parser.parse_args()


def _read_env_file(
    path: Path,
) -> dict[str, str]:
    try:
        file_stat = path.lstat()
    except FileNotFoundError as exc:
        raise SlackReadinessGuardError(
            "Slack environment file is missing"
        ) from exc

    if stat.S_ISLNK(file_stat.st_mode):
        raise SlackReadinessGuardError(
            "Slack environment file must not "
            "be a symbolic link"
        )

    if not stat.S_ISREG(file_stat.st_mode):
        raise SlackReadinessGuardError(
            "Slack environment file must be "
            "a regular file"
        )

    file_mode = stat.S_IMODE(
        file_stat.st_mode
    )

    if file_mode != 0o600:
        raise SlackReadinessGuardError(
            "Slack environment file mode "
            "must be 600"
        )

    if file_stat.st_uid != os.geteuid():
        raise SlackReadinessGuardError(
            "Slack environment file owner "
            "does not match the service user"
        )

    if file_stat.st_gid != os.getegid():
        raise SlackReadinessGuardError(
            "Slack environment file group "
            "does not match the service group"
        )

    values: dict[str, str] = {}

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            raise SlackReadinessGuardError(
                "Slack environment file contains "
                "an invalid line"
            )

        key, value = line.split("=", 1)

        key = key.strip()
        value = value.strip()

        if not key:
            raise SlackReadinessGuardError(
                "Slack environment key is empty"
            )

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        values[key] = value

    return values


def _build_readiness_values(
    env_file: Path,
    environment: Mapping[str, str],
) -> dict[str, str]:
    values = _read_env_file(env_file)

    for key in (
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
        "SLACK_APPROVAL_TEAM_ID",
        "SLACK_APPROVAL_CHANNEL_ID",
        "SLACK_APPROVER_USER_IDS",
        "SLACK_APPROVAL_MODE",
        "SLACK_APPROVAL_LIVE_CONFIRM",
        "DATABASE_BACKEND",
        "DATABASE_URL",
    ):
        if key in environment:
            values[key] = environment[key]

    values.setdefault(
        "DATABASE_BACKEND",
        "sqlite",
    )

    values.setdefault(
        "DATABASE_URL",
        EXPECTED_DATABASE_URL,
    )

    values.setdefault(
        "SLACK_APPROVAL_LIVE_CONFIRM",
        "",
    )

    return values


def _check_health(
    env_file: Path,
) -> bool:
    try:
        values = _build_readiness_values(
            env_file,
            os.environ,
        )

        validate_slack_readiness_environment(
            values
        )
    except SlackReadinessGuardError as exc:
        print(
            f"READINESS_HEALTH: FAIL ({exc})",
            file=sys.stderr,
        )

        return False

    print("READINESS_HEALTH: PASS")
    print("SLACK_MODE: DRY_RUN")
    print(
        "PRODUCTION_DATABASE_ALLOWED: FALSE"
    )

    return True


def main() -> int:
    args = parse_args()

    if not _check_health(args.env_file):
        print(
            "AUTOSTART_APPROVAL: NOT_APPROVED"
        )
        print("FINAL_DECISION: NO_GO")
        print("PRODUCTION_STATUS: NO_GO")

        return 2

    if args.check_health:
        print(
            "AUTOSTART_APPROVAL: NOT_EVALUATED"
        )
        print("FINAL_DECISION: NO_GO")
        print("PRODUCTION_STATUS: NO_GO")

        return 0

    try:
        expected_commit = (
            resolve_repository_commit(
                args.repository_root
            )
        )

        validate_slack_autostart_gate(
            gate_path=args.gate_file,
            expected_commit=expected_commit,
        )
    except SlackAutostartGateError as exc:
        print(
            "AUTOSTART_APPROVAL: "
            f"NOT_APPROVED ({exc})"
        )
        print("FINAL_DECISION: NO_GO")
        print("PRODUCTION_STATUS: NO_GO")

        return 3

    print("AUTOSTART_APPROVAL: APPROVED")
    print(
        "AUTOSTART_SCOPE: "
        "READINESS_DRY_RUN_ONLY"
    )
    print(
        "FINAL_DECISION: "
        "GO_READINESS_AUTOSTART_ONLY"
    )
    print("PRODUCTION_STATUS: NO_GO")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
