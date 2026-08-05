from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.run_start_ls6ar_actual_publish_execution_runner_credential_preflight import (
    STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG,
    STATUS_MISSING_NO_PUBLISH_FLAG,
    STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG,
    STATUS_MISSING_NO_SECRET_OUTPUT_FLAG,
    STATUS_MISSING_NO_WORDPRESS_API_FLAG,
    STATUS_MISSING_RECORD_FLAG,
    STATUS_PASSED,
    main,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, keys: tuple[str, ...], value) -> None:
    data = read_json(path)
    cur = data
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, data)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6aq_boundary": tmp_path / "exchange/runtime/ls6aq_boundary.json",
        "ls6aq_lock": tmp_path / "exchange/locks/ls6aq_boundary.lock.json",
        "ls6aq_run": tmp_path / "exchange/logs/ls6aq_run.json",
        "ls6aq_validation": tmp_path / "exchange/logs/ls6aq_validation.json",
        "credential_env": tmp_path / "etc/credential.env",
        "preflight_output": tmp_path / "exchange/runtime/preflight_result.json",
        "preflight_lock_output": tmp_path / "exchange/locks/preflight_lock.json",
        "output": tmp_path / "exchange/logs/preflight_result.json",
        "report": tmp_path / "reports/preflight_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AR",
            "execution_mode": "CREDENTIAL_PREFLIGHT_ONLY_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "credential_preflight": {
                "credential_env_path": "/etc/ai-media-os/credential.env",
                "required_key_names": [
                    "WORDPRESS_SITE_URL",
                    "WORDPRESS_USERNAME",
                    "WORDPRESS_APP_PASSWORD",
                ],
            },
            "required_previous_phase": {
                "ls6aq": {
                    "required_run_status": "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH",
                    "required_validation_status": "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH",
                    "required_post_id": 183,
                    "required_returned_post_status": "draft",
                    "required_final_boundary_ready": True,
                    "required_final_boundary_consumed": False,
                    "required_final_boundary_allows_execution_by_this_phase": False,
                    "required_credential_preflight_required": True,
                    "required_final_command_required": True,
                    "required_separate_publish_execution_phase_required": True,
                    "required_publish_execution_still_blocked": True,
                }
            },
            "credential_preflight_policy": {
                "actual_publish_execution_runner_credential_preflight_ready": True,
                "actual_publish_execution_runner_credential_preflight_consumed": False,
                "actual_publish_execution_runner_final_boundary_ready": True,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "credential_env_read_allowed_by_this_phase": True,
                "credential_env_read_executed": True,
                "credential_env_exists": True,
                "credential_env_readable": True,
                "credential_env_permission_checked": True,
                "credential_required_keys_present": True,
                "credential_required_keys_non_empty": True,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
            "next_phase": {
                "phase": "LS-6AS",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    boundary = {
        "status": "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_execution_runner_final_boundary_ready": True,
        "actual_publish_execution_runner_final_boundary_consumed": False,
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
        "actual_publish_execution_runner_credential_preflight_required": True,
        "actual_publish_execution_runner_final_command_required": True,
        "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
        "publish_execution_still_blocked": True,
    }
    write_json(files["ls6aq_boundary"], boundary)
    write_json(files["ls6aq_run"], dict(boundary))
    write_json(files["ls6aq_lock"], {"post_id": 183, "locked": True})
    write_json(
        files["ls6aq_validation"],
        {"status": "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH"},
    )

    files["credential_env"].parent.mkdir(parents=True, exist_ok=True)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://hoshido.jp\n"
        "WORDPRESS_USERNAME=ai_publisher\n"
        "WORDPRESS_APP_PASSWORD=dummy-secret\n",
        encoding="utf-8",
    )

    return files


def run_flags() -> list[str]:
    return [
        "--record-credential-preflight",
        "--allow-credential-env-read",
        "--require-no-wordpress-api",
        "--require-no-publish",
        "--require-no-runner-execution",
        "--require-no-secret-output",
    ]


def build_argv(files: dict[str, Path], extra_flags: list[str]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6aq-boundary-result", str(files["ls6aq_boundary"]),
        "--ls6aq-boundary-lock", str(files["ls6aq_lock"]),
        "--ls6aq-run-result", str(files["ls6aq_run"]),
        "--ls6aq-validation-result", str(files["ls6aq_validation"]),
        "--credential-env-path", str(files["credential_env"]),
        "--credential-preflight-output", str(files["preflight_output"]),
        "--credential-preflight-lock-output", str(files["preflight_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        *extra_flags,
    ]


def invoke(monkeypatch, files: dict[str, Path], extra_flags: list[str]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, extra_flags))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_01_missing_record_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--record-credential-preflight")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_RECORD_FLAG


def test_02_missing_allow_credential_read_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--allow-credential-env-read")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG


def test_03_missing_no_wordpress_api_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-wordpress-api")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_NO_WORDPRESS_API_FLAG


def test_04_missing_no_publish_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-publish")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_NO_PUBLISH_FLAG


def test_05_missing_no_runner_execution_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-runner-execution")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG


def test_06_missing_no_secret_output_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-secret-output")
    out = invoke(monkeypatch, files, flags)
    assert out["status"] == STATUS_MISSING_NO_SECRET_OUTPUT_FLAG


@pytest.mark.parametrize(
    "path,keys,value",
    [
        ("ls6aq_validation", ("status",), "BROKEN"),
        ("ls6aq_boundary", ("actual_publish_execution_runner_final_boundary_consumed",), True),
        ("ls6aq_boundary", ("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase",), True),
        ("ls6aq_boundary", ("actual_publish_execution_runner_credential_preflight_required",), False),
        ("ls6aq_boundary", ("actual_publish_execution_runner_final_command_required",), False),
        ("ls6aq_boundary", ("actual_publish_execution_runner_separate_publish_execution_phase_required",), False),
    ],
)
def test_07_to_12_previous_phase_violation_not_ready(
    monkeypatch, tmp_path: Path, path: str, keys: tuple[str, ...], value
) -> None:
    files = make_inputs(tmp_path)
    mutate(files[path], keys, value)
    out = invoke(monkeypatch, files, run_flags())
    assert out["status"] != STATUS_PASSED


def test_13_credential_env_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].unlink()
    out = invoke(monkeypatch, files, run_flags())
    assert out["status"] != STATUS_PASSED


def test_14_credential_env_unreadable_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    os.chmod(files["credential_env"], 0)
    try:
        out = invoke(monkeypatch, files, run_flags())
    finally:
        os.chmod(files["credential_env"], 0o600)
    assert out["status"] != STATUS_PASSED


def test_15_required_key_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://hoshido.jp\nWORDPRESS_USERNAME=ai_publisher\n",
        encoding="utf-8",
    )
    out = invoke(monkeypatch, files, run_flags())
    assert out["status"] != STATUS_PASSED


