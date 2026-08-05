from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6aq_actual_publish_execution_runner_final_boundary import main as run_main
from scripts.validate_start_ls6aq_actual_publish_execution_runner_final_boundary import (
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
    doc = read_json(path)
    cur = doc
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, doc)


def make_run_inputs(tmp_path: Path) -> dict[str, Path]:
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
        "run_output": tmp_path / "exchange/logs/run_result.json",
        "run_report": tmp_path / "reports/run_report.md",
        "validation_output": tmp_path / "exchange/logs/validation_result.json",
        "validation_report": tmp_path / "reports/validation_report.md",
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
                "credential_env_read_executed": False,
                "publish_executed": False,
                "actual_publish_execution_runner_final_boundary_consumed": False,
                "actual_publish_execution_runner_execution_approval_gate_consumed": False,
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

    write_json(files["ls6ap_template"], {"status": "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE_READY_NO_PUBLISH"})

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
        "credential_env_read_executed": False,
        "publish_executed": False,
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
            "current_phase_execution": {"wordpress_api_call_executed": False},
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


def run_build_argv(files: dict[str, Path]) -> list[str]:
    return [
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
        "--output", str(files["run_output"]),
        "--report", str(files["run_report"]),
        "--record-final-boundary",
        "--require-no-wordpress-api",
        "--require-no-credential-read",
        "--require-no-publish",
        "--require-no-runner-execution",
    ]


def validate_build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--boundary-result", str(files["boundary_output"]),
        "--boundary-lock", str(files["boundary_lock_output"]),
        "--run-result", str(files["run_output"]),
        "--ls6ap-ready-result", str(files["ls6ap_ready"]),
        "--ls6ap-approval-gate-result", str(files["ls6ap_approval"]),
        "--ls6ao-validation-result", str(files["ls6ao_result"]),
        "--ls6ao-validation-lock", str(files["ls6ao_lock"]),
        "--ls6ao-validation-log", str(files["ls6ao_log"]),
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


def mutate_run_and_boundary(files: dict[str, Path], keys: tuple[str, ...], value) -> None:
    mutate(files["boundary_output"], keys, value)
    mutate(files["run_output"], keys, value)


def test_57_validation_valid_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_58_validation_detects_missing_boundary_result(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["boundary_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_59_validation_detects_missing_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["boundary_lock_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_60_validation_detects_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    files["run_output"].unlink()
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "keys,value",
    [
        (("actual_publish_execution_runner_final_boundary_consumed",), True),
        (("actual_publish_execution_runner_execution_approval_gate_consumed",), True),
        (("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase",), True),
        (("actual_publish_execution_runner_credential_preflight_required",), False),
        (("actual_publish_execution_runner_final_command_required",), False),
        (("actual_publish_execution_runner_separate_publish_execution_phase_required",), False),
        (("actual_publish_execution_runner_network_call_enabled",), True),
        (("actual_publish_execution_runner_credential_read_enabled",), True),
        (("actual_publish_execution_runner_publish_enabled",), True),
        (("actual_publish_execution_runner_execution_enabled",), True),
        (("actual_publish_execution_runner_executed",), True),
        (("manual_publish_executed",), True),
        (("wordpress_api_call_executed",), True),
        (("credential_env_read_executed",), True),
        (("publish_executed",), True),
        (("rerun_allowed",), True),
    ],
)
def test_61_to_76_validation_detects_flag_violations(
    monkeypatch, tmp_path: Path, keys: tuple[str, ...], value
) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_run_and_boundary(files, keys, value)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_77_validation_detects_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_run_and_boundary(files, ("next_phase", "phase"), "WRONG")
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_78_validation_detects_publish_execution_still_blocked_false(monkeypatch, tmp_path: Path) -> None:
    files = make_run_inputs(tmp_path)
    run_phase(monkeypatch, files)
    mutate_run_and_boundary(files, ("publish_execution_still_blocked",), False)
    out = validate_phase(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY
