from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6z_manual_publish_final_explicit_publish_execution_command.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "command": tmp_path / "exchange/human_review/command.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_run": tmp_path / "exchange/logs/ls6y_run.json",
        "ls6y_preflight": tmp_path / "exchange/runtime/ls6y_preflight.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y_lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6w_validation": tmp_path / "exchange/logs/ls6w_validation.json",
        "ls6w_preflight": tmp_path / "exchange/runtime/ls6w_preflight.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/output.md",
    }

    write_json(files["policy"], {"phase": "LS-6Z", "execution_mode": "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_GATE_ONLY", "production_status": "NO_PUBLISH"})

    template = {
        "phase": "LS-6Z",
        "document_type": "MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_TEMPLATE",
        "command_status": "TEMPLATE_NOT_COMMANDED",
        "target_post": {
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "title": "2.5次元の誘惑",
            "asin": "B07X2G67B4",
            "expected_current_status": "draft",
        },
        "final_explicit_publish_execution_command": {
            "final_explicit_publish_execution_command_label": "",
            "required_final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "command_reason": "",
            "final_explicit_publish_execution_command_consumed": False,
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
        },
        "current_phase_execution": {
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
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "final_execution_command_consumed": False,
            "actual_publish_execution_gate_consumed": False,
            "actual_publish_runner_boundary_consumed": False,
            "final_explicit_publish_execution_command_consumed": False,
            "ls6oc1_rerun_executed": False,
            "rerun_allowed": False,
        },
    }
    write_json(files["template"], template)

    command = {
        "phase": "LS-6Z",
        "document_type": "MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND",
        "command_status": "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
        "target_post": {
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "title": "2.5次元の誘惑",
            "asin": "B07X2G67B4",
            "expected_current_status": "draft",
        },
        "final_explicit_publish_execution_command": {
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "required_final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "command_reason": "ok",
            "final_explicit_publish_execution_command_consumed": False,
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
            "requires_next_phase": "LS-6AA",
        },
        "current_phase_execution": template["current_phase_execution"],
    }
    write_json(files["command"], command)

    write_json(files["ls6y_validation"], {
        "status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "manual_publish_executed": False,
        "publish_execution_still_blocked": True,
        "next_phase": {"phase": "LS-6Z"},
    })
    write_json(files["ls6y_run"], {"status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"})
    write_json(files["ls6y_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6y_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH"})

    write_json(files["ls6x_ready"], {
        "status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH",
        "actual_publish_execution_gate_label": "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "actual_publish_execution_gate_consumed": False,
        "manual_publish_executed": False,
    })
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_label": "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY"}})

    write_json(files["ls6w_validation"], {
        "status": "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH",
        "returned_post_status": "draft",
    })
    write_json(files["ls6w_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"})

    write_json(files["ls6v_ready"], {
        "status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH",
        "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "final_execution_command_consumed": False,
        "manual_publish_executed": False,
    })
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})

    write_json(files["ls6t_ready"], {
        "status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH",
        "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
        "execute_now_confirmation_consumed": False,
    })
    write_json(files["ls6t_confirmation"], {"confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6r_ready"], {
        "status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
        "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
        "approval_label_consumed": False,
    })
    write_json(files["ls6r_approval"], {"approval_status": "APPROVED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def run_validator(files: dict[str, Path], *, allow_template: bool = False) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--template", str(files["template"]),
        "--command", str(files["command"]),
        "--ls6y-validation-result", str(files["ls6y_validation"]),
        "--ls6y-run-result", str(files["ls6y_run"]),
        "--ls6y-boundary-preflight-result", str(files["ls6y_preflight"]),
        "--ls6y-boundary-lock", str(files["ls6y_lock"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6w-validation-result", str(files["ls6w_validation"]),
        "--ls6w-final-runner-preflight-result", str(files["ls6w_preflight"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if allow_template:
        cmd.append("--allow-template")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def assert_not_ready(files: dict[str, Path], *, allow_template: bool = False) -> None:
    run_validator(files, allow_template=allow_template)
    assert read_json(files["output"])["status"] == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_NOT_READY"


def test_01_template_allow_template_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f, allow_template=True)
    assert read_json(f["output"])["status"] == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_command_result_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH"


def test_03_command_file_missing_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    f["command"].unlink()
    assert_not_ready(f)


def test_04_wrong_final_explicit_command_label_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["final_explicit_publish_execution_command_label"] = "WRONG"
    write_json(f["command"], p)
    assert_not_ready(f)


def test_05_final_explicit_command_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["final_explicit_publish_execution_command_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_06_actual_publish_runner_boundary_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["actual_publish_runner_boundary_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_07_actual_publish_execution_gate_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["actual_publish_execution_gate_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_08_final_execution_command_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["final_execution_command_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_09_approval_label_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["approval_label_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_10_execute_now_confirmation_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["execute_now_confirmation_consumed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_11_actual_publish_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["actual_publish_execution_allowed_by_this_phase"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_12_actual_runner_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["actual_runner_execution_allowed_by_this_phase"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_13_manual_publish_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["manual_publish_allowed_by_this_phase"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_14_manual_publish_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["manual_publish_execution_allowed_by_this_phase"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_15_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["final_explicit_publish_execution_command"]["manual_publish_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_16_current_phase_wordpress_api_call_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["wordpress_api_call_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_17_current_phase_wordpress_get_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["wordpress_get_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_18_current_phase_wordpress_post_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["wordpress_post_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_19_current_phase_wordpress_write_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["wordpress_write_executed_by_this_phase"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_20_current_phase_wordpress_publish_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["wordpress_publish_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_21_current_phase_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["publish_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_22_current_phase_credential_read_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["credential_env_read_executed"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_23_current_phase_credential_value_output_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["credential_value_output"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_24_current_phase_authorization_output_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["current_phase_execution"]["authorization_header_output"] = True
    write_json(f["command"], p)
    assert_not_ready(f)


def test_25_post_id_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["target_post"]["post_id"] = 999
    write_json(f["command"], p)
    assert_not_ready(f)


def test_26_expected_current_status_not_draft_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["command"])
    p["target_post"]["expected_current_status"] = "publish"
    write_json(f["command"], p)
    assert_not_ready(f)


def test_27_ls6y_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_validation"])
    p["status"] = "WRONG"
    write_json(f["ls6y_validation"], p)
    assert_not_ready(f)


def test_28_ls6y_run_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_run"])
    p["status"] = "WRONG"
    write_json(f["ls6y_run"], p)
    assert_not_ready(f)


def test_29_ls6y_boundary_preflight_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_preflight"])
    p["status"] = "WRONG"
    write_json(f["ls6y_preflight"], p)
    assert_not_ready(f)


def test_30_ls6y_boundary_lock_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_lock"])
    p["status"] = "WRONG"
    write_json(f["ls6y_lock"], p)
    assert_not_ready(f)


def test_31_ls6y_actual_publish_runner_boundary_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_validation"])
    p["actual_publish_runner_boundary_consumed"] = True
    write_json(f["ls6y_validation"], p)
    assert_not_ready(f)


def test_32_ls6y_publish_execution_still_blocked_false_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_validation"])
    p["publish_execution_still_blocked"] = False
    write_json(f["ls6y_validation"], p)
    assert_not_ready(f)


def test_33_ls6y_next_phase_not_ls6z_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6y_validation"])
    p["next_phase"] = {"phase": "LS-6AA"}
    write_json(f["ls6y_validation"], p)
    assert_not_ready(f)


def test_34_ls6x_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"])
    p["status"] = "WRONG"
    write_json(f["ls6x_ready"], p)
    assert_not_ready(f)


def test_35_ls6x_actual_publish_execution_gate_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"])
    p["actual_publish_execution_gate_consumed"] = True
    write_json(f["ls6x_ready"], p)
    assert_not_ready(f)


def test_36_ls6w_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6w_validation"])
    p["status"] = "WRONG"
    write_json(f["ls6w_validation"], p)
    assert_not_ready(f)


def test_37_ls6w_returned_post_status_not_draft_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6w_validation"])
    p["returned_post_status"] = "publish"
    write_json(f["ls6w_validation"], p)
    assert_not_ready(f)


def test_38_ls6v_final_execution_command_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6v_ready"])
    p["final_execution_command_consumed"] = True
    write_json(f["ls6v_ready"], p)
    assert_not_ready(f)


def test_39_ls6t_execute_now_confirmation_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(f["ls6t_ready"], p)
    assert_not_ready(f)


def test_40_ls6r_approval_label_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(f["ls6r_ready"], p)
    assert_not_ready(f)


def test_41_ls6p_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6p_lock"])
    p["rerun_allowed"] = True
    write_json(f["ls6p_lock"], p)
    assert_not_ready(f)


def test_42_ls6oc1_consumption_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(f["ls6oc1_lock"], p)
    assert_not_ready(f)


def test_43_result_keeps_final_explicit_publish_execution_command_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["final_explicit_publish_execution_command_consumed"] is False


def test_44_result_keeps_actual_publish_runner_boundary_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["actual_publish_runner_boundary_consumed"] is False


def test_45_result_keeps_actual_publish_execution_gate_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["actual_publish_execution_gate_consumed"] is False


def test_46_result_keeps_final_execution_command_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["final_execution_command_consumed"] is False


def test_47_result_keeps_approval_label_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["approval_label_consumed"] is False


def test_48_result_keeps_execute_now_confirmation_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["execute_now_confirmation_consumed"] is False


def test_49_result_keeps_actual_publish_execution_allowed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["actual_publish_execution_allowed_by_this_phase"] is False


def test_50_result_keeps_actual_runner_execution_allowed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["actual_runner_execution_allowed_by_this_phase"] is False


def test_51_result_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["manual_publish_executed"] is False


def test_52_result_keeps_wordpress_api_call_executed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["wordpress_api_call_executed"] is False


def test_53_result_keeps_credential_env_read_executed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["credential_env_read_executed"] is False


def test_54_result_next_phase_ls6aa(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["next_phase"]["phase"] == "LS-6AA"


def test_55_result_requires_actual_publish_execution_final_preflight_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["requires_actual_publish_execution_final_preflight"] is True


def test_56_result_requires_separate_actual_publish_execution_phase_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["requires_separate_actual_publish_execution_phase"] is True


def test_57_result_publish_execution_still_blocked_true(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["publish_execution_still_blocked"] is True
