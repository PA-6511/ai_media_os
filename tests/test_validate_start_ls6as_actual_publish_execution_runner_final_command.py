from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6as_actual_publish_execution_runner_final_command import (
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_TEMPLATE_READY,
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


def build_fixtures(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "final_command": tmp_path / "exchange/human_review/final_command.json",
        "ls6ar_result": tmp_path / "exchange/runtime/ls6ar_result.json",
        "ls6ar_lock": tmp_path / "exchange/locks/ls6ar_lock.json",
        "ls6ar_run": tmp_path / "exchange/logs/ls6ar_run.json",
        "ls6ar_validation": tmp_path / "exchange/logs/ls6ar_validation.json",
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/output.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AS",
            "execution_mode": "FINAL_COMMAND_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "required_previous_phase": {
                "ls6ar": {
                    "required_run_status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_PASSED_NO_PUBLISH",
                    "required_validation_status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
                    "required_post_id": 183,
                    "required_returned_post_status": "draft",
                    "required_credential_preflight_ready": True,
                    "required_credential_preflight_consumed": False,
                    "required_final_boundary_ready": True,
                    "required_final_boundary_consumed": False,
                    "required_boundary_allows_execution_by_this_phase": False,
                    "required_credential_env_read_executed": True,
                    "required_credential_env_exists": True,
                    "required_credential_env_readable": True,
                    "required_credential_env_permission_checked": True,
                    "required_credential_required_keys_present": True,
                    "required_credential_required_keys_non_empty": True,
                    "required_no_credential_value_output": True,
                    "required_no_credential_value_persisted": True,
                    "required_no_secret_length_output": True,
                    "required_no_secret_hash_output": True,
                    "required_no_authorization_header_generated": True,
                    "required_no_basic_auth_string_generated": True,
                    "required_no_wordpress_api_call": True,
                    "required_no_publish": True,
                    "required_no_runner_execution": True,
                    "required_publish_execution_still_blocked": True,
                }
            },
            "final_command_policy": {
                "actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
                "actual_publish_execution_runner_final_command_consumed": False,
                "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": False,
                "actual_publish_execution_runner_final_command_approved_for_later_separated_phase": True,
                "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
            },
            "must_remain_false_flags": {
                "credential_env_read_executed_by_this_phase": False,
                "credential_env_read_executed": False,
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
                "actual_publish_execution_runner_final_command_consumed": False,
                "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": False,
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
                "phase": "LS-6AT",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_separate_publish_execution_phase": True,
                "requires_actual_publish_execution_runner_separated_execution": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    write_json(
        files["template"],
        {
            "phase": "LS-6AS",
            "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_TEMPLATE",
            "command_status": "TEMPLATE_NOT_CONFIRMED",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "final_command": {
                "actual_publish_execution_runner_final_command_label": "",
                "required_actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
                "command_reason": "",
                "actual_publish_execution_runner_final_command_consumed": False,
                "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": False,
                "actual_publish_execution_runner_final_command_approved_for_later_separated_phase": True,
                "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
                "actual_publish_execution_runner_credential_preflight_ready": True,
                "actual_publish_execution_runner_credential_preflight_consumed": False,
                "actual_publish_execution_runner_final_boundary_ready": True,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "ls6ar_credential_preflight_validated": True,
                "credential_env_read_executed_by_this_phase": False,
                "credential_env_read_executed": False,
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
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "requires_separate_publish_execution_phase": True,
                "requires_actual_publish_execution_runner_separated_execution": True,
                "publish_execution_still_blocked": True,
            },
            "current_phase_execution": {
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
                "actual_publish_execution_runner_network_call_enabled": False,
                "actual_publish_execution_runner_credential_read_enabled": False,
                "actual_publish_execution_runner_publish_enabled": False,
                "actual_publish_execution_runner_execution_enabled": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    write_json(
        files["final_command"],
        {
            "phase": "LS-6AS",
            "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND",
            "command_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "final_command": {
                "actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
                "required_actual_publish_execution_runner_final_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_EXECUTION_PHASE_ONLY",
                "command_reason": "record only",
                "actual_publish_execution_runner_final_command_consumed": False,
                "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": False,
                "actual_publish_execution_runner_final_command_approved_for_later_separated_phase": True,
                "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
                "actual_publish_execution_runner_credential_preflight_ready": True,
                "actual_publish_execution_runner_credential_preflight_consumed": False,
                "actual_publish_execution_runner_final_boundary_ready": True,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "ls6ar_credential_preflight_validated": True,
                "ls6ar_credential_env_read_executed": True,
                "credential_env_read_executed_by_this_phase": False,
                "credential_env_read_executed": False,
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
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "requires_separate_publish_execution_phase": True,
                "requires_actual_publish_execution_runner_separated_execution": True,
                "publish_execution_still_blocked": True,
            },
            "current_phase_execution": {
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
                "actual_publish_execution_runner_network_call_enabled": False,
                "actual_publish_execution_runner_credential_read_enabled": False,
                "actual_publish_execution_runner_publish_enabled": False,
                "actual_publish_execution_runner_execution_enabled": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    ls6ar_base = {
        "phase": "LS-6AR",
        "status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_PASSED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_execution_runner_credential_preflight_ready": True,
        "actual_publish_execution_runner_credential_preflight_consumed": False,
        "actual_publish_execution_runner_final_boundary_ready": True,
        "actual_publish_execution_runner_final_boundary_consumed": False,
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
        "credential_env_read_executed": True,
        "credential_env_exists": True,
        "credential_env_readable": True,
        "credential_env_permission_checked": True,
        "credential_required_keys_present": True,
        "credential_required_keys_non_empty": True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "basic_auth_string_generated": False,
        "wordpress_api_call_executed": False,
        "publish_executed": False,
        "actual_publish_execution_runner_executed": False,
        "publish_execution_still_blocked": True,
    }
    write_json(files["ls6ar_result"], ls6ar_base)
    write_json(files["ls6ar_run"], dict(ls6ar_base))
    write_json(
        files["ls6ar_validation"],
        {"status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH"},
    )
    write_json(files["ls6ar_lock"], {"locked": True})

    return files


def build_argv(files: dict[str, Path], allow_template: bool = False) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--template",
        str(files["template"]),
        "--final-command",
        str(files["final_command"]),
        "--ls6ar-credential-preflight-result",
        str(files["ls6ar_result"]),
        "--ls6ar-credential-preflight-lock",
        str(files["ls6ar_lock"]),
        "--ls6ar-run-result",
        str(files["ls6ar_run"]),
        "--ls6ar-validation-result",
        str(files["ls6ar_validation"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    if allow_template:
        argv.append("--allow-template")
    return argv


def run_phase(monkeypatch, files: dict[str, Path], allow_template: bool = False) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, allow_template=allow_template))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def mutate_ls6ar(files: dict[str, Path], keys: tuple[str, ...], value) -> None:
    mutate(files["ls6ar_result"], keys, value)
    mutate(files["ls6ar_run"], keys, value)


def mutate_final(files: dict[str, Path], keys: tuple[str, ...], value) -> None:
    mutate(files["final_command"], keys, value)


def test_1_allow_template_returns_template_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files, allow_template=True)
    assert out["status"] == STATUS_TEMPLATE_READY


def test_2_valid_final_command_returns_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_READY


def test_3_missing_policy_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["policy"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_4_missing_template_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["template"].unlink()
    out = run_phase(monkeypatch, files, allow_template=True)
    assert out["status"] == STATUS_NOT_READY


def test_5_missing_final_command_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["final_command"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_6_missing_ls6ar_result_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["ls6ar_result"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_7_missing_ls6ar_lock_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["ls6ar_lock"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_8_missing_ls6ar_run_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["ls6ar_run"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_9_missing_ls6ar_validation_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    files["ls6ar_validation"].unlink()
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_10_post_id_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    mutate_ls6ar(files, ("post_id",), 999)
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "keys,value",
    [
        (("returned_post_status",), "publish"),
        (("status",), "WRONG"),
        ((), None),
    ],
)
def test_11_to_13_status_and_returned_status_checks(monkeypatch, tmp_path: Path, keys: tuple[str, ...], value) -> None:
    files = build_fixtures(tmp_path)
    if keys:
        mutate_ls6ar(files, keys, value)
    else:
        mutate(files["ls6ar_validation"], ("status",), "WRONG")
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "keys,value",
    [
        (("actual_publish_execution_runner_credential_preflight_ready",), False),
        (("actual_publish_execution_runner_credential_preflight_consumed",), True),
        (("actual_publish_execution_runner_final_boundary_ready",), False),
        (("actual_publish_execution_runner_final_boundary_consumed",), True),
        (("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase",), True),
        (("credential_env_read_executed",), False),
        (("credential_env_exists",), False),
        (("credential_env_readable",), False),
        (("credential_required_keys_present",), False),
        (("credential_required_keys_non_empty",), False),
        (("credential_value_output",), True),
        (("credential_value_persisted",), True),
        (("secret_length_output",), True),
        (("secret_hash_output",), True),
        (("authorization_header_generated",), True),
        (("basic_auth_string_generated",), True),
    ],
)
def test_14_to_29_ls6ar_source_flag_checks(monkeypatch, tmp_path: Path, keys: tuple[str, ...], value) -> None:
    files = build_fixtures(tmp_path)
    mutate_ls6ar(files, keys, value)
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "keys,value",
    [
        (("final_command", "actual_publish_execution_runner_final_command_label"), "WRONG_LABEL"),
        (("final_command", "actual_publish_execution_runner_final_command_consumed"), True),
        (("final_command", "actual_publish_execution_runner_final_command_allows_execution_by_this_phase"), True),
        (("final_command", "actual_publish_execution_runner_final_command_approved_for_later_separated_phase"), False),
        (("final_command", "actual_publish_execution_runner_separate_publish_execution_phase_required"), False),
        (("final_command", "credential_env_read_executed_by_this_phase"), True),
        (("final_command", "credential_env_read_executed"), True),
        (("final_command", "credential_values_loaded_for_output"), True),
        (("final_command", "credential_values_persisted"), True),
        (("final_command", "credential_values_logged"), True),
        (("final_command", "credential_value_output"), True),
        (("final_command", "credential_secret_output"), True),
        (("final_command", "secret_length_output"), True),
        (("final_command", "secret_hash_output"), True),
        (("final_command", "authorization_header_generated"), True),
        (("final_command", "authorization_header_output"), True),
        (("final_command", "basic_auth_string_generated"), True),
        (("final_command", "basic_auth_string_output"), True),
        (("current_phase_execution", "wordpress_api_call_executed"), True),
        (("current_phase_execution", "wordpress_get_executed"), True),
        (("current_phase_execution", "wordpress_post_executed"), True),
        (("current_phase_execution", "wordpress_write_executed_by_this_phase"), True),
        (("current_phase_execution", "wordpress_publish_executed"), True),
        (("current_phase_execution", "publish_executed"), True),
        (("current_phase_execution", "actual_publish_execution_runner_executed"), True),
        (("current_phase_execution", "manual_publish_executed"), True),
        (("final_command", "actual_publish_execution_allowed_by_this_phase"), True),
        (("final_command", "actual_runner_execution_allowed_by_this_phase"), True),
        (("final_command", "manual_publish_allowed_by_this_phase"), True),
        (("final_command", "manual_publish_execution_allowed_by_this_phase"), True),
        (("current_phase_execution", "rerun_allowed"), True),
    ],
)
def test_30_to_60_final_command_and_current_phase_checks(
    monkeypatch, tmp_path: Path, keys: tuple[str, ...], value
) -> None:
    files = build_fixtures(tmp_path)
    mutate_final(files, keys, value)
    out = run_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_61_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    run_phase(monkeypatch, files)
    assert files["output"].exists()


def test_62_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    run_phase(monkeypatch, files)
    assert files["report"].exists()


def test_63_result_keeps_final_command_recorded_true(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["actual_publish_execution_runner_final_command_recorded"] is True


def test_64_result_keeps_final_command_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["actual_publish_execution_runner_final_command_consumed"] is False


def test_65_result_keeps_final_command_allows_execution_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["actual_publish_execution_runner_final_command_allows_execution_by_this_phase"] is False


def test_66_result_keeps_credential_env_read_executed_by_this_phase_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["credential_env_read_executed_by_this_phase"] is False


def test_67_result_keeps_credential_env_read_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["credential_env_read_executed"] is False


def test_68_result_keeps_wordpress_api_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False


def test_69_result_keeps_publish_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["publish_executed"] is False


def test_70_result_keeps_runner_execution_false(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["actual_publish_execution_runner_executed"] is False


def test_71_result_next_phase_ls6at(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["next_phase"]["phase"] == "LS-6AT"


def test_72_result_publish_execution_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    files = build_fixtures(tmp_path)
    out = run_phase(monkeypatch, files)
    assert out["publish_execution_still_blocked"] is True


def test_73_source_code_has_no_requests_call() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "requests." not in src


def test_74_source_code_has_no_urllib_request() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "urllib.request" not in src


def test_75_source_code_has_no_wp_json() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "wp-json" not in src


def test_76_source_code_has_no_wp_v2_posts() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "/wp/v2/posts" not in src


def test_77_source_code_has_no_authorization_generation() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "Authorization" not in src


def test_78_source_code_has_no_basic_generation() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "Basic " not in src


def test_79_source_code_has_no_base64_import_or_use() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/validate_start_ls6as_actual_publish_execution_runner_final_command.py"
    ).read_text(encoding="utf-8")
    assert "base64" not in src
    assert "b64encode" not in src
