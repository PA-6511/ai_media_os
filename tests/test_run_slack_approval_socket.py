from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_check_config_does_not_expose_secrets() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    env = os.environ.copy()

    env.update(
        {
            "SLACK_BOT_TOKEN": (
                "xoxb-secret-test-token"
            ),
            "SLACK_APP_TOKEN": (
                "xapp-secret-test-token"
            ),
            "SLACK_APPROVAL_TEAM_ID": "T123",
            "SLACK_APPROVAL_CHANNEL_ID": "C123",
            "SLACK_APPROVER_USER_IDS": "U123",
            "SLACK_APPROVAL_MODE": "DRY_RUN",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_slack_approval_socket.py",
            "--check-config",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert "SLACK_SOCKET_CONFIG: PASS" in (
        result.stdout
    )

    assert "DATABASE_WRITES: DISABLED" in (
        result.stdout
    )

    assert (
        "xoxb-secret-test-token"
        not in result.stdout
    )

    assert (
        "xapp-secret-test-token"
        not in result.stdout
    )
    combined_output = result.stdout + result.stderr
    assert "xoxb-secret-test-token" not in combined_output
    assert "xapp-secret-test-token" not in combined_output


def test_start_returns_zero_on_keyboard_interrupt(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from scripts import (
        run_slack_approval_socket as runner,
    )

    handler_state = {
        "created": False,
        "started": False,
        "closed": 0,
    }

    class InterruptingHandler:
        def __init__(
            self,
            app,
            app_token,
        ) -> None:
            assert app is not None
            assert app_token == "xapp-test-token"

            handler_state["created"] = True

        def start(self) -> None:
            handler_state["started"] = True
            raise KeyboardInterrupt

        def close(self) -> None:
            handler_state["closed"] += 1

    config = SimpleNamespace(
        mode="DRY_RUN",
        app_token="xapp-test-token",
    )

    monkeypatch.setattr(
        runner,
        "parse_args",
        lambda: SimpleNamespace(
            check_config=False,
            start=True,
        ),
    )

    monkeypatch.setattr(
        runner,
        "load_config",
        lambda: config,
    )

    monkeypatch.setattr(
        runner,
        "build_app",
        lambda supplied_config: object(),
    )

    result = runner.main(
        handler_factory=InterruptingHandler,
    )

    assert result == 0
    assert handler_state["created"] is True
    assert handler_state["started"] is True
    assert handler_state["closed"] == 1


def test_sigterm_handler_requests_clean_stop() -> None:
    import signal

    import pytest

    from scripts import (
        run_slack_approval_socket as runner,
    )

    class FakeHandler:
        def __init__(self) -> None:
            self.close_count = 0

        def close(self) -> None:
            self.close_count += 1

    handler = FakeHandler()
    controller = runner.WorkerStopController(handler)

    with pytest.raises(KeyboardInterrupt):
        controller.request_stop(
            signal.SIGTERM,
            None,
        )

    controller.close_once()
    assert controller.stop_requested is True
    assert handler.close_count == 1
