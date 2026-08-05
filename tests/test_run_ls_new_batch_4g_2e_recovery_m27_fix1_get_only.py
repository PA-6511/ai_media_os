from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

RUNNER = ROOT / (
    "scripts/"
    "run_ls_new_batch_4g_2e_recovery_m27_fix1_get_only.py"
)

DIAGNOSTIC = ROOT / (
    "exchange/diagnostics/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_m27_transport_failure_diagnostic.json"
)
PLAN = ROOT / (
    "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_next_single_get_non_execution_plan.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m27_fix1_result.json"
)


spec = importlib.util.spec_from_file_location(
    "m27_fix1_runner",
    RUNNER,
)
assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)
spec.loader.exec_module(module)


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_network_gate_is_closed_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        module.NETWORK_APPROVAL_ENV,
        raising=False,
    )

    assert os.environ.get(
        module.NETWORK_APPROVAL_ENV
    ) is None


def test_mock_success_is_exactly_one_get() -> None:
    calls: list[tuple[str, str, int]] = []

    def fake_transport(
        url: str,
        authorization_value: str,
        timeout_seconds: int,
    ) -> tuple[int, bytes]:
        calls.append(
            (
                url,
                authorization_value,
                timeout_seconds,
            )
        )

        return (
            200,
            json.dumps(
                {
                    "id": 192,
                    "status": "publish"
                }
            ).encode("utf-8"),
        )

    result = module.execute_with_transport(
        fake_transport,
        "REDACTED_TARGET",
        "REDACTED_AUTH",
    )

    assert len(calls) == 1
    assert result[
        "request_method"
    ] == "GET"
    assert result[
        "get_request_count"
    ] == 1
    assert result[
        "non_get_request_count"
    ] == 0
    assert result[
        "automatic_retry_count"
    ] == 0
    assert result[
        "redirect_followed"
    ] is False
    assert result[
        "http_status_code"
    ] == 200
    assert result[
        "response_json_object"
    ] is True


def test_mock_transport_failure_is_safe() -> None:
    calls = 0

    def failing_transport(
        url: str,
        authorization_value: str,
        timeout_seconds: int,
    ) -> tuple[int, bytes]:
        nonlocal calls
        calls += 1

        raise ConnectionResetError(
            "message must not be recorded"
        )

    result = module.execute_with_transport(
        failing_transport,
        "REDACTED_TARGET",
        "REDACTED_AUTH",
    )

    assert calls == 1
    assert result[
        "get_request_count"
    ] == 1
    assert result[
        "automatic_retry_count"
    ] == 0
    assert result[
        "network_error_type"
    ] == "ConnectionResetError"
    assert result[
        "failure_stage"
    ] == "SINGLE_TRANSPORT_CALL"

    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert (
        "message must not be recorded"
        not in serialized
    )
    assert "REDACTED_AUTH" not in serialized
    assert "REDACTED_TARGET" not in serialized


def test_revised_transport_uses_urllib_no_redirect() -> None:
    source = RUNNER.read_text(
        encoding="utf-8"
    )

    assert "urllib_single_get_transport" in source
    assert "NoRedirectHandler" in source
    assert "automatic_retry_count" in source
    assert "http.client.HTTPSConnection" not in source


def test_diagnostic_failure_stage() -> None:
    value = load(DIAGNOSTIC)

    assert value[
        "m27_preflight_passed"
    ] is False
    assert value[
        "local_integrity_gate_passed"
    ] is True
    assert value[
        "failure_stage"
    ] == (
        "AFTER_REQUEST_SENT_BEFORE_RESPONSE_HEADERS"
    )
    assert value[
        "get_request_count"
    ] == 1
    assert value[
        "automatic_retry_count"
    ] == 0


def test_plan_remains_non_executable() -> None:
    value = load(PLAN)

    assert value[
        "network_execution_authorized"
    ] is False
    assert value[
        "wordpress_update_authorized"
    ] is False
    assert value[
        "authorization_consumption_authorized"
    ] is False
    assert value[
        "maximum_get_request_count"
    ] == 1
    assert value[
        "automatic_retry_allowed"
    ] is False


def test_result_safety_boundary() -> None:
    value = load(RESULT)

    assert value[
        "dns_resolution_performed"
    ] is False
    assert value[
        "network_connection_performed"
    ] is False
    assert value[
        "http_request_performed"
    ] is False
    assert value[
        "wordpress_access_performed"
    ] is False
    assert value[
        "wordpress_write_performed"
    ] is False
    assert value[
        "wordpress_update_performed"
    ] is False
    assert value[
        "authorization_consumed"
    ] is False
    assert value[
        "execution_allowed"
    ] is False
    assert value[
        "production_status"
    ] == "NO_GO"


def test_evidence_contains_no_secret_output() -> None:
    combined = (
        DIAGNOSTIC.read_text(
            encoding="utf-8"
        )
        + PLAN.read_text(
            encoding="utf-8"
        )
        + RESULT.read_text(
            encoding="utf-8"
        )
    )

    assert "WORDPRESS_APP_PASSWORD" not in combined
    assert '"Authorization"' not in combined
    assert "Basic " not in combined
    assert "https://" not in combined
    assert "http://" not in combined
