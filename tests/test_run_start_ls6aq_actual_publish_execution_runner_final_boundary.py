from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6aq_actual_publish_execution_runner_final_boundary import (
    STATUS_MISSING_NO_CREDENTIAL_READ_FLAG,
    STATUS_MISSING_NO_PUBLISH_FLAG,
    STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG,
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
    doc = read_json(path)
    cur = doc
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, doc)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6ap_template": tmp_path / "exchange/logs/ls6ap_template.json",
        "ls6ap_ready": tmp_path / "exchange/logs/ls6ap_ready.json",
        "ls6ap_approval": tmp_path / "exchange/human_review/ls6ap_approval.json",
        "ls6ao_result": tmp_path / "exchange/runtime/ls6ao_result.json",
        "ls6ao_lock": tmp_path / "exchange/locks/ls6ao_lock.json",
        "ls6ao_log": tmp_path / "exchange/logs/ls6ao_log.json",
        "boundary_output": tmp_path / "exchange/runtime/boundary_result.json",
        "boundary_lock_output": tmp_path / "exchange/locks/boundary_lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AQ",
            "execution_mode": "FINAL_BOUNDARY_ONLY_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "required_previous_phase": {
                "ls6ap": {
                    "required_template_status": "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE_READY_NO_PUBLISH",
                    "required_ready_status": "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_READY_NO_PUBLISH",
                    "required_gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION",
                    "required_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
                    "required_approval_gate_consumed": False,
                    "required_execution_approval_allowed_by_this_phase": False,
                    "required_approved_for_later_phase": True,
                    "required_later_final_boundary": True,
                    "required_later_credential_preflight": True,
                    "required_later_final_command": True,
                    "required_separate_publish_phase": True,
                },
                "ls6ao": {
                    "required_validation_status": "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH",
                    "required_ls6an_fix_a_status_normalization_validated": True,
                    "required_ls6an_no_execution_implementation_validated": True,
                    "required_runner_skeleton_static_safety_validated": True,
                    "required_source_artifacts_unchanged": True,
                },
            },
            "final_boundary_policy": {
                "actual_publish_execution_runner_final_boundary_ready": True,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_execution_approval_gate_recorded": True,
                "actual_publish_execution_runner_execution_approval_gate_consumed": False,
                "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": False,
                "actual_publish_execution_runner_execution_approved_for_later_phase": True,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "actual_publish_execution_runner_credential_preflight_required": True,
                "actual_publish_execution_runner_final_command_required": True,
                "actual_publish_execution_runner_separate_publish_execution_phase_required": True,
                "actual_publish_execution_runner_no_execution_implementation_validated": True,
                "ls6ao_validation_validated": True,
                "runner_skeleton_static_safety_validated": True,
                "source_artifacts_unchanged": True,
                "runner_skeleton_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_reexecuted_by_this_phase": False,
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
                "requires_actual_publish_execution_runner_credential_preflight": True,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
            "must_remain_false_flags": {
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
                "credential_env_read_executed": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_execution_approval_gate_consumed": False,
                "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": False,
                "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": False,
                "runner_skeleton_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_reexecuted_by_this_phase": False,
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
                "phase": "LS-6AR",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execution_runner_credential_preflight": True,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    write_json(
        files["ls6ap_template"],
        {
            "status": "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE_READY_NO_PUBLISH",
        },
    )

    ls6ap_ready = {
        "status": "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_READY_NO_PUBLISH",
        "gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_execution_runner_execution_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
        "actual_publish_execution_runner_execution_approval_gate_consumed": False,
        "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": False,
        "actual_publish_execution_runner_execution_approved_for_later_phase": True,
        "actual_publish_execution_runner_execution_requires_later_final_boundary": True,
        "actual_publish_execution_runner_execution_requires_later_credential_preflight": True,
        "actual_publish_execution_runner_execution_requires_later_final_command": True,
        "actual_publish_execution_runner_execution_requires_separate_publish_execution_phase": True,
        "actual_publish_execution_runner_no_execution_implementation_validated": True,
        "runner_skeleton_static_safety_validated": True,
        "source_artifacts_unchanged": True,
        "runner_skeleton_reexecuted_by_this_phase": False,
        "actual_publish_execution_runner_reexecuted_by_this_phase": False,
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
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "publish_execution_still_blocked": True,
    }
    write_json(files["ls6ap_ready"], ls6ap_ready)

    write_json(
        files["ls6ap_approval"],
        {
            "gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "approval_gate": {
                "actual_publish_execution_runner_execution_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
                "actual_publish_execution_runner_execution_approval_gate_consumed": False,
            },
            "current_phase_execution": {
                "wordpress_api_call_executed": False,
            },
        },
    )

    ls6ao = {
        "status": "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "ls6an_fix_a_status_normalization_validated": True,
        "ls6an_no_execution_implementation_validated": True,
        "runner_skeleton_static_safety_validated": True,
        "source_artifacts_unchanged": True,
    }
    write_json(files["ls6ao_result"], ls6ao)
    write_json(files["ls6ao_lock"], {"post_id": 183})
    write_json(files["ls6ao_log"], dict(ls6ao))

    return files


