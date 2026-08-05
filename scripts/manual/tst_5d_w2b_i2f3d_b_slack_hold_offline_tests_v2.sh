#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="/home/deploy/ai_media_os"

I2E_ROOT_REL="exchange/review_evidence/slack_worker_release_rebinding/slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133/tst-5d-w2b-i2e-baseline-absorption-rereview-20260725T141632"
INVENTORY_ROOT_REL="${I2E_ROOT_REL}/i2f3d-a-slack-hold-remediation-test-inventory-20260725T162021-495991"
DECISION_ROOT_REL="${I2E_ROOT_REL}/i2f3c-c-human-review-decision-record-20260725T161539-495634"

INVENTORY_RESULT="${REPO_ROOT}/${INVENTORY_ROOT_REL}/result.json"
INVENTORY_JSON="${REPO_ROOT}/${INVENTORY_ROOT_REL}/slack-hold-remediation-test-inventory.json"
IMPLEMENTATION_PLAN="${REPO_ROOT}/${INVENTORY_ROOT_REL}/offline-test-implementation-plan.json"
MATCHING_TESTS="${REPO_ROOT}/${INVENTORY_ROOT_REL}/matching-test-files.txt"
INVENTORY_EVIDENCE_MANIFEST="${REPO_ROOT}/${INVENTORY_ROOT_REL}/inventory-evidence-manifest.txt"
DECISION_RESULT="${REPO_ROOT}/${DECISION_ROOT_REL}/result.json"

EXPECTED_INVENTORY_RESULT_SHA="43324aacece6135b4bc09f30248c1067390156f62740208d5914e709026269bf"
EXPECTED_INVENTORY_JSON_SHA="a25a12c202619e8c4f377e733a9f3d01fd5d380f3bf5e9cf6cbff60308133632"
EXPECTED_IMPLEMENTATION_PLAN_SHA="dc673d75e41687c38b72c4e5d2309d79a2c42676f785d636588a49bd511de8db"
EXPECTED_INVENTORY_EVIDENCE_MANIFEST_SHA="1a52fb42fec4f996e894522dcf290f0a6e1a8abf5a50b8acf05e994f417404d5"
EXPECTED_DECISION_RESULT_SHA="1790eedbf06d94c29c7dbe03e7aa3dd9bea4b4343f5cd3a1c4ea42d6ed732cba"

SLACK_SOURCE="${REPO_ROOT}/scripts/run_slack_approval_socket.py"
WORKFLOW_SOURCE="${REPO_ROOT}/app/db/repositories/workflow_state_repository.py"
PRODUCTION_MANIFEST="${REPO_ROOT}/config/slack_worker_release_source_manifest.json"
DB_PATH="${REPO_ROOT}/data/database/ebook_affiliate.db"

EXPECTED_SLACK_SOURCE_SHA="c2ab37a7e86fbdca79a456ed17a8c55b20fdd0dc0f8e1f3b426f0ba75cebe3e6"
EXPECTED_WORKFLOW_SOURCE_SHA="00241611109dc51d44c8e23f2b0940c10f5488bf7cd4061597284679bdcfd90e"
EXPECTED_PRODUCTION_MANIFEST_SHA="ea201edeba978e1d0b3cf6219cc16efac8641567216885c5a245c66e99fc9c2d"
EXPECTED_DB_SHA="1a421bd32edf1e9eedebc90cfd1b588b1ca0745670c6372c146a99b154e374e9"

sha256_file() {
    sha256sum "$1" | awk '{print $1}'
}

require_file_sha() {
    local path="$1"
    local expected="$2"
    local actual

    if [[ ! -f "$path" ]]; then
        printf 'ERROR=MISSING_FILE:%s\n' "$path" >&2
        exit 1
    fi

    actual="$(sha256_file "$path")"
    if [[ "$actual" != "$expected" ]]; then
        printf 'ERROR=SHA_MISMATCH:%s\nEXPECTED=%s\nACTUAL=%s\n' \
            "$path" "$expected" "$actual" >&2
        exit 1
    fi

    printf 'SHA_PASS=%s:%s\n' "$path" "$actual"
}

cd "$REPO_ROOT"

require_file_sha "$INVENTORY_RESULT" "$EXPECTED_INVENTORY_RESULT_SHA"
require_file_sha "$INVENTORY_JSON" "$EXPECTED_INVENTORY_JSON_SHA"
require_file_sha "$IMPLEMENTATION_PLAN" "$EXPECTED_IMPLEMENTATION_PLAN_SHA"
require_file_sha \
    "$INVENTORY_EVIDENCE_MANIFEST" \
    "$EXPECTED_INVENTORY_EVIDENCE_MANIFEST_SHA"
require_file_sha "$DECISION_RESULT" "$EXPECTED_DECISION_RESULT_SHA"

require_file_sha "$SLACK_SOURCE" "$EXPECTED_SLACK_SOURCE_SHA"
require_file_sha "$WORKFLOW_SOURCE" "$EXPECTED_WORKFLOW_SOURCE_SHA"
require_file_sha \
    "$PRODUCTION_MANIFEST" \
    "$EXPECTED_PRODUCTION_MANIFEST_SHA"
require_file_sha "$DB_PATH" "$EXPECTED_DB_SHA"

python3 - "$INVENTORY_JSON" <<'PY'
import json
import sys

path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))

if data.get("result") != "PASS_SLACK_HOLD_REMEDIATION_INVENTORY_READY":
    raise SystemExit("INVENTORY_RESULT_INVALID")
if data.get("gaps", {}).get(
    "slack_bolt_import_error_fixed_error_test_missing"
) is not True:
    raise SystemExit("IMPORT_ERROR_GAP_NOT_CONFIRMED")
if data.get("gaps", {}).get(
    "production_default_factory_equivalence_test_missing"
) is not True:
    raise SystemExit("FACTORY_EQUIVALENCE_GAP_NOT_CONFIRMED")
if data.get("governance", {}).get("unit_slack_runtime") != (
    "HOLD_PENDING_OFFLINE_FOCUSED_TESTS"
):
    raise SystemExit("SLACK_HOLD_STATE_INVALID")
if data.get("governance", {}).get("overall_candidate_decision") != "HOLD":
    raise SystemExit("OVERALL_DECISION_INVALID")
PY

RUN_ID="$(date +%Y%m%dT%H%M%S)-$$"
SHADOW_ROOT="/tmp/tst-5d-w2b-i2f3d-b-slack-offline-tests-${RUN_ID}"
EVIDENCE_REL="${I2E_ROOT_REL}/i2f3d-b-slack-hold-offline-tests-${RUN_ID}"
EVIDENCE_ROOT="${REPO_ROOT}/${EVIDENCE_REL}"

if [[ -e "$SHADOW_ROOT" ]]; then
    printf 'ERROR=SHADOW_ROOT_EXISTS:%s\n' "$SHADOW_ROOT" >&2
    exit 1
fi
if [[ -e "$EVIDENCE_ROOT" ]]; then
    printf 'ERROR=EVIDENCE_ROOT_EXISTS:%s\n' "$EVIDENCE_REL" >&2
    exit 1
fi

mkdir -p "$SHADOW_ROOT/tests" "$EVIDENCE_ROOT/shadow-test-snapshot"

SHADOW_TEST="${SHADOW_ROOT}/tests/test_slack_approval_socket_hold_remediation_offline.py"

cat > "$SHADOW_TEST" <<'PY'
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


REPO_ROOT = Path("/home/deploy/ai_media_os")
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

    monkeypatch.setattr(sys, "argv", [str(SOURCE_PATH)])
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

    monkeypatch.setattr(sys, "argv", [str(SOURCE_PATH)])
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
PY

chmod 0444 "$SHADOW_TEST"

SHADOW_TEST_SHA="$(sha256_file "$SHADOW_TEST")"

python3 -m py_compile "$SHADOW_TEST"

COLLECT_LOG="${EVIDENCE_ROOT}/pytest-collect.log"
FOCUSED_LOG="${EVIDENCE_ROOT}/pytest-focused.log"
RELATED_LOG="${EVIDENCE_ROOT}/pytest-related.log"
SUMMARY_JSON="${EVIDENCE_ROOT}/offline-test-summary.json"

set +e
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$REPO_ROOT" \
pytest \
    --collect-only \
    -q \
    "$SHADOW_TEST" \
    >"$COLLECT_LOG" 2>&1
COLLECT_RC=$?
set -e

cat "$COLLECT_LOG"

if [[ "$COLLECT_RC" -ne 0 ]]; then
    printf 'RESULT=BLOCKED_W2B_I2F3D_B_COLLECT_FAILED\n'
    printf 'COLLECT_EXIT_CODE=%s\n' "$COLLECT_RC"
    printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'UNIT_SLACK_RUNTIME=HOLD_PENDING_OFFLINE_FOCUSED_TESTS\n'
    exit "$COLLECT_RC"
fi

set +e
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$REPO_ROOT" \
pytest \
    -q \
    "$SHADOW_TEST" \
    >"$FOCUSED_LOG" 2>&1
FOCUSED_RC=$?
set -e

cat "$FOCUSED_LOG"

