from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

UNIT_PATH = (
    REPO_ROOT
    / "systemd/"
    "ai-media-os-slack-approval-readiness.service"
)

POLICY_PATH = (
    REPO_ROOT
    / "config/"
    "slack_trusted_autostart_verifier_policy.json"
)

EXPECTED_EXEC_CONDITION = (
    "ExecCondition=/usr/bin/env "
    "-i "
    "PATH=/usr/bin:/bin "
    "HOME=/nonexistent "
    "LANG=C.UTF-8 "
    "/usr/bin/python3 "
    "-I "
    "/usr/local/libexec/ai-media-os/"
    "slack-autostart-verifier.py "
    "--check-autostart"
)


def unit_text() -> str:
    return UNIT_PATH.read_text(
        encoding="utf-8"
    )


def unit_lines() -> list[str]:
    return unit_text().splitlines()


def command_line(prefix: str) -> str:
    matches = [
        line
        for line in unit_lines()
        if line.startswith(prefix)
    ]

    assert len(matches) == 1

    return matches[0]


def load_policy() -> dict[str, object]:
    return json.loads(
        POLICY_PATH.read_text(
            encoding="utf-8"
        )
    )


def test_exec_condition_is_present_once() -> None:
    text = unit_text()

    assert text.count("ExecCondition=") == 1


def test_exec_condition_matches_trusted_verifier_command() -> None:
    assert command_line(
        "ExecCondition="
    ) == EXPECTED_EXEC_CONDITION


def test_exec_condition_precedes_start_checks() -> None:
    lines = unit_lines()

    condition_index = lines.index(
        EXPECTED_EXEC_CONDITION
    )

    start_pre_index = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("ExecStartPre=")
    )

    start_index = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("ExecStart=")
    )

    assert condition_index < start_pre_index
    assert condition_index < start_index


def test_exec_condition_uses_sanitized_environment() -> None:
    line = command_line(
        "ExecCondition="
    )

    assert "/usr/bin/env -i " in line
    assert "PATH=/usr/bin:/bin " in line
    assert "HOME=/nonexistent " in line
    assert "LANG=C.UTF-8 " in line


def test_exec_condition_uses_isolated_system_python() -> None:
    line = command_line(
        "ExecCondition="
    )

    assert (
        "/usr/bin/python3 -I "
        in line
    )


def test_exec_condition_uses_root_managed_verifier() -> None:
    line = command_line(
        "ExecCondition="
    )

    assert (
        "/usr/local/libexec/ai-media-os/"
        "slack-autostart-verifier.py "
        "--check-autostart"
        in line
    )


def test_exec_condition_does_not_use_repository_runtime() -> None:
    line = command_line(
        "ExecCondition="
    )

    assert (
        "/home/deploy/ai_media_os/"
        ".venv/bin/python"
        not in line
    )

    assert (
        "/home/deploy/ai_media_os/"
        "scripts/"
        "check_slack_readiness_autostart.py"
        not in line
    )


def test_exec_condition_does_not_receive_worker_environment() -> None:
    line = command_line(
        "ExecCondition="
    )

    forbidden = (
        "DATABASE_BACKEND=",
        "DATABASE_URL=",
        "SLACK_APPROVAL_MODE=",
        "SLACK_APPROVAL_LIVE_CONFIRM=",
        "PYTHONPATH=",
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN",
    )

    for value in forbidden:
        assert value not in line


def test_worker_commands_remain_readiness_dry_run() -> None:
    start_pre = command_line(
        "ExecStartPre="
    )

    start = command_line(
        "ExecStart="
    )

    for line in (
        start_pre,
        start,
    ):
        assert (
            "DATABASE_BACKEND=sqlite"
            in line
        )

        assert (
            "DATABASE_URL=sqlite:////"
            "var/lib/"
            "ai-media-os-slack-readiness/"
            "ebook_affiliate_readiness.db"
            in line
        )

        assert (
            "SLACK_APPROVAL_MODE=DRY_RUN"
            in line
        )

        assert (
            "SLACK_APPROVAL_LIVE_CONFIRM= "
            in line
        )

        assert (
            "/home/deploy/ai_media_os/"
            ".venv/bin/python"
            in line
        )

        assert (
            "/home/deploy/ai_media_os/"
            "scripts/"
            "run_slack_approval_readiness.py"
            in line
        )


def test_environment_file_remains_for_worker_runtime() -> None:
    text = unit_text()

    assert (
        "EnvironmentFile="
        "/etc/ai-media-os/slack.env"
        in text
    )

    assert (
        "Environment="
        "PYTHONPATH=/home/deploy/ai_media_os"
        in text
    )


def test_host_unit_switch_authorization_is_consumed_and_locked() -> None:
    policy = load_policy()

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1C-2C-2"
    )

    assert policy[
        "expected_exec_condition"
    ] == EXPECTED_EXEC_CONDITION

    assert policy[
        "repository_unit_switch_completed"
    ] is True

    assert policy[
        "host_unit_switch_completed"
    ] is True

    assert policy[
        "host_unit_switch_authorization_consumed"
    ] is True

    assert policy[
        "host_unit_switch_allowed"
    ] is False

    assert policy[
        "unit_install_allowed"
    ] is False

    assert policy[
        "daemon_reload_allowed"
    ] is False

    assert policy[
        "systemd_block_test_allowed"
    ] is False

    assert policy[
        "unit_enable_allowed"
    ] is False

    assert policy[
        "service_start_allowed"
    ] is False

    assert policy[
        "gate_creation_allowed"
    ] is False

    assert policy["production_status"] == (
        "NO_GO"
    )

    assert policy["default_decision"] == (
        "NO_GO"
    )

    authorization = policy[
        "host_switch_authorization"
    ]

    assert authorization[
        "authorized"
    ] is True

    assert authorization[
        "single_controlled_execution"
    ] is True

    assert authorization[
        "consumed"
    ] is True

    assert authorization[
        "consumed_by_host_state"
    ] is True

    assert authorization[
        "consumption_reason"
    ] == (
        "AUTHORIZED_REPOSITORY_UNIT_INSTALLED_"
        "AND_DAEMON_RELOADED"
    )

    assert authorization[
        "postchange_repository_and_installed_match"
    ] is True

    assert authorization[
        "postchange_need_daemon_reload"
    ] == "no"

    assert authorization[
        "postchange_autostart_gate_present"
    ] is False

    assert authorization[
        "postchange_unit_enabled"
    ] is False

    assert authorization[
        "postchange_service_running"
    ] is False

    assert authorization[
        "further_host_unit_switch_allowed"
    ] is False

    for key in (
        "postchange_repository_unit_sha256",
        "postchange_installed_unit_sha256",
        "postchange_installed_verifier_sha256",
    ):
        value = authorization[key]

        assert isinstance(value, str)
        assert len(value) == 64

        int(value, 16)

    assert (
        authorization[
            "postchange_repository_unit_sha256"
        ]
        == authorization[
            "postchange_installed_unit_sha256"
        ]
    )
