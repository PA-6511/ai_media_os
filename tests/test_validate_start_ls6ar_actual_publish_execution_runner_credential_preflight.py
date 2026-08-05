from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6ar_actual_publish_execution_runner_credential_preflight import main as run_main
from scripts.validate_start_ls6ar_actual_publish_execution_runner_credential_preflight import (
    STATUS_NOT_READY,
    STATUS_VALIDATED,
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
        "run_output": tmp_path / "exchange/logs/preflight_result.json",
        "run_report": tmp_path / "reports/preflight_report.md",
        "validation_output": tmp_path / "exchange/logs/validation_result.json",
        "validation_report": tmp_path / "reports/validation_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AR",
            "execution_mode": "CREDENTIAL_PREFLIGHT_ONLY_NO_PUBLISH",
            "target_post": {"post_id": 183},
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
            "must_remain_false_flags": {
                "credential_values_loaded_for_output": False,
                "credential_values_persisted": False,
                "credential_values_logged": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_generated": False,
                "authorization_header_output": False,
                "basic_auth_string_generated": False,
                "basic_auth_string_output": False,
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
                "wordpress_post_executed": False,
                "wordpress_put_executed": False,
                "wordpress_patch_executed": False,
                "wordpress_delete_executed": False,
                "wordpress_write_executed_by_this_phase": False,
                "wordpress_publish_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "post119_update_executed": False,
                "actual_publish_execution_runner_credential_preflight_consumed": False,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "actual_publish_execution_runner_network_call_enabled": False,
                "actual_publish_execution_runner_credential_read_enabled": False,
                "actual_publish_execution_runner_publish_enabled": False,
                "actual_publish_execution_runner_execution_enabled": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
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

    write_json(
        files["ls6aq_boundary"],
        {
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
        },
    )
    write_json(files["ls6aq_lock"], {"locked": True, "post_id": 183})
    write_json(
        files["ls6aq_run"],
        {
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
        },
    )
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


def run_build_argv(files: dict[str, Path]) -> list[str]:
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
        "--output", str(files["run_output"]),
        "--report", str(files["run_report"]),
        "--record-credential-preflight",
        "--allow-credential-env-read",
        "--require-no-wordpress-api",
        "--require-no-publish",
        "--require-no-runner-execution",
        "--require-no-secret-output",
    ]


def validate_build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--credential-preflight-result", str(files["preflight_output"]),
        "--credential-preflight-lock", str(files["preflight_lock_output"]),
        "--run-result", str(files["run_output"]),
        "--ls6aq-boundary-result", str(files["ls6aq_boundary"]),
        "--ls6aq-boundary-lock", str(files["ls6aq_lock"]),
        "--ls6aq-validation-result", str(files["ls6aq_validation"]),
        "--output", str(files["validation_output"]),
        "--report", str(files["validation_report"]),
    ]


def run_phase(monkeypatch, files: dict[str, Path]) -> None:
    monkeypatch.setattr("sys.argv", run_build_argv(files))
    rc = run_main()
    assert rc == 0


def validate_phase(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", validate_build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["validation_output"])


def mutate_both(files: dict[str, Path], keys: tuple[str, ...], value) -> None:
    mutate(files["preflight_output"], keys, value)
    mutate(files["run_output"], keys, value)


def test_37_validation_valid_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_38_validation_detects_missing_preflight_result(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["preflight_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_39_validation_detects_missing_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["preflight_lock_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_40_validation_detects_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["run_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "keys,value",
    [
        (("actual_publish_execution_runner_credential_preflight_consumed",), True),
        (("actual_publish_execution_runner_final_boundary_consumed",), True),
        (("credential_env_read_allowed_by_this_phase",), False),
        (("credential_env_read_executed",), False),
        (("credential_env_exists",), False),
        (("credential_env_readable",), False),
        (("credential_required_keys_present",), False),
        (("credential_required_keys_non_empty",), False),
        (("credential_values_persisted",), True),
        (("credential_values_logged",), True),
        (("credential_value_output",), True),
        (("credential_secret_output",), True),
        (("secret_length_output",), True),
        (("secret_hash_output",), True),
        (("authorization_header_generated",), True),
        (("authorization_header_output",), True),
        (("basic_auth_string_generated",), True),
        (("basic_auth_string_output",), True),
        (("wordpress_api_call_executed",), True),
        (("wordpress_get_executed",), True),
        (("wordpress_post_executed",), True),
        (("wordpress_write_executed_by_this_phase",), True),
        (("wordpress_publish_executed",), True),
        (("publish_executed",), True),
        (("actual_publish_execution_runner_executed",), True),
        (("manual_publish_executed",), True),
        (("actual_publish_execution_allowed_by_this_phase",), True),
        (("actual_runner_execution_allowed_by_this_phase",), True),
        (("rerun_allowed",), True),
    ],
)
def test_41_to_69_validation_detects_flag_violations(
    monkeypatch, tmp_path: Path, keys: tuple[str, ...], value
) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_both(files, keys, value)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_70_validation_detects_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_both(files, ("next_phase", "phase"), "WRONG")
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_71_validation_detects_publish_execution_still_blocked_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_both(files, ("publish_execution_still_blocked",), False)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_72_source_code_has_no_requests_call() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "requests." not in (run_src + val_src)


def test_73_source_code_has_no_urllib_request() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "urllib.request" not in (run_src + val_src)


def test_74_source_code_has_no_wp_json() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "wp-json" not in (run_src + val_src)


def test_75_source_code_has_no_wp_v2_posts() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "/wp/v2/posts" not in (run_src + val_src)


def test_76_source_code_has_no_authorization_generation() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "Authorization" not in (run_src + val_src)


def test_77_source_code_has_no_basic_generation() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    assert "Basic " not in (run_src + val_src)


def test_78_source_code_has_no_base64_usage() -> None:
    run_src = Path("/home/deploy/ai_media_os/scripts/run_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    val_src = Path("/home/deploy/ai_media_os/scripts/validate_start_ls6ar_actual_publish_execution_runner_credential_preflight.py").read_text(encoding="utf-8")
    merged = run_src + val_src
    assert "base64" not in merged
    assert "b64encode" not in merged
