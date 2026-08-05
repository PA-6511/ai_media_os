from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPT_PATH = Path("scripts/run_start_ls6w_manual_publish_actual_execution_final_runner_preflight.py")


def load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ls6w_run", SCRIPT_PATH)
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
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6u_validation": tmp_path / "exchange/logs/ls6u_validation.json",
        "ls6u_preflight": tmp_path / "exchange/runtime/ls6u_preflight.json",
        "ls6u_lock": tmp_path / "exchange/locks/ls6u_lock.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "credential_env": tmp_path / "credential.env",
        "wp_out": tmp_path / "exchange/runtime/wp_verify.json",
        "preflight_out": tmp_path / "exchange/runtime/preflight.json",
        "lock_out": tmp_path / "exchange/locks/preflight.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6W", "execution_mode": "FINAL_RUNNER_PREFLIGHT_ONLY_NO_PUBLISH", "production_status": "NO_PUBLISH", "target_post": {"post_id": 183, "post_link": "https://hoshido.jp/?p=183", "title": "2.5次元の誘惑", "asin": "B07X2G67B4"}})
    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "command_status": "FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "final_execution_command_consumed": False, "manual_publish_executed": False, "publish_execution_still_blocked": True, "post_id": 183, "returned_post_status": "draft"})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_label": "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "final_execution_command_consumed": False, "manual_publish_executed": False}})
    write_json(files["ls6u_validation"], {"status": "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "actual_runner_execution_allowed_by_this_phase": False})
    write_json(files["ls6u_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6u_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH"})
    write_json(files["ls6t_ready"], {"status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION"})
    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval_status": "APPROVED_NO_PUBLISH_EXECUTION"})
    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=u\nWORDPRESS_APP_PASSWORD=p\n", encoding="utf-8")
    return files


def invoke(module, files: dict[str, Path], *, verify=True, record=True, separated=True, mocked_json: dict | None = None, http_error: str | None = None):
    def fake_verify(base_url: str, username: str, password: str, post_id: int):
        if http_error:
            return None, http_error
        return mocked_json or {"id": 183, "status": "draft"}, None

    module.verify_current_draft = fake_verify

    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6u-validation-result", str(files["ls6u_validation"]),
        "--ls6u-runner-boundary-preflight-result", str(files["ls6u_preflight"]),
        "--ls6u-runner-boundary-lock", str(files["ls6u_lock"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--credential-env", str(files["credential_env"]),
        "--wordpress-current-draft-status-output", str(files["wp_out"]),
        "--final-runner-preflight-output", str(files["preflight_out"]),
        "--final-runner-preflight-lock-output", str(files["lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if verify:
        argv.append("--verify-current-draft")
    if record:
        argv.append("--record-final-runner-preflight")
    if separated:
        argv.append("--require-separated-publish-execution")

    orig = sys.argv
    try:
        sys.argv = argv
        module.main()
    finally:
        sys.argv = orig


def test_01_missing_verify_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, verify=False)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"


def test_02_missing_record_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, record=False)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_PREFLIGHT_FLAG"


def test_03_missing_separated_flag_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, separated=False)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG"


def test_04_ls6v_ready_missing_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    f["ls6v_ready"].unlink()
    try:
        invoke(m, f)
    except FileNotFoundError:
        return
    assert read_json(f["output"])["status"].endswith("NOT_READY")


def test_05_ls6v_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6v_ready"]); p["status"] = "WRONG"; write_json(f["ls6v_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_06_ls6v_final_command_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6v_ready"]); p["final_execution_command_consumed"] = True; write_json(f["ls6v_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_07_ls6v_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6v_ready"]); p["manual_publish_executed"] = True; write_json(f["ls6v_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_08_ls6u_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6u_validation"]); p["status"] = "WRONG"; write_json(f["ls6u_validation"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_09_ls6u_actual_runner_allowed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6u_validation"]); p["actual_runner_execution_allowed_by_this_phase"] = True; write_json(f["ls6u_validation"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_10_ls6t_execute_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6t_ready"]); p["execute_now_confirmation_consumed"] = True; write_json(f["ls6t_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_11_ls6r_approval_consumed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6r_ready"]); p["approval_label_consumed"] = True; write_json(f["ls6r_ready"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_12_ls6oc1_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    p = read_json(f["ls6oc1_lock"]); p["rerun_allowed"] = True; write_json(f["ls6oc1_lock"], p)
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"


def test_13_missing_credential_key_failed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    f["credential_env"].write_text("WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=u\n", encoding="utf-8")
    invoke(m, f)
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH"


def test_14_wordpress_get_http500_failed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, http_error="wordpress GET failed with HTTP 500")
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH"


def test_15_wordpress_get_id_mismatch_failed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, mocked_json={"id": 999, "status": "draft"})
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH"


def test_16_wordpress_get_status_not_draft_failed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, mocked_json={"id": 183, "status": "publish"})
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH"


def test_17_valid_mocked_get_passed(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f, mocked_json={"id": 183, "status": "draft"})
    assert read_json(f["output"])["status"] == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"


def test_18_post_put_patch_delete_not_called(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    wp = read_json(f["wp_out"])
    assert wp["wordpress_post_executed"] is False
    assert wp["wordpress_put_executed"] is False
    assert wp["wordpress_patch_executed"] is False
    assert wp["wordpress_delete_executed"] is False


def test_19_publish_schedule_delete_update_not_called(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    pf = read_json(f["preflight_out"])
    assert pf["wordpress_publish_executed"] is False
    assert pf["future_schedule_executed"] is False
    assert pf["delete_executed"] is False
    assert pf["post119_update_executed"] is False


def test_20_credential_values_not_in_result(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    txt = f["output"].read_text(encoding="utf-8")
    assert "WORDPRESS_APP_PASSWORD" not in txt
    assert '"credential_value_output": true' not in txt


def test_21_final_runner_preflight_lock_generated(tmp_path: Path) -> None:
    m = load_module(); f = make_files(tmp_path)
    invoke(m, f)
    assert f["lock_out"].exists()
