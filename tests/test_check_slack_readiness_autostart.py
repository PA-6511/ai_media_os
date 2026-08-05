from __future__ import annotations

from pathlib import Path
import sys

from app.services.slack_autostart_gate import (
    SlackAutostartGateError,
)
from scripts import (
    check_slack_readiness_autostart as command,
)


def prepare_common(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "slack.env"

    env_file.write_text(
        "SLACK_APPROVAL_MODE=DRY_RUN\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        command,
        "_check_health",
        lambda _path: True,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_slack_readiness_autostart.py",
            "--check-health",
            "--env-file",
            str(env_file),
        ],
    )


def test_health_pass_remains_no_go(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    prepare_common(monkeypatch, tmp_path)

    result = command.main()
    output = capsys.readouterr().out

    assert result == 0
    assert "READINESS_HEALTH: PASS" not in output
    assert (
        "AUTOSTART_APPROVAL: NOT_EVALUATED"
        in output
    )
    assert "FINAL_DECISION: NO_GO" in output
    assert "xoxb-" not in output
    assert "xapp-" not in output


def test_missing_gate_returns_no_go(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    prepare_common(monkeypatch, tmp_path)

    monkeypatch.setattr(
        command,
        "resolve_repository_commit",
        lambda _root: "a" * 40,
    )

    def reject_gate(**_kwargs):
        raise SlackAutostartGateError(
            "Autostart approval gate is missing"
        )

    monkeypatch.setattr(
        command,
        "validate_slack_autostart_gate",
        reject_gate,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_slack_readiness_autostart.py",
            "--check-autostart",
            "--env-file",
            str(tmp_path / "slack.env"),
        ],
    )

    result = command.main()
    output = capsys.readouterr().out

    assert result == 3
    assert (
        "AUTOSTART_APPROVAL: NOT_APPROVED"
        in output
    )
    assert "FINAL_DECISION: NO_GO" in output
    assert "xoxb-" not in output
    assert "xapp-" not in output


def test_valid_gate_returns_readiness_only_go(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    prepare_common(monkeypatch, tmp_path)

    monkeypatch.setattr(
        command,
        "resolve_repository_commit",
        lambda _root: "a" * 40,
    )

    monkeypatch.setattr(
        command,
        "validate_slack_autostart_gate",
        lambda **_kwargs: object(),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_slack_readiness_autostart.py",
            "--check-autostart",
            "--env-file",
            str(tmp_path / "slack.env"),
        ],
    )

    result = command.main()
    output = capsys.readouterr().out

    assert result == 0
    assert "AUTOSTART_APPROVAL: APPROVED" in output
    assert (
        "GO_READINESS_AUTOSTART_ONLY"
        in output
    )
    assert "PRODUCTION_STATUS: NO_GO" in output
    assert "xoxb-" not in output
    assert "xapp-" not in output

def test_secure_env_file_is_read(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "slack.env"

    env_file.write_text(
        "SLACK_APPROVAL_MODE=DRY_RUN\n",
        encoding="utf-8",
    )
    env_file.chmod(0o600)

    values = command._read_env_file(
        env_file
    )

    assert values == {
        "SLACK_APPROVAL_MODE": "DRY_RUN",
    }


def test_insecure_env_file_mode_is_rejected(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "slack.env"

    env_file.write_text(
        "SLACK_APPROVAL_MODE=DRY_RUN\n",
        encoding="utf-8",
    )
    env_file.chmod(0o644)

    try:
        command._read_env_file(env_file)
    except Exception as exc:
        assert isinstance(
            exc,
            command.SlackReadinessGuardError,
        )
        assert "mode must be 600" in str(exc)
    else:
        raise AssertionError(
            "Insecure environment mode accepted"
        )


def test_env_file_symbolic_link_is_rejected(
    tmp_path: Path,
) -> None:
    real_env = tmp_path / "real.env"
    linked_env = tmp_path / "linked.env"

    real_env.write_text(
        "SLACK_APPROVAL_MODE=DRY_RUN\n",
        encoding="utf-8",
    )
    real_env.chmod(0o600)

    linked_env.symlink_to(real_env)

    try:
        command._read_env_file(linked_env)
    except Exception as exc:
        assert isinstance(
            exc,
            command.SlackReadinessGuardError,
        )
        assert "symbolic link" in str(exc)
    else:
        raise AssertionError(
            "Environment symlink accepted"
        )