def build_argv(files: dict[str, Path], extra: list[str] | None = None) -> list[str]:
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6ap-template-result", str(files["ls6ap_template"]),
        "--ls6ap-ready-result", str(files["ls6ap_ready"]),
        "--ls6ap-approval-gate-result", str(files["ls6ap_approval"]),
        "--ls6ao-validation-result", str(files["ls6ao_result"]),
        "--ls6ao-validation-lock", str(files["ls6ao_lock"]),
        "--ls6ao-validation-log", str(files["ls6ao_log"]),
        "--boundary-output", str(files["boundary_output"]),
        "--boundary-lock-output", str(files["boundary_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if extra:
        argv.extend(extra)
    return argv


def invoke(monkeypatch, files: dict[str, Path], extra: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, extra=extra))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def run_flags() -> list[str]:
    return [
        "--record-final-boundary",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-runner-execution",
    ]


def test_01_missing_record_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags()[1:])
    assert out["status"] == STATUS_MISSING_RECORD_FLAG


def test_02_missing_no_wordpress_api_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-wordpress-api")
    out = invoke(monkeypatch, files, extra=flags)
    assert out["status"] == STATUS_MISSING_NO_WORDPRESS_API_FLAG


def test_03_missing_no_credential_read_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-credential-read")
    out = invoke(monkeypatch, files, extra=flags)
    assert out["status"] == STATUS_MISSING_NO_CREDENTIAL_READ_FLAG


def test_04_missing_no_publish_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-publish")
    out = invoke(monkeypatch, files, extra=flags)
    assert out["status"] == STATUS_MISSING_NO_PUBLISH_FLAG


def test_05_missing_no_runner_execution_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    flags = run_flags()
    flags.remove("--require-no-runner-execution")
    out = invoke(monkeypatch, files, extra=flags)
    assert out["status"] == STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG


def test_06_ls6ap_ready_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ap_ready"], ("status",), "BROKEN")
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["status"] != STATUS_PASSED


@pytest.mark.parametrize(
    "path,keys,value",
    [
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_approval_gate_consumed",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_approval_allowed_by_this_phase",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_approved_for_later_phase",), False),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_requires_later_final_boundary",), False),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_requires_later_credential_preflight",), False),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_requires_later_final_command",), False),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_requires_separate_publish_execution_phase",), False),
        ("ls6ao_result", ("status",), "BROKEN"),
        ("ls6ao_result", ("ls6an_no_execution_implementation_validated",), False),
        ("ls6ao_result", ("runner_skeleton_static_safety_validated",), False),
        ("ls6ao_result", ("source_artifacts_unchanged",), False),
        ("ls6ap_ready", ("runner_skeleton_reexecuted_by_this_phase",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_reexecuted_by_this_phase",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_network_call_enabled",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_credential_read_enabled",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_publish_enabled",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_execution_enabled",), True),
        ("ls6ap_ready", ("actual_publish_execution_runner_executed",), True),
        ("ls6ap_ready", ("manual_publish_executed",), True),
        ("ls6ap_ready", ("wordpress_api_call_executed",), True),
        ("ls6ap_ready", ("wordpress_get_executed",), True),
        ("ls6ap_ready", ("wordpress_post_executed",), True),
        ("ls6ap_ready", ("wordpress_write_executed_by_this_phase",), True),
        ("ls6ap_ready", ("wordpress_publish_executed",), True),
        ("ls6ap_ready", ("publish_executed",), True),
        ("ls6ap_ready", ("credential_env_read_executed",), True),
        ("ls6ap_ready", ("credential_value_output",), True),
        ("ls6ap_ready", ("authorization_header_output",), True),
    ],
)
def test_07_to_34_invalid_conditions_not_ready(
    monkeypatch, tmp_path: Path, path: str, keys: tuple[str, ...], value
) -> None:
    files = make_inputs(tmp_path)
    mutate(files[path], keys, value)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["status"] != STATUS_PASSED


def test_35_valid_run_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["status"] == STATUS_PASSED


def test_36_boundary_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files, extra=run_flags())
    assert files["boundary_output"].exists()


def test_37_boundary_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files, extra=run_flags())
    assert files["boundary_lock_output"].exists()


def test_38_run_log_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files, extra=run_flags())
    assert files["output"].exists()


def test_39_run_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files, extra=run_flags())
    assert files["report"].exists()


def test_40_result_keeps_final_boundary_ready_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_final_boundary_ready"] is True


def test_41_result_keeps_final_boundary_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_final_boundary_consumed"] is False


def test_42_result_keeps_approval_gate_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_execution_approval_gate_consumed"] is False


def test_43_result_keeps_boundary_allows_execution_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase"] is False


def test_44_result_keeps_credential_preflight_required_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_credential_preflight_required"] is True


def test_45_result_keeps_final_command_required_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_final_command_required"] is True


def test_46_result_keeps_separate_publish_execution_phase_required_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_separate_publish_execution_phase_required"] is True


def test_47_result_keeps_network_call_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_network_call_enabled"] is False


def test_48_result_keeps_credential_read_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_credential_read_enabled"] is False


def test_49_result_keeps_publish_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_publish_enabled"] is False


def test_50_result_keeps_execution_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_execution_enabled"] is False


def test_51_result_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["actual_publish_execution_runner_executed"] is False


def test_52_result_keeps_manual_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["manual_publish_executed"] is False


def test_53_result_keeps_wordpress_api_call_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["wordpress_api_call_executed"] is False


def test_54_result_keeps_credential_env_read_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["credential_env_read_executed"] is False


def test_55_result_keeps_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["publish_executed"] is False


def test_56_result_next_phase_ls6ar(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, extra=run_flags())
    assert out["next_phase"]["phase"] == "LS-6AR"
