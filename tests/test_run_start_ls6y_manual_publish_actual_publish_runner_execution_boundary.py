from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_PATH = Path("scripts/run_start_ls6y_manual_publish_actual_publish_runner_execution_boundary.py")


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ls6y_run", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6w_validation": tmp_path / "exchange/logs/ls6w_validation.json",
        "ls6w_preflight": tmp_path / "exchange/runtime/ls6w_preflight.json",
        "ls6w_lock": tmp_path / "exchange/locks/ls6w_lock.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "preflight_output": tmp_path / "exchange/runtime/preflight.json",
        "boundary_lock_output": tmp_path / "exchange/locks/boundary.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6Y",
            "execution_mode": "ACTUAL_PUBLISH_RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
        },
    )

    write_json(
        files["ls6x_ready"],
        {
            "status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH",
            "gate_status": "ACTUAL_PUBLISH_EXECUTION_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "post_id": 183,
            "returned_post_status": "draft",
            "actual_publish_execution_gate_label": "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "actual_publish_execution_gate_consumed": False,
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "requires_next_actual_publish_runner_phase": True,
            "publish_execution_still_blocked": True,
            "next_phase": {"phase": "LS-6Y"},
        },
    )

    write_json(
        files["ls6x_gate"],
        {
            "gate_status": "ACTUAL_PUBLISH_EXECUTION_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_gate": {
                "actual_publish_execution_gate_label": "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
                "actual_publish_execution_gate_consumed": False,
                "manual_publish_executed": False,
            },
        },
    )

    write_json(
        files["ls6w_validation"],
        {
            "status": "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH",
            "returned_post_status": "draft",
            "draft_verified": True,
            "final_execution_command_consumed": False,
            "requires_separate_publish_execution": True,
        },
    )
    write_json(files["ls6w_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6w_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH"})

    write_json(
        files["ls6v_ready"],
        {
            "status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH",
            "command_status": "FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "final_execution_command_consumed": False,
            "manual_publish_executed": False,
        },
    )
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False, "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY"}})

    write_json(
        files["ls6t_ready"],
        {
            "status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH",
            "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
            "execute_now_confirmation_consumed": False,
        },
    )
    write_json(files["ls6t_confirmation"], {"confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION"})

    write_json(
        files["ls6r_ready"],
        {
            "status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
        },
    )
    write_json(files["ls6r_approval"], {"approval_status": "APPROVED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"locked": True, "rerun_allowed": False})
    return files


def invoke(module, files: dict[str, Path], *, record=True, final_explicit=True, separated=True) -> None:
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6w-validation-result", str(files["ls6w_validation"]),
        "--ls6w-final-runner-preflight-result", str(files["ls6w_preflight"]),
        "--ls6w-final-runner-preflight-lock", str(files["ls6w_lock"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--actual-publish-runner-boundary-preflight-output", str(files["preflight_output"]),
        "--actual-publish-runner-boundary-lock-output", str(files["boundary_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if record:
        argv.append("--record-actual-publish-runner-boundary")
    if final_explicit:
        argv.append("--require-final-explicit-publish-execution-command")
    if separated:
        argv.append("--require-separated-actual-publish-execution-phase")

    orig = sys.argv
    try:
        sys.argv = argv
        module.main()
    finally:
        sys.argv = orig


def assert_not_ready_status(files: dict[str, Path], expected: str) -> None:
    result = read_json(files["output"])
    assert result["status"] == expected


def test_01_missing_record_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, record=False)
    assert_not_ready_status(f, "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_BOUNDARY_FLAG")


def test_02_missing_final_explicit_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, final_explicit=False)
    assert_not_ready_status(f, "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_FINAL_EXPLICIT_COMMAND_FLAG")


def test_03_missing_separated_execution_phase_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, separated=False)
    assert_not_ready_status(f, "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_SEPARATED_EXECUTION_PHASE_FLAG")


def test_04_ls6x_ready_missing_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    f["ls6x_ready"].unlink()
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_05_ls6x_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"]); p["status"] = "WRONG"; write_json(f["ls6x_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_06_ls6x_gate_label_mismatch_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"]); p["actual_publish_execution_gate_label"] = "WRONG"; write_json(f["ls6x_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_07_ls6x_gate_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"]); p["actual_publish_execution_gate_consumed"] = True; write_json(f["ls6x_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_08_ls6x_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6x_ready"]); p["manual_publish_executed"] = True; write_json(f["ls6x_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_09_ls6w_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6w_validation"]); p["status"] = "WRONG"; write_json(f["ls6w_validation"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_10_ls6w_returned_status_not_draft_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6w_validation"]); p["returned_post_status"] = "publish"; write_json(f["ls6w_validation"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_11_ls6v_final_execution_command_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6v_ready"]); p["final_execution_command_consumed"] = True; write_json(f["ls6v_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_12_ls6t_execute_now_confirmation_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"]); p["execute_now_confirmation_consumed"] = True; write_json(f["ls6t_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_13_ls6r_approval_label_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6r_ready"]); p["approval_label_consumed"] = True; write_json(f["ls6r_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_14_ls6oc1_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6oc1_lock"]); p["rerun_allowed"] = True; write_json(f["ls6oc1_lock"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def test_15_valid_boundary_preflight_passed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"


def test_16_wordpress_api_and_credentials_not_executed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    out = read_json(f["output"])
    assert out["wordpress_api_call_executed"] is False
    assert out["credential_env_read_executed"] is False


def test_17_output_keeps_wordpress_api_call_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["wordpress_api_call_executed"] is False


def test_18_output_keeps_credential_read_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["credential_env_read_executed"] is False


def test_19_output_keeps_actual_publish_execution_gate_consumed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["actual_publish_execution_gate_consumed"] is False


def test_20_output_keeps_actual_publish_runner_boundary_consumed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["actual_publish_runner_boundary_consumed"] is False


def test_21_output_keeps_final_execution_command_consumed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["final_execution_command_consumed"] is False


def test_22_output_keeps_approval_label_consumed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["approval_label_consumed"] is False


def test_23_output_keeps_execute_now_confirmation_consumed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["execute_now_confirmation_consumed"] is False


def test_24_output_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert read_json(f["output"])["manual_publish_executed"] is False


def test_25_runner_boundary_lock_generated(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    lock = read_json(f["boundary_lock_output"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH"
