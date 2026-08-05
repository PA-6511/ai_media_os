from __future__ import annotations

import json
from pathlib import Path

from scripts.run_start_ls6ab_manual_publish_separated_actual_publish_execution_runner import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6aa_run": tmp_path / "exchange/logs/ls6aa_run.json",
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
        "blocked_output": tmp_path / "exchange/runtime/blocked.json",
        "blocked_lock_output": tmp_path / "exchange/locks/blocked.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
        "fix_test_1": tmp_path / "tests/t1.py",
        "fix_test_2": tmp_path / "tests/t2.py",
    }

    files["fix_test_1"].parent.mkdir(parents=True, exist_ok=True)
    files["fix_test_1"].write_text("def test_a():\n    assert True\n", encoding="utf-8")
    files["fix_test_2"].write_text("def test_b():\n    assert True\n", encoding="utf-8")

    write_json(
        files["policy"],
        {
            "phase": "LS-6AB",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "target_post": {"post_id": 183},
            "required_previous_phase": {
                "ls6aa_fix_a": {
                    "required_min_collected_tests": 1,
                    "expected_collected_tests": 2,
                    "test_files": [str(files["fix_test_1"]), str(files["fix_test_2"])],
                }
            },
        },
    )

    write_json(
        files["ls6aa_run"],
        {
            "status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "actual_publish_execution_final_preflight_ready": True,
            "actual_publish_execution_final_preflight_consumed": False,
            "manual_publish_executed": False,
            "publish_execution_still_blocked": True,
            "requires_explicit_execute_now_for_actual_publish": True,
        },
    )
    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6aa_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"})

    write_json(
        files["ls6z_ready"],
        {
            "status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH",
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "final_explicit_publish_execution_command_consumed": False,
            "manual_publish_executed": False,
        },
    )
    write_json(
        files["ls6z_command"],
        {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}},
    )

    write_json(files["ls6y_validation"], {"status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})

    write_json(files["ls6x_ready"], {"status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_execution_command_consumed": False})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})

    write_json(files["ls6t_ready"], {"status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval_status": "APPROVED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6aa-run-result", str(files["ls6aa_run"]),
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
        "--blocked-runner-output", str(files["blocked_output"]),
        "--blocked-runner-lock-output", str(files["blocked_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--record-blocked-actual-publish-runner",
        "--require-explicit-execute-now-for-actual-publish",
        "--require-separate-publish-execution-phase",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_missing_record_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-blocked-actual-publish-runner")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_RECORD_FLAG"


def test_missing_explicit_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-explicit-execute-now-for-actual-publish")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG"


def test_missing_separate_phase_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def test_ls6aa_run_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["ls6aa_run"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6aa_run_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_run"])
    p["status"] = "BROKEN"
    write_json(files["ls6aa_run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6aa_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_validation"])
    p["status"] = "BROKEN"
    write_json(files["ls6aa_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6aa_preflight_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_run"])
    p["actual_publish_execution_final_preflight_consumed"] = True
    write_json(files["ls6aa_run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6aa_manual_publish_executed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_run"])
    p["manual_publish_executed"] = True
    write_json(files["ls6aa_run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6z_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6z_ready"])
    p["final_explicit_publish_execution_command_consumed"] = True
    write_json(files["ls6z_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6y_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6y_validation"])
    p["actual_publish_runner_boundary_consumed"] = True
    write_json(files["ls6y_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6x_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6x_ready"])
    p["actual_publish_execution_gate_consumed"] = True
    write_json(files["ls6x_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6v_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6v_ready"])
    p["final_execution_command_consumed"] = True
    write_json(files["ls6v_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6t_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(files["ls6t_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6r_consumed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_ls6oc1_rerun_allowed_true_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_valid_blocked_runner_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"


def test_no_wordpress_or_creds_used(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False
    assert out["wordpress_get_executed"] is False
    assert out["credential_env_read_executed"] is False


def test_output_keeps_wordpress_api_call_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False


def test_output_keeps_cread_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["credential_env_read_executed"] is False


def test_output_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_executed"] is False


def test_output_keeps_explicit_received_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["explicit_execute_now_for_actual_publish_received"] is False


def test_output_keeps_explicit_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["explicit_execute_now_for_actual_publish_consumed"] is False


def test_output_keeps_final_explicit_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["final_explicit_publish_execution_command_consumed"] is False


def test_output_keeps_final_preflight_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_final_preflight_consumed"] is False


def test_output_keeps_boundary_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_runner_boundary_consumed"] is False


def test_output_keeps_gate_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_gate_consumed"] is False


def test_output_keeps_manual_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["manual_publish_executed"] is False


def test_blocked_runner_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    lock = read_json(files["blocked_lock_output"])
    assert lock["status"] == "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"
