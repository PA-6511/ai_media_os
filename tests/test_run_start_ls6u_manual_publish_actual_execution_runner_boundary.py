from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("ls6u_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6s_preflight": tmp_path / "exchange/runtime/ls6s_preflight.json",
        "ls6s_lock": tmp_path / "exchange/locks/ls6s_lock.json",
        "ls6s_run": tmp_path / "exchange/logs/ls6s_run.json",
        "ls6s_validation": tmp_path / "exchange/logs/ls6s_validation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_exec": tmp_path / "exchange/runtime/ls6oc1_exec.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "preflight_out": tmp_path / "exchange/runtime/preflight_out.json",
        "boundary_lock_out": tmp_path / "exchange/locks/boundary_lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "required_previous_phase": {
                "ls6t": {
                    "required_ready_status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH",
                    "required_confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION",
                    "required_execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
                },
                "ls6s": {
                    "required_run_status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
                    "required_validation_status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
                },
                "ls6r": {
                    "required_ready_status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
                    "required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                },
                "ls6oc1": {
                    "required_created_count": 1,
                    "required_returned_post_status": "draft",
                },
            },
            "target_post": {
                "post_id": 183,
            },
        },
    )

    write_json(
        files["ls6t_ready"],
        {
            "status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH",
            "confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION",
            "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
            "execute_now_confirmation_consumed": False,
            "manual_publish_executed": False,
            "publish_execution_still_blocked": True,
        },
    )
    write_json(
        files["ls6t_confirmation"],
        {
            "confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION",
            "confirmation": {
                "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
                "execute_now_confirmation_consumed": False,
                "manual_publish_executed": False,
            },
        },
    )

    write_json(files["ls6s_preflight"], {"status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "returned_post_status": "draft"})
    write_json(files["ls6s_lock"], {"status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"})
    write_json(files["ls6s_run"], {"status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(
        files["ls6s_validation"],
        {
            "status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
            "approval_label_consumed": False,
            "manual_publish_executed": False,
            "publish_execution_still_blocked": True,
        },
    )

    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})
    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(files["ls6oc1_exec"], {"new_post_id": 183, "returned_post_status": "draft", "created_count": 1})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def run_main(files: dict[str, Path], *, boundary: bool, final_sep: bool) -> int:
    module = load_module(Path("scripts/run_start_ls6u_manual_publish_actual_execution_runner_boundary.py"))
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6s-final-preflight-result", str(files["ls6s_preflight"]),
        "--ls6s-final-preflight-lock", str(files["ls6s_lock"]),
        "--ls6s-run-result", str(files["ls6s_run"]),
        "--ls6s-validation-result", str(files["ls6s_validation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-execution-result", str(files["ls6oc1_exec"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--runner-boundary-preflight-output", str(files["preflight_out"]),
        "--runner-boundary-lock-output", str(files["boundary_lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if boundary:
        argv.append("--record-runner-boundary")
    if final_sep:
        argv.append("--require-final-execution-command-separation")
    orig = sys.argv
    try:
        sys.argv = argv
        return module.main()
    finally:
        sys.argv = orig


def test_01_missing_boundary_flag_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=False, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY_MISSING_BOUNDARY_FLAG"


def test_02_missing_final_command_sep_flag_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=False)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY_MISSING_FINAL_COMMAND_SEPARATION_FLAG"


def test_03_ls6t_ready_missing_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    f["ls6t_ready"].unlink()
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_04_ls6t_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"])
    p["status"] = "WRONG"
    write_json(f["ls6t_ready"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_05_ls6t_execute_label_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"])
    p["execute_now_confirmation_label"] = "WRONG"
    write_json(f["ls6t_ready"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_06_ls6t_execute_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(f["ls6t_ready"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_07_ls6t_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"])
    p["manual_publish_executed"] = True
    write_json(f["ls6t_ready"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_08_ls6s_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["status"] = "WRONG"
    write_json(f["ls6s_validation"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_09_ls6s_publish_execution_still_blocked_false_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["publish_execution_still_blocked"] = False
    write_json(f["ls6s_validation"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_10_ls6r_approval_label_consumed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    p = read_json(f["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(f["ls6r_ready"], p)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_11_ls6oc1_consumption_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    write_json(f["ls6oc1_lock"], {"rerun_allowed": True})
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"


def test_12_valid_boundary_preflight_passed(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["status"] == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH"


def test_13_wordpress_api_or_credential_not_called(tmp_path: Path) -> None:
    text = Path("scripts/run_start_ls6u_manual_publish_actual_execution_runner_boundary.py").read_text(encoding="utf-8")
    assert "requests." not in text
    assert "urllib.request" not in text
    assert "wp-json" not in text
    assert "/wp/v2/posts" not in text


def test_14_output_keeps_wordpress_api_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["wordpress_api_call_executed"] is False


def test_15_output_keeps_cred_env_read_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["credential_env_read_executed"] is False


def test_16_output_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["manual_publish_executed"] is False


def test_17_output_keeps_approval_label_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["approval_label_consumed"] is False


def test_18_output_keeps_execute_consumed_false(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert read_json(f["output"])["execute_now_confirmation_consumed"] is False


def test_19_boundary_lock_generated(tmp_path: Path) -> None:
    f = make_files(tmp_path)
    run_main(f, boundary=True, final_sep=True)
    assert f["boundary_lock_out"].exists()
