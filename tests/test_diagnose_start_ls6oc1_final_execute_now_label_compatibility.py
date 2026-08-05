from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnose_start_ls6oc1_final_execute_now_label_compatibility.py"
RUNNER = ROOT / "scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"
EXPECTED = "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "confirmation": tmp_path / "exchange/human_review/confirmation.json",
        "ready": tmp_path / "exchange/logs/ready.json",
        "policy": tmp_path / "config/policy.json",
        "previous": tmp_path / "exchange/logs/previous_run.json",
        "output": tmp_path / "exchange/logs/diagnosis.json",
        "report": tmp_path / "reports/diagnosis.md",
        "execution": tmp_path / "exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json",
        "consumption": tmp_path / "exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json",
        "validation": tmp_path / "exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_validation_result.json",
    }
    write_json(
        files["confirmation"],
        {
            "confirmation_label": EXPECTED,
            "decision": {"required_confirm_final_label": EXPECTED},
        },
    )
    write_json(files["ready"], {"confirmation_label": EXPECTED})
    write_json(
        files["policy"],
        {
            "required_previous_phase": {"ls6oc0": {"required_label": EXPECTED}},
            "actual_execution_policy": {"required_confirm_final_label": EXPECTED},
        },
    )
    write_json(
        files["previous"],
        {
            "status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY",
            "errors": ["final execute-now confirmation label mismatch"],
            "wordpress_api_call_executed": False,
            "credential_env_read_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "actual_wordpress_go_consumed_by_this_phase": False,
            "final_execute_now_consumed_by_this_phase": False,
            "one_shot_actual_execution_lock_consumed_by_this_phase": False,
            "runtime_freeze_restored": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
    )
    return files


def run_diag(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--confirmation",
        str(files["confirmation"]),
        "--ready-result",
        str(files["ready"]),
        "--policy",
        str(files["policy"]),
        "--previous-run-result",
        str(files["previous"]),
        "--runner-script",
        str(RUNNER),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_valid_labels_diagnosed_or_fixed(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    cp = run_diag(files)
    assert cp.returncode == 0
    out = read_json(files["output"])
    assert out["status"] in {
        "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_DIAGNOSED_NO_EXECUTION",
        "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_FIXED_NO_EXECUTION",
    }
    assert out["label_compatibility_passed"] is True


def test_confirmation_label_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["confirmation_label"] = "WRONG_LABEL"
    write_json(files["confirmation"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_confirmation_decision_required_label_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["confirmation"])
    payload["decision"]["required_confirm_final_label"] = "WRONG_LABEL"
    write_json(files["confirmation"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_ready_result_confirmation_label_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    write_json(files["ready"], {"confirmation_label": "WRONG_LABEL"})
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_policy_required_previous_label_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["policy"])
    payload["required_previous_phase"]["ls6oc0"]["required_label"] = "WRONG_LABEL"
    write_json(files["policy"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_policy_actual_execution_required_label_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["policy"])
    payload["actual_execution_policy"]["required_confirm_final_label"] = "WRONG_LABEL"
    write_json(files["policy"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_previous_run_wordpress_api_true_fails(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["previous"])
    payload["wordpress_api_call_executed"] = True
    write_json(files["previous"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_previous_run_credential_read_true_fails(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["previous"])
    payload["credential_env_read_executed"] = True
    write_json(files["previous"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_previous_run_write_true_fails(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["previous"])
    payload["wordpress_write_executed"] = True
    write_json(files["previous"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_previous_run_actual_execution_true_fails(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["previous"])
    payload["actual_execution_executed"] = True
    write_json(files["previous"], payload)
    run_diag(files)
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"


def test_fix_a_does_not_generate_execution_result(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_diag(files)
    assert not files["execution"].exists()


def test_fix_a_does_not_generate_consumption_lock(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_diag(files)
    assert not files["consumption"].exists()


def test_fix_a_does_not_generate_validation_result(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_diag(files)
    assert not files["validation"].exists()


def test_secret_and_execution_flags_remain_false(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    run_diag(files)
    out = read_json(files["output"])
    assert out["credential_env_read_executed"] is False
    assert out["wordpress_api_call_executed"] is False
    assert out["wordpress_write_executed"] is False
    assert out["actual_execution_executed"] is False