from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ah_manual_publish_actual_publish_execution_runner_boundary import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, key: str, value) -> None:
    data = read_json(path)
    data[key] = value
    write_json(path, data)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "runtime": tmp_path / "exchange/runtime/runtime.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "ls6ag_ready": tmp_path / "exchange/logs/ls6ag_ready.json",
        "ls6ag_command": tmp_path / "exchange/human_review/ls6ag_command.json",
        "ls6af_validation": tmp_path / "exchange/logs/ls6af_validation.json",
        "ls6af_result": tmp_path / "exchange/runtime/ls6af_result.json",
        "ls6af_lock": tmp_path / "exchange/locks/ls6af_lock.json",
        "ls6ae_validation": tmp_path / "exchange/logs/ls6ae_validation.json",
        "ls6ae_wp": tmp_path / "exchange/runtime/ls6ae_wp.json",
        "ls6ae_result": tmp_path / "exchange/runtime/ls6ae_result.json",
        "ls6ae_lock": tmp_path / "exchange/locks/ls6ae_lock.json",
        "ls6ad_validation": tmp_path / "exchange/logs/ls6ad_validation.json",
        "ls6ad_result": tmp_path / "exchange/runtime/ls6ad_result.json",
        "ls6ad_lock": tmp_path / "exchange/locks/ls6ad_lock.json",
        "ls6ac_ready": tmp_path / "exchange/logs/ls6ac_ready.json",
        "ls6ac_confirmation": tmp_path / "exchange/human_review/ls6ac_confirmation.json",
        "ls6ab_validation": tmp_path / "exchange/logs/ls6ab_validation.json",
        "ls6ab_result": tmp_path / "exchange/runtime/ls6ab_result.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab_lock.json",
        "ls6aa_validation": tmp_path / "exchange/logs/ls6aa_validation.json",
        "ls6aa_result": tmp_path / "exchange/runtime/ls6aa_result.json",
        "ls6aa_lock": tmp_path / "exchange/locks/ls6aa_lock.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_command": tmp_path / "exchange/human_review/ls6z_command.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y_lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"phase": "LS-6AH", "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_ONLY_NO_PUBLISH"})

    run = {
        "status": "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "returned_post_status": "draft",
        "ls6ag_final_execution_command_validated": True,
        "actual_publish_execution_runner_boundary_ready": True,
        "actual_publish_execution_runner_boundary_consumed": False,
        "actual_publish_final_execution_command_recorded": True,
        "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
        "actual_publish_final_execution_command_consumed": False,
        "actual_publish_runner_final_gate_ready": True,
        "actual_publish_runner_final_gate_consumed": False,
        "actual_publish_final_preflight_ready": True,
        "actual_publish_final_preflight_consumed": False,
        "actual_publish_execution_boundary_ready": True,
        "actual_publish_execution_boundary_consumed": False,
        "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
        "actual_publish_execute_now_final_confirmation_consumed": False,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": True,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_ready": True,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
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
        "locked": True,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_final_preflight": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AI",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_final_preflight": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
    }
    write_json(files["run"], run)
    runtime = dict(run)
    runtime["status"] = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_READY_NO_PUBLISH"
    runtime["document_type"] = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_RESULT"
    write_json(files["runtime"], runtime)
    write_json(
        files["lock"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "requires_next_phase": "LS-6AI",
        },
    )

    write_json(files["ls6ag_ready"], {"status": "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "actual_publish_final_execution_command_consumed": False, "requires_actual_publish_execution_runner_boundary": True, "publish_execution_still_blocked": True})
    write_json(files["ls6ag_command"], {"command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "actual_publish_final_execution_command": {"actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "actual_publish_final_execution_command_consumed": False}})
    write_json(files["ls6af_validation"], {"status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6af_result"], {"actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6af_lock"], {"actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "draft_verified": True, "returned_post_status": "draft"})
    write_json(files["ls6ae_wp"], {"returned_post_status": "draft"})
    write_json(files["ls6ae_result"], {"actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ae_lock"], {"actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_result"], {"actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ac_ready"], {"actual_publish_execute_now_final_confirmation_consumed": False})
    write_json(files["ls6ac_confirmation"], {"actual_publish_execute_now_final_confirmation": {"actual_publish_execute_now_final_confirmation_consumed": False}})
    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_result"], {"actual_publish_execution_runner_executed": False})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})
    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_result"], {"actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6z_ready"], {"final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})
    write_json(files["ls6y_validation"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})
    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--actual-publish-execution-runner-boundary-result", str(files["runtime"]),
        "--actual-publish-execution-runner-boundary-lock", str(files["lock"]),
        "--run-result", str(files["run"]),
        "--ls6ag-ready-result", str(files["ls6ag_ready"]),
        "--ls6ag-command-result", str(files["ls6ag_command"]),
        "--ls6af-validation-result", str(files["ls6af_validation"]),
        "--ls6af-runner-final-gate-result", str(files["ls6af_result"]),
        "--ls6af-runner-final-gate-lock", str(files["ls6af_lock"]),
        "--ls6ae-validation-result", str(files["ls6ae_validation"]),
        "--ls6ae-wordpress-current-draft-status-result", str(files["ls6ae_wp"]),
        "--ls6ae-final-preflight-result", str(files["ls6ae_result"]),
        "--ls6ae-final-preflight-lock", str(files["ls6ae_lock"]),
        "--ls6ad-validation-result", str(files["ls6ad_validation"]),
        "--ls6ad-boundary-result", str(files["ls6ad_result"]),
        "--ls6ad-boundary-lock", str(files["ls6ad_lock"]),
        "--ls6ac-ready-result", str(files["ls6ac_ready"]),
        "--ls6ac-confirmation-result", str(files["ls6ac_confirmation"]),
        "--ls6ab-validation-result", str(files["ls6ab_validation"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_result"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
        "--ls6aa-validation-result", str(files["ls6aa_validation"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_result"]),
        "--ls6aa-final-preflight-lock", str(files["ls6aa_lock"]),
        "--ls6z-ready-result", str(files["ls6z_ready"]),
        "--ls6z-command-result", str(files["ls6z_command"]),
        "--ls6y-validation-result", str(files["ls6y_validation"]),
        "--ls6y-boundary-lock", str(files["ls6y_lock"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]


def invoke(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_37_validator_valid_result(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "authorization_header_output",
        "actual_publish_execution_runner_boundary_consumed",
        "actual_publish_final_execution_command_consumed",
        "actual_publish_runner_final_gate_consumed",
        "actual_publish_final_preflight_consumed",
        "actual_publish_execution_boundary_consumed",
        "actual_publish_execute_now_final_confirmation_consumed",
        "explicit_execute_now_for_actual_publish_consumed",
        "actual_publish_execution_runner_executed",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_executed",
        "rerun_allowed",
    ],
)
def test_38_to_65_detect_true_flags(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    run = read_json(files["run"])
    run[field] = True
    write_json(files["run"], run)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_66_detect_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run = read_json(files["run"])
    run["next_phase"]["phase"] = "LS-6ZZ"
    write_json(files["run"], run)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_67_detect_requires_final_preflight_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run = read_json(files["run"])
    run["requires_actual_publish_execution_runner_final_preflight"] = False
    write_json(files["run"], run)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_68_detect_publish_execution_still_blocked_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run = read_json(files["run"])
    run["publish_execution_still_blocked"] = False
    write_json(files["run"], run)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_NOT_READY"