if [[ "$FOCUSED_RC" -ne 0 ]]; then
    printf 'RESULT=BLOCKED_W2B_I2F3D_B_FOCUSED_TESTS_FAILED\n'
    printf 'FOCUSED_EXIT_CODE=%s\n' "$FOCUSED_RC"
    printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_SLACK_RUNTIME=HOLD_PENDING_OFFLINE_FOCUSED_TESTS\n'
    exit "$FOCUSED_RC"
fi

mapfile -t RELATED_TEST_FILES < <(
    awk 'NF {print $1}' "$MATCHING_TESTS" \
        | while IFS= read -r path; do
            if [[ -f "${REPO_ROOT}/${path}" ]]; then
                printf '%s\n' "${REPO_ROOT}/${path}"
            fi
        done \
        | LC_ALL=C sort -u
)

if [[ "${#RELATED_TEST_FILES[@]}" -gt 0 ]]; then
    set +e
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$REPO_ROOT" \
    pytest \
        -q \
        "${RELATED_TEST_FILES[@]}" \
        >"$RELATED_LOG" 2>&1
    RELATED_RC=$?
    set -e
else
    printf 'NO_RELATED_TEST_FILES_DISCOVERED\n' >"$RELATED_LOG"
    RELATED_RC=0
fi

cat "$RELATED_LOG"

if [[ "$RELATED_RC" -ne 0 ]]; then
    printf 'RESULT=BLOCKED_W2B_I2F3D_B_RELATED_TESTS_FAILED\n'
    printf 'RELATED_EXIT_CODE=%s\n' "$RELATED_RC"
    printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
    printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
    printf 'FAILED_EVIDENCE_PRESERVED=true\n'
    printf 'UNIT_SLACK_RUNTIME=HOLD_PENDING_OFFLINE_FOCUSED_TESTS\n'
    exit "$RELATED_RC"
fi

cp --preserve=mode,timestamps \
    "$SHADOW_TEST" \
    "$EVIDENCE_ROOT/shadow-test-snapshot/test_slack_approval_socket_hold_remediation_offline.py"

python3 - \
    "$SHADOW_TEST" \
    "$COLLECT_LOG" \
    "$FOCUSED_LOG" \
    "$RELATED_LOG" \
    "$MATCHING_TESTS" \
    "$SUMMARY_JSON" <<'PY'
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

test_path = Path(sys.argv[1])
collect_log = Path(sys.argv[2])
focused_log = Path(sys.argv[3])
related_log = Path(sys.argv[4])
matching_tests = Path(sys.argv[5])
summary_path = Path(sys.argv[6])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


tree = ast.parse(test_path.read_text(encoding="utf-8"))
test_names = [
    node.name
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name.startswith("test_")
]

focused_text = focused_log.read_text(encoding="utf-8", errors="replace")
related_text = related_log.read_text(encoding="utf-8", errors="replace")

focused_match = re.search(r"(\d+)\s+passed", focused_text)
related_match = re.search(r"(\d+)\s+passed", related_text)

summary = {
    "schema_version": "1.0",
    "phase": "TST-5D-W2B-I2F-3D-B",
    "result": "PASS_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS",
    "shadow_test": {
        "path": str(test_path),
        "sha256": sha(test_path),
        "test_names": test_names,
        "test_count": len(test_names),
    },
    "pytest": {
        "collect_log_sha256": sha(collect_log),
        "focused_log_sha256": sha(focused_log),
        "related_log_sha256": sha(related_log),
        "focused_passed_count": (
            int(focused_match.group(1)) if focused_match else None
        ),
        "related_passed_count": (
            int(related_match.group(1)) if related_match else 0
        ),
        "collect_exit_code": 0,
        "focused_exit_code": 0,
        "related_exit_code": 0,
    },
    "hold_conditions": {
        "slack_bolt_import_error_fixed_error": "PASS",
        "main_returns_3_on_dependency_error": "PASS",
        "handler_start_not_reached_on_dependency_error": "PASS",
        "database_session_not_created_on_dependency_error": "PASS",
        "production_default_app_factory_arguments": "PASS",
        "production_default_handler_factory_arguments": "PASS",
        "handler_start_exactly_once": "PASS",
        "handler_close_at_most_once": "PASS",
        "sigterm_handler_restored": "PASS",
    },
    "boundaries": {
        "production_runtime_source_modified": False,
        "production_test_file_created": False,
        "production_database_opened": False,
        "credential_content_read": False,
        "external_network_used": False,
        "deployment_performed": False,
    },
    "matching_test_inventory_sha256": sha(matching_tests),
    "unit_slack_runtime": "READY_FOR_HUMAN_REREVIEW_NOT_APPROVED",
    "overall_candidate_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "next_phase": (
        "TST-5D-W2B-I2F-3D-C_SLACK_HOLD_REMEDIATION_"
        "OFFLINE_TEST_HUMAN_REREVIEW"
    ),
}

