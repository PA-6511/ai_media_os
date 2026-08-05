from __future__ import annotations

import json
from pathlib import Path

from scripts.run_start_ls6ad_manual_publish_actual_publish_execution_boundary import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6ac_ready": tmp_path / "exchange/logs/ls6ac_ready.json",
        "ls6ac_confirmation": tmp_path / "exchange/human_review/ls6ac_confirmation.json",
        "ls6ab_validation": tmp_path / "exchange/logs/ls6ab_validation.json",
        "ls6ab_blocked": tmp_path / "exchange/runtime/ls6ab_blocked.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab.lock.json",
        "ls6aa_validation": tmp_path / "exchange/logs/ls6aa_validation.json",
        "ls6aa_preflight": tmp_path / "exchange/runtime/ls6aa_preflight.json",
        "ls6aa_lock": tmp_path / "exchange/locks/ls6aa.lock.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_command": tmp_path / "exchange/human_review/ls6z_command.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y.lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p.lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1.lock.json",
        "boundary_output": tmp_path / "exchange/runtime/boundary_result.json",
        "boundary_lock_output": tmp_path / "exchange/locks/boundary.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AD",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_BOUNDARY_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "target_post": {"post_id": 183, "expected_current_status": "draft"},
            "actual_publish_execution_boundary_policy": {
                "actual_publish_execution_boundary_ready": True,
                "actual_publish_execution_boundary_consumed": False,
                "credential_env_read_allowed_by_this_phase": False,
            },
        },
    )

    write_json(
        files["ls6ac_ready"],
        {
            "status": "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "confirmation_status": "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
            "actual_publish_execute_now_final_confirmation_consumed": False,
            "explicit_execute_now_for_actual_publish_required": True,
            "explicit_execute_now_for_actual_publish_received": True,
            "explicit_execute_now_for_actual_publish_consumed": False,
            "actual_publish_execution_runner_ready": True,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_runner_blocked": True,
            "requires_actual_publish_execution_boundary": True,
            "publish_execution_still_blocked": True,
            "next_phase": {"phase": "LS-6AD"},
        },
    )

    write_json(
        files["ls6ac_confirmation"],
        {
            "confirmation_status": "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execute_now_final_confirmation": {
                "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
                "actual_publish_execute_now_final_confirmation_consumed": False,
                "explicit_execute_now_for_actual_publish_required": True,
                "explicit_execute_now_for_actual_publish_received": True,
                "explicit_execute_now_for_actual_publish_consumed": False,
                "actual_publish_execution_runner_executed": False,
            },
        },
    )

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(
        files["ls6ab_blocked"],
        {
            "actual_publish_execution_runner_ready": True,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_runner_blocked": True,
            "explicit_execute_now_for_actual_publish_required": True,
            "explicit_execute_now_for_actual_publish_received": False,
            "explicit_execute_now_for_actual_publish_consumed": False,
        },
    )
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})

    write_json(files["ls6z_ready"], {"status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})

    write_json(files["ls6y_validation"], {"status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})

    write_json(files["ls6x_ready"], {"status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_execution_command_consumed": False})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})

    write_json(files["ls6t_ready"], {"status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"execute_now_confirmation_consumed": False})

    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval_label_consumed": False})

    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6ac-ready-result", str(files["ls6ac_ready"]),
        "--ls6ac-confirmation-result", str(files["ls6ac_confirmation"]),
        "--ls6ab-validation-result", str(files["ls6ab_validation"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_blocked"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
        "--ls6aa-validation-result", str(files["ls6aa_validation"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_preflight"]),
        "--ls6aa-final-preflight-lock", str(files["ls6aa_lock"]),
        "--ls6z-ready-result", str(files["ls6z_ready"]),
        "--ls6z-command-result", str(files["ls6z_command"]),
        "--ls6y-validation-result", str(files["ls6y_validation"]),
        "--ls6y-boundary-lock", str(files["ls6y_lock"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--boundary-output", str(files["boundary_output"]),
        "--boundary-lock-output", str(files["boundary_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--record-actual-publish-execution-boundary",
        "--require-actual-publish-final-preflight",
        "--require-separate-publish-execution-phase",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_01_missing_record_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-actual-publish-execution-boundary")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_RECORD_FLAG"


def test_02_missing_final_preflight_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-actual-publish-final-preflight")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_FINAL_PREFLIGHT_FLAG"


def test_03_missing_separate_phase_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def test_04_ls6ac_ready_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["ls6ac_ready"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_05_ls6ac_ready_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["status"] = "BROKEN"
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_06_ls6ac_confirmation_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["actual_publish_execute_now_final_confirmation_consumed"] = True
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_07_ls6ac_explicit_received_false_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["explicit_execute_now_for_actual_publish_received"] = False
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_08_ls6ac_explicit_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["explicit_execute_now_for_actual_publish_consumed"] = True
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_09_ls6ac_runner_executed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["actual_publish_execution_runner_executed"] = True
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_10_ls6ab_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_validation"])
    p["status"] = "BROKEN"
    write_json(files["ls6ab_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_11_ls6ab_runner_executed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_blocked"])
    p["actual_publish_execution_runner_executed"] = True
    write_json(files["ls6ab_blocked"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_12_ls6ab_explicit_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_blocked"])
    p["explicit_execute_now_for_actual_publish_consumed"] = True
    write_json(files["ls6ab_blocked"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_13_ls6aa_preflight_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_preflight"])
    p["actual_publish_execution_final_preflight_consumed"] = True
    write_json(files["ls6aa_preflight"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_14_ls6z_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6z_ready"])
    p["final_explicit_publish_execution_command_consumed"] = True
    write_json(files["ls6z_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_15_ls6y_boundary_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6y_validation"])
    p["actual_publish_runner_boundary_consumed"] = True
    write_json(files["ls6y_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_16_ls6x_gate_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6x_ready"])
    p["actual_publish_execution_gate_consumed"] = True
    write_json(files["ls6x_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_17_ls6v_final_execution_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6v_ready"])
    p["final_execution_command_consumed"] = True
    write_json(files["ls6v_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_18_ls6t_execute_now_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(files["ls6t_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_19_ls6r_approval_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_20_ls6oc1_rerun_allowed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def test_21_valid_boundary_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"


def test_22_no_wordpress_or_cread_used(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False
    assert out["wordpress_get_executed"] is False
    assert out["credential_env_read_executed"] is False


def test_23_output_keeps_boundary_consumed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execution_boundary_consumed"] is False


def test_24_output_keeps_confirmation_consumed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execute_now_final_confirmation_consumed"] is False


def test_25_output_keeps_explicit_consumed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["explicit_execute_now_for_actual_publish_consumed"] is False


def test_26_output_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execution_runner_executed"] is False


def test_27_output_keeps_wordpress_api_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["wordpress_api_call_executed"] is False


def test_28_output_keeps_cread_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["credential_env_read_executed"] is False


def test_29_output_keeps_manual_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["manual_publish_executed"] is False


def test_30_boundary_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    lock = read_json(files["boundary_lock_output"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH"
