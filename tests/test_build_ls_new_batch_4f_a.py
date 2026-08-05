from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_credential_fixture_validator_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_credential_fixture_validation_request.example.json"
)
FIXTURE_PATH = (
    ROOT
    / "exchange/fixtures/credentials/"
    "wordpress-readonly-category.valid.fixture.env"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_credential_fixture_validation_result.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4f_a_credential_fixture_validator_report.md"
)
BUILDER_PATH = (
    ROOT / "scripts/build_ls_new_batch_4f_a.py"
)
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4f_a_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4f_a_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture(
    path: Path,
    content: str,
    mode: int = 0o600,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def valid_fixture_text() -> str:
    return (
        "WORDPRESS_BASE_URL=https://fixture.invalid\n"
        "WORDPRESS_READONLY_USERNAME=DUMMY_USER\n"
        "WORDPRESS_READONLY_APP_PASSWORD=DUMMY_PASSWORD\n"
    )


def test_policy_boundary_is_fixture_only() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4F-A"
    assert (
        boundary[
            "production_credential_content_read_allowed"
        ]
        is False
    )
    assert boundary["credential_value_output_allowed"] is False
    assert boundary["environment_variable_read_allowed"] is False
    assert boundary["network_connection_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_valid_fixture_mode_is_0600() -> None:
    assert FIXTURE_PATH.exists()
    assert (FIXTURE_PATH.stat().st_mode & 0o777) == 0o600


def test_result_contains_no_secret_values() -> None:
    result = load_json(RESULT_PATH)
    serialized = json.dumps(result, ensure_ascii=False)

    assert "DUMMY_APP_PASSWORD" not in serialized
    assert "DUMMY_READONLY_USER" not in serialized
    assert result["credential_values_output"] is False
    assert result["value_lengths_output"] is False
    assert result["value_hashes_output"] is False


def test_valid_fixture_generates_sanitized_package() -> None:
    package = load_json(OUTPUT_PATH)
    validation = package["fixture_validation"]

    assert validation["exists"] is True
    assert validation["regular_file"] is True
    assert validation["mode_octal"] == "0600"
    assert validation["missing_keys"] == []
    assert validation["unknown_keys"] == []
    assert validation["duplicate_keys"] == []
    assert validation["empty_value_keys"] == []
    assert validation["values_output"] is False


def test_missing_key_is_rejected(tmp_path: Path) -> None:
    builder = load_builder()
    fixture = tmp_path / "missing.env"

    write_fixture(
        fixture,
        (
            "WORDPRESS_BASE_URL=https://fixture.invalid\n"
            "WORDPRESS_READONLY_USERNAME=DUMMY_USER\n"
        ),
    )

    try:
        builder.parse_fixture(
            fixture,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "required fixture keys missing" in str(exc)
    else:
        raise AssertionError("missing key was accepted")


def test_duplicate_key_is_rejected(tmp_path: Path) -> None:
    builder = load_builder()
    fixture = tmp_path / "duplicate.env"

    write_fixture(
        fixture,
        valid_fixture_text()
        + "WORDPRESS_READONLY_USERNAME=SECOND_VALUE\n",
    )

    try:
        builder.parse_fixture(
            fixture,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "duplicate fixture keys" in str(exc)
    else:
        raise AssertionError("duplicate key was accepted")


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    builder = load_builder()
    fixture = tmp_path / "unknown.env"

    write_fixture(
        fixture,
        valid_fixture_text() + "UNKNOWN_KEY=value\n",
    )

    try:
        builder.parse_fixture(
            fixture,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "unknown fixture keys" in str(exc)
    else:
        raise AssertionError("unknown key was accepted")


def test_empty_value_is_rejected(tmp_path: Path) -> None:
    builder = load_builder()
    fixture = tmp_path / "empty.env"

    write_fixture(
        fixture,
        (
            "WORDPRESS_BASE_URL=https://fixture.invalid\n"
            "WORDPRESS_READONLY_USERNAME=\n"
            "WORDPRESS_READONLY_APP_PASSWORD=DUMMY_PASSWORD\n"
        ),
    )

    try:
        builder.parse_fixture(
            fixture,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "empty fixture values" in str(exc)
    else:
        raise AssertionError("empty value was accepted")


def test_insecure_mode_is_rejected(tmp_path: Path) -> None:
    builder = load_builder()
    fixture = tmp_path / "mode.env"

    write_fixture(
        fixture,
        valid_fixture_text(),
        mode=0o644,
    )

    try:
        builder.parse_fixture(
            fixture,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "mode must be 0600" in str(exc)
    else:
        raise AssertionError("mode 0644 was accepted")


def test_production_path_request_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["fixture_path"] = (
        "/etc/ai-media-os/"
        "wordpress-readonly-category.env"
    )

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "production credential path is forbidden" in str(
            exc
        )
    else:
        raise AssertionError(
            "production credential path was accepted"
        )


def test_fixture_root_escape_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["fixture_path"] = (
        "exchange/examples/"
        "new_release_wp_read_only_lookup_"
        "preflight_request.example.json"
    )

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "escapes allowed fixture root" in str(exc)
    else:
        raise AssertionError("fixture-root escape was accepted")


def test_execution_runner_remains_blocked() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    result = json.loads(completed.stderr)

    assert result["status"] == "BLOCKED_FIXTURE_BASELINE_ONLY"
    assert result["dummy_fixture_validated"] is True
    assert (
        result["production_credential_path_touched"]
        is False
    )
    assert result["credential_values_loaded"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_CREDENTIAL_PRESENCE_FIXTURE_BASELINE"
    )
    assert (
        result["decision"]
        == "READ_ONLY_CREDENTIAL_STRUCTURE_FIXED"
    )
    assert result["fixture_mode_octal"] == "0600"
    assert result["required_keys_present"] is True
    assert result["production_credential_path_touched"] is False
    assert result["ready_for_ls_new_batch_4f_b"] is True
    assert (
        result[
            "ready_for_production_credential_presence_check"
        ]
        is False
    )
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Credential values output: `false`" in report
    assert "Production credential path touched: `false`" in report
    assert "WordPress API call allowed: `false`" in report
    assert "Execution allowed: `false`" in report