summary_path.write_text(
    json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY

python3 -m json.tool "$SUMMARY_JSON" >/dev/null

EVIDENCE_MANIFEST="${EVIDENCE_ROOT}/offline-test-evidence-manifest.txt"
(
    cd "$EVIDENCE_ROOT"
    find . -type f \
        ! -name 'offline-test-evidence-manifest.txt' \
        ! -name 'result.json' \
        -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 sha256sum
) > "$EVIDENCE_MANIFEST"
chmod 0444 "$EVIDENCE_MANIFEST"

COLLECT_LOG_SHA="$(sha256_file "$COLLECT_LOG")"
FOCUSED_LOG_SHA="$(sha256_file "$FOCUSED_LOG")"
RELATED_LOG_SHA="$(sha256_file "$RELATED_LOG")"
SUMMARY_SHA="$(sha256_file "$SUMMARY_JSON")"
EVIDENCE_MANIFEST_SHA="$(sha256_file "$EVIDENCE_MANIFEST")"

FOCUSED_PASSED="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["pytest"]["focused_passed_count"])' \
        "$SUMMARY_JSON"
)"
RELATED_PASSED="$(
    python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["pytest"]["related_passed_count"])' \
        "$SUMMARY_JSON"
)"

SLACK_SOURCE_AFTER="$(sha256_file "$SLACK_SOURCE")"
WORKFLOW_SOURCE_AFTER="$(sha256_file "$WORKFLOW_SOURCE")"
PRODUCTION_MANIFEST_AFTER="$(sha256_file "$PRODUCTION_MANIFEST")"
DB_AFTER="$(sha256_file "$DB_PATH")"
DECISION_RESULT_AFTER="$(sha256_file "$DECISION_RESULT")"
INVENTORY_RESULT_AFTER="$(sha256_file "$INVENTORY_RESULT")"

[[ "$SLACK_SOURCE_AFTER" == "$EXPECTED_SLACK_SOURCE_SHA" ]] || {
    printf 'ERROR=SLACK_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$WORKFLOW_SOURCE_AFTER" == "$EXPECTED_WORKFLOW_SOURCE_SHA" ]] || {
    printf 'ERROR=WORKFLOW_SOURCE_CHANGED\n' >&2
    exit 1
}
[[ "$PRODUCTION_MANIFEST_AFTER" == "$EXPECTED_PRODUCTION_MANIFEST_SHA" ]] || {
    printf 'ERROR=PRODUCTION_MANIFEST_CHANGED\n' >&2
    exit 1
}
[[ "$DB_AFTER" == "$EXPECTED_DB_SHA" ]] || {
    printf 'ERROR=PRODUCTION_DB_CHANGED\n' >&2
    exit 1
}
[[ "$DECISION_RESULT_AFTER" == "$EXPECTED_DECISION_RESULT_SHA" ]] || {
    printf 'ERROR=HUMAN_DECISION_RECORD_CHANGED\n' >&2
    exit 1
}
[[ "$INVENTORY_RESULT_AFTER" == "$EXPECTED_INVENTORY_RESULT_SHA" ]] || {
    printf 'ERROR=INVENTORY_RESULT_CHANGED\n' >&2
    exit 1
}

