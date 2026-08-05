from __future__ import annotations

import argparse
import importlib
import inspect
import signal
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "scripts/run_slack_approval_socket.py"
EXPECTED_SOURCE_SHA = (
    "c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runtime_module() -> Any:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    module_name = "scripts.run_slack_approval_socket"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)

    assert Path(module.__file__).resolve() == SOURCE_PATH.resolve()
    assert _sha256(SOURCE_PATH) == EXPECTED_SOURCE_SHA
    return module


class _AttributeBag:
    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)

    def __getattr__(self, name: str) -> Any:
        lower = name.lower()
        if "token" in lower:
            return f"{name}-offline-test"
        if lower.startswith(("is_", "has_", "enable", "allow", "require")):
            return False
        if "timeout" in lower or "limit" in lower or "count" in lower:
            return 1
        if "ids" in lower or "channels" in lower or "actions" in lower:
            return ()
        if "path" in lower or "file" in lower:
            return Path("/tmp") / f"{name}-offline-test"
        if "mode" in lower:
            return "DRY_RUN"
        return f"{name}-offline-test"


def _config() -> _AttributeBag:
    return _AttributeBag(
        bot_token="xoxb-offline-test",
        app_token="xapp-offline-test",
        mode="DRY_RUN",
    )


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        log_level="INFO",
        once=False,
        dry_run=True,
    )


def _deny_network(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    raise AssertionError("EXTERNAL_NETWORK_OPERATION_FORBIDDEN")


def _deny_database(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    raise AssertionError("DATABASE_SESSION_CREATION_FORBIDDEN")


def test_main_returns_fixed_dependency_error_without_network_or_db_when_slack_bolt_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime = _load_runtime_module()

    monkeypatch.setattr(sys, "argv", [str(SOURCE_PATH), "--start"])
    monkeypatch.setattr(runtime, "load_config", _config)
    monkeypatch.setattr(runtime, "SessionLocal", _deny_database)
    monkeypatch.setattr(socket, "socket", _deny_network)

    signal_calls: list[tuple[Any, Any]] = []
    monkeypatch.setattr(runtime.signal, "getsignal", lambda signum: object())
    monkeypatch.setattr(
        runtime.signal,
        "signal",
        lambda signum, handler: signal_calls.append((signum, handler)),
    )

    load_count = 0

    def missing_runtime() -> tuple[Any, Any]:
        nonlocal load_count
        load_count += 1
        raise runtime.SlackBoltDependencyNotAvailable(
            runtime.SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE
        )

    handler_factory_calls: list[tuple[Any, ...]] = []

    def forbidden_handler_factory(*args: Any, **kwargs: Any) -> Any:
        handler_factory_calls.append((args, kwargs))
        raise AssertionError("HANDLER_FACTORY_MUST_NOT_BE_CALLED")

    monkeypatch.setattr(runtime, "load_slack_runtime", missing_runtime)

    result = runtime.main(handler_factory=forbidden_handler_factory)
    captured = capsys.readouterr()

    assert result == 3
    assert load_count == 1
    assert handler_factory_calls == []
    assert runtime.SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE in captured.err
    assert captured.err.strip().splitlines()[-1] == (
        runtime.SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE
    )
    assert signal_calls == []


def test_main_default_factories_preserve_app_and_handler_arguments_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _load_runtime_module()
    config = _config()

    monkeypatch.setattr(sys, "argv", [str(SOURCE_PATH), "--start"])
    monkeypatch.setattr(runtime, "load_config", lambda: config)
    monkeypatch.setattr(runtime, "SessionLocal", _deny_database)
    monkeypatch.setattr(socket, "socket", _deny_network)

    previous_handler = object()
    signal_events: list[tuple[Any, Any]] = []

    monkeypatch.setattr(
        runtime.signal,
        "getsignal",
        lambda signum: previous_handler,
    )
    monkeypatch.setattr(
        runtime.signal,
        "signal",
        lambda signum, handler: signal_events.append((signum, handler)),
    )

    app_calls: list[dict[str, Any]] = []
    handler_calls: list[tuple[Any, str]] = []

    class FakeApp:
        def __init__(self, **kwargs: Any) -> None:
            app_calls.append(dict(kwargs))
            self.client = SimpleNamespace()

        def _decorator(self, *args: Any, **kwargs: Any) -> Any:
            del args, kwargs

            def register(function: Any) -> Any:
                return function

            return register

        action = _decorator
        command = _decorator
        event = _decorator
        message = _decorator
        shortcut = _decorator
        view = _decorator
        options = _decorator

        def __getattr__(self, name: str) -> Any:
            del name
            return self._decorator

    class FakeHandler:
        instances: list["FakeHandler"] = []

        def __init__(self, app: Any, app_token: str) -> None:
            handler_calls.append((app, app_token))
            self.app = app
            self.app_token = app_token
            self.start_count = 0
            self.close_count = 0
            self.__class__.instances.append(self)

        def start(self) -> None:
            self.start_count += 1

        def close(self) -> None:
            self.close_count += 1

    runtime_load_calls: list[int] = []

    def fake_load_slack_runtime() -> tuple[Any, Any]:
        runtime_load_calls.append(len(runtime_load_calls) + 1)
        return FakeApp, FakeHandler

    monkeypatch.setattr(
        runtime,
        "load_slack_runtime",
        fake_load_slack_runtime,
    )

    result = runtime.main()

    assert result == 0
    assert len(runtime_load_calls) == 2

    assert app_calls == [{"token": config.bot_token}]
    assert len(handler_calls) == 1

    app, app_token = handler_calls[0]
    assert isinstance(app, FakeApp)
    assert app_token == config.app_token

    assert len(FakeHandler.instances) == 1
    handler = FakeHandler.instances[0]
    assert handler.start_count == 1
    assert handler.close_count == 1

    assert len(signal_events) == 2
    assert signal_events[0][0] == signal.SIGTERM
    assert callable(signal_events[0][1])
    assert signal_events[1] == (signal.SIGTERM, previous_handler)


def test_worker_stop_controller_close_once_is_idempotent_offline() -> None:
    runtime = _load_runtime_module()

    class FakeHandler:
        def __init__(self) -> None:
            self.close_count = 0

        def close(self) -> None:
            self.close_count += 1

    handler = FakeHandler()
    controller = runtime.WorkerStopController(handler)

    controller.close_once()
    controller.close_once()

    assert handler.close_count == 1


def test_worker_stop_controller_sigterm_requests_stop_and_closes_once_offline() -> None:
    runtime = _load_runtime_module()

    class FakeHandler:
        def __init__(self) -> None:
            self.close_count = 0

        def close(self) -> None:
            self.close_count += 1

    handler = FakeHandler()
    controller = runtime.WorkerStopController(handler)

    with pytest.raises(KeyboardInterrupt):
        controller.request_stop(signal.SIGTERM, None)

    controller.close_once()

    assert controller.stop_requested is True
    assert handler.close_count == 1