def test_16_required_key_empty_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_SITE_URL=https://hoshido.jp\n"
        "WORDPRESS_USERNAME=ai_publisher\n"
        "WORDPRESS_APP_PASSWORD=\n",
        encoding="utf-8",
    )
    out = invoke(monkeypatch, files, run_flags())
    assert out["status"] != STATUS_PASSED


def test_17_valid_credential_preflight_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["status"] == STATUS_PASSED


def test_18_result_keeps_credential_env_read_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["credential_env_read_executed"] is True


def test_19_result_keeps_credential_env_exists_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["credential_env_exists"] is True


def test_20_result_keeps_credential_env_readable_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["credential_env_readable"] is True


def test_21_result_keeps_required_keys_present_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["credential_required_keys_present"] is True


def test_22_result_keeps_required_keys_non_empty_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["credential_required_keys_non_empty"] is True


def test_23_result_does_not_include_credential_values(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files, run_flags())
    text = files["output"].read_text(encoding="utf-8")
    assert "dummy-secret" not in text


def test_24_result_does_not_include_credential_value_length(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["secret_length_output"] is False


def test_25_result_does_not_include_credential_hash(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["secret_hash_output"] is False


def test_26_result_keeps_authorization_header_generated_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["authorization_header_generated"] is False


def test_27_result_keeps_authorization_header_output_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["authorization_header_output"] is False


def test_28_result_keeps_basic_auth_string_generated_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["basic_auth_string_generated"] is False


def test_29_result_keeps_basic_auth_string_output_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["basic_auth_string_output"] is False


def test_30_result_keeps_wordpress_api_call_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["wordpress_api_call_executed"] is False


def test_31_result_keeps_wordpress_get_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["wordpress_get_executed"] is False


def test_32_result_keeps_wordpress_post_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["wordpress_post_executed"] is False


def test_33_result_keeps_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["publish_executed"] is False


def test_34_result_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["actual_publish_execution_runner_executed"] is False


def test_35_result_keeps_manual_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["manual_publish_executed"] is False


def test_36_result_next_phase_ls6as(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, run_flags())
    assert out["next_phase"]["phase"] == "LS-6AS"