RESULT_JSON="${EVIDENCE_ROOT}/result.json"
cat > "$RESULT_JSON" <<JSON
{
  "schema_version": "1.0",
  "phase": "TST-5D-W2B-I2F-3D-B",
  "result": "PASS_W2B_I2F3D_B_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS",
  "shadow_root": "${SHADOW_ROOT}",
  "shadow_test_path": "${SHADOW_TEST}",
  "shadow_test_sha256": "${SHADOW_TEST_SHA}",
  "evidence_root": "${EVIDENCE_REL}",
  "pytest": {
    "collect_exit_code": ${COLLECT_RC},
    "focused_exit_code": ${FOCUSED_RC},
    "related_exit_code": ${RELATED_RC},
    "focused_passed_count": ${FOCUSED_PASSED},
    "related_passed_count": ${RELATED_PASSED},
    "collect_log_sha256": "${COLLECT_LOG_SHA}",
    "focused_log_sha256": "${FOCUSED_LOG_SHA}",
    "related_log_sha256": "${RELATED_LOG_SHA}"
  },
  "hold_conditions": {
    "slack_bolt_import_error_fixed_error": "PASS",
    "production_default_factory_equivalence": "PASS",
    "handler_lifecycle_offline": "PASS"
  },
  "artifacts": {
    "offline_test_summary_sha256": "${SUMMARY_SHA}",
    "offline_test_evidence_manifest_sha256": "${EVIDENCE_MANIFEST_SHA}"
  },
  "execution": {
    "shadow_test_created": true,
    "production_test_file_created": false,
    "production_runtime_source_modified": false,
    "pytest_executed": true,
    "production_database_opened": false,
    "credential_content_read": false,
    "external_network_used": false
  },
  "governance": {
    "unit_slack_runtime": "READY_FOR_HUMAN_REREVIEW_NOT_APPROVED",
    "overall_candidate_decision": "HOLD",
    "release_status": "CANDIDATE_NOT_APPROVED",
    "production_approval_created": false,
    "production_manifest_update_allowed": false,
    "production_database_access_allowed": false,
    "production_migration_allowed": false,
    "deployment_allowed": false,
    "runtime_execution_allowed": false,
    "external_network_allowed": false
  },
  "safety": {
    "slack_source_changed": false,
    "workflow_source_changed": false,
    "human_decision_record_changed": false,
    "inventory_result_changed": false,
    "production_manifest_changed": false,
    "production_database_content_changed": false,
    "production_database_sql_connection_used": false,
    "migration_applied": false,
    "deployment_performed": false,
    "external_network_used": false
  },
  "next_phase": "TST-5D-W2B-I2F-3D-C_SLACK_HOLD_REMEDIATION_OFFLINE_TEST_HUMAN_REREVIEW",
  "completed_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON

RESULT_SHA="$(sha256_file "$RESULT_JSON")"

printf '\nRESULT=PASS_W2B_I2F3D_B_SLACK_HOLD_REMEDIATION_OFFLINE_TESTS\n'
printf 'SHADOW_ROOT=%s\n' "$SHADOW_ROOT"
printf 'SHADOW_TEST_PATH=%s\n' "$SHADOW_TEST"
printf 'SHADOW_TEST_SHA=%s\n' "$SHADOW_TEST_SHA"
printf 'EVIDENCE_ROOT=%s\n' "$EVIDENCE_REL"
printf 'FOCUSED_TEST_PASSED_COUNT=%s\n' "$FOCUSED_PASSED"
printf 'RELATED_TEST_PASSED_COUNT=%s\n' "$RELATED_PASSED"
printf 'SLACK_BOLT_IMPORT_ERROR_FIXED_ERROR=PASS\n'
printf 'PRODUCTION_DEFAULT_FACTORY_EQUIVALENCE=PASS\n'
printf 'HANDLER_LIFECYCLE_OFFLINE=PASS\n'
printf 'OFFLINE_TEST_SUMMARY_SHA=%s\n' "$SUMMARY_SHA"
printf 'EVIDENCE_MANIFEST_SHA=%s\n' "$EVIDENCE_MANIFEST_SHA"
printf 'RESULT_SHA=%s\n' "$RESULT_SHA"
printf 'SHADOW_TEST_CREATED=true\n'
printf 'PRODUCTION_TEST_FILE_CREATED=false\n'
printf 'PRODUCTION_RUNTIME_SOURCE_MODIFIED=false\n'
printf 'PYTEST_EXECUTED=true\n'
printf 'PRODUCTION_DB_OPENED=false\n'
printf 'PRODUCTION_DB_SQL_CONNECTION_USED=false\n'
printf 'CREDENTIAL_CONTENT_READ=false\n'
printf 'EXTERNAL_NETWORK_USED=false\n'
printf 'HUMAN_DECISION_RECORD_CHANGED=false\n'
printf 'INVENTORY_RESULT_CHANGED=false\n'
printf 'PRODUCTION_MANIFEST_CHANGED=false\n'
printf 'PRODUCTION_DB_CONTENT_CHANGED=false\n'
printf 'PRODUCTION_MIGRATION_APPLIED=false\n'
printf 'DEPLOYMENT_PERFORMED=false\n'
printf 'UNIT_SLACK_RUNTIME=READY_FOR_HUMAN_REREVIEW_NOT_APPROVED\n'
printf 'OVERALL_CANDIDATE_DECISION=HOLD\n'
printf 'RELEASE_STATUS=CANDIDATE_NOT_APPROVED\n'
printf 'NEXT_PHASE=TST-5D-W2B-I2F-3D-C_SLACK_HOLD_REMEDIATION_OFFLINE_TEST_HUMAN_REREVIEW\n'
printf 'SCRIPT_EXIT_CODE=0\n'
