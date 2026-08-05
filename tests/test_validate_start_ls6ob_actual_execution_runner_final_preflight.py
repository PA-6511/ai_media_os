from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RUN_SCRIPT = Path("scripts/run_start_ls6ob_actual_execution_runner_final_preflight.py")
VALIDATE_SCRIPT = Path("scripts/validate_start_ls6ob_actual_execution_runner_final_preflight.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def base_files(root: Path) -> dict[str, Path]:
    files = {
        "policy": root / "config/start_ls6ob_actual_execution_runner_final_preflight_policy.json",
        "ls6oa_ready": root / "exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_ready_result.json",
        "ls6oa_go": root / "exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json",
        "ls6n_run": root / "exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_result.json",
        "ls6n_validation": root / "exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_validation_result.json",
        "one_shot_lock": root / "exchange/locks/start_ls6n_one_shot_actual_execution.lock.json",
        "final_preflight": root / "exchange/runtime/start_ls6n_final_execution_preflight_result.json",
        "ls6m_validation": root / "exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_result.json",
        "credential_presence": root / "exchange/runtime/start_ls6m_credential_presence_check_result.json",
        "runtime_state": root / "exchange/runtime/start_ls6m_runtime_freeze_active_state.json",
        "runtime_lock": root / "exchange/locks/start_ls6m_runtime_freeze_active.lock.json",
        "ls6i_validation": root / "exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json",
        "ls6c_payload": root / "exchange/logs/start_ls6c_real_draft_payload_preview.json",
        "ls6c_result": root / "exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json",
        "ls6b_lock": root / "exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json",
        "preflight_output": root / "exchange/runtime/start_ls6ob_actual_execution_runner_final_preflight_result.json",
        "run_output": root / "exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_result.json",
        "run_report": root / "reports/start_ls6ob_actual_execution_runner_final_preflight_gate_report.md",
        "validation_output": root / "exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_validation_result.json",
        "validation_report": root / "reports/start_ls6ob_actual_execution_runner_final_preflight_gate_validation_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6O-B",
            "execution_mode": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY",
            "production_status": "NO_GO",
        },
    )
    write_json(files["ls6oa_ready"], {"status": "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"})
    write_json(
        files["ls6oa_go"],
        {
            "go_status": "HUMAN_CONFIRMED_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO",
            "go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY",
            "decision": {"actual_wordpress_go_consumed": False},
        },
    )
    write_json(files["ls6n_run"], {"status": "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE"})
    write_json(files["ls6n_validation"], {"status": "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE"})
    write_json(files["one_shot_lock"], {"one_shot_actual_execution_lock_active": True, "one_shot_actual_execution_lock_consumed": False})
    write_json(files["final_preflight"], {"status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE", "final_execution_preflight_passed": True})
    write_json(files["ls6m_validation"], {"status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE"})
    write_json(files["credential_presence"], {"required_keys_present": True, "required_keys_non_empty": True})
    write_json(files["runtime_state"], {"runtime_freeze_active": True, "runtime_freeze_applied": True, "runtime_freeze_restored": False})
    write_json(files["runtime_lock"], {"locked": True})
    write_json(files["ls6i_validation"], {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})
    write_json(
        files["ls6c_payload"],
        {
            "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
            "payload_ready": True,
            "payload_count": 1,
            "max_items": 1,
            "payloads": [
                {
                    "title": "2.5次元の誘惑",
                    "post_status": "draft",
                    "content": '<a href="https://www.amazon.co.jp/dp/B07X2G67B4?tag=test">x</a>',
                }
            ],
        },
    )
    write_json(files["ls6c_result"], {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"})
    write_json(files["ls6b_lock"], {"rerun_allowed": False})

    return files


def run_phase(files: dict[str, Path]) -> None:
    cmd = [
        sys.executable,
        str(RUN_SCRIPT),
        "--policy", str(files["policy"]),
        "--ls6oa-ready-result", str(files["ls6oa_ready"]),
        "--ls6oa-go", str(files["ls6oa_go"]),
        "--ls6n-run-result", str(files["ls6n_run"]),
        "--ls6n-validation-result", str(files["ls6n_validation"]),
        "--one-shot-lock", str(files["one_shot_lock"]),
        "--final-execution-preflight", str(files["final_preflight"]),
        "--ls6m-validation-result", str(files["ls6m_validation"]),
        "--credential-presence-result", str(files["credential_presence"]),
        "--runtime-freeze-state", str(files["runtime_state"]),
        "--runtime-freeze-lock", str(files["runtime_lock"]),
        "--ls6i-validation-result", str(files["ls6i_validation"]),
        "--ls6c-payload", str(files["ls6c_payload"]),
        "--ls6c-result", str(files["ls6c_result"]),
        "--ls6b-lock", str(files["ls6b_lock"]),
        "--preflight-output", str(files["preflight_output"]),
        "--output", str(files["run_output"]),
        "--report", str(files["run_report"]),
    ]
    cp = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert cp.returncode == 0


def validate_phase(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(VALIDATE_SCRIPT),
        "--policy", str(files["policy"]),
        "--run-result", str(files["run_output"]),
        "--preflight-result", str(files["preflight_output"]),
        "--ls6oa-ready-result", str(files["ls6oa_ready"]),
        "--ls6oa-go", str(files["ls6oa_go"]),
        "--ls6n-validation-result", str(files["ls6n_validation"]),
        "--one-shot-lock", str(files["one_shot_lock"]),
        "--final-execution-preflight", str(files["final_preflight"]),
        "--ls6m-validation-result", str(files["ls6m_validation"]),
        "--credential-presence-result", str(files["credential_presence"]),
        "--runtime-freeze-state", str(files["runtime_state"]),
        "--runtime-freeze-lock", str(files["runtime_lock"]),
        "--ls6i-validation-result", str(files["ls6i_validation"]),
        "--ls6c-payload", str(files["ls6c_payload"]),
        "--ls6c-result", str(files["ls6c_result"]),
        "--ls6b-lock", str(files["ls6b_lock"]),
        "--output", str(files["validation_output"]),
        "--report", str(files["validation_report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_validate_pass(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE"
    assert out["runner_final_preflight_validated"] is True
    assert out["actual_wordpress_go_ready"] is True
    assert out["actual_wordpress_go_consumed"] is False
    assert out["one_shot_actual_execution_lock_active"] is True
    assert out["one_shot_actual_execution_lock_consumed"] is False
    assert out["runtime_freeze_active"] is True
    assert out["runtime_freeze_restored"] is False
    assert out["runner_executed"] is False
    assert out["actual_execution_executed"] is False


def test_validate_not_ready_when_run_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    run_result = read_json(files["run_output"])
    run_result["status"] = "WRONG"
    write_json(files["run_output"], run_result)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("run result status mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_preflight_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    preflight = read_json(files["preflight_output"])
    preflight["status"] = "WRONG"
    write_json(files["preflight_output"], preflight)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("preflight status mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_go_label_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    go_data = read_json(files["ls6oa_go"])
    go_data["go_label"] = "WRONG"
    write_json(files["ls6oa_go"], go_data)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("go label mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_actual_go_consumed_true(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    go_data = read_json(files["ls6oa_go"])
    go_data["decision"]["actual_wordpress_go_consumed"] = True
    write_json(files["ls6oa_go"], go_data)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("go consumed must be false" in e for e in out["errors"])


def test_validate_not_ready_when_preflight_has_dangerous_true(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    preflight = read_json(files["preflight_output"])
    preflight["wordpress_write_executed"] = True
    write_json(files["preflight_output"], preflight)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("preflight.wordpress_write_executed must be false" in e for e in out["errors"])


def test_validate_not_ready_when_run_result_has_dangerous_true(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    run_result = read_json(files["run_output"])
    run_result["approval_token_consumed"] = True
    write_json(files["run_output"], run_result)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("run_result.approval_token_consumed must be false" in e for e in out["errors"])


def test_validate_not_ready_when_runtime_freeze_restored(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    runtime_state = read_json(files["runtime_state"])
    runtime_state["runtime_freeze_restored"] = True
    write_json(files["runtime_state"], runtime_state)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("runtime_freeze_restored" in e for e in out["errors"])


def test_validate_not_ready_when_ls6n_validation_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    val = read_json(files["ls6n_validation"])
    val["status"] = "WRONG"
    write_json(files["ls6n_validation"], val)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("LS-6N validation status mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_ls6m_validation_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    val = read_json(files["ls6m_validation"])
    val["status"] = "WRONG"
    write_json(files["ls6m_validation"], val)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("LS-6M validation status mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_ls6i_validation_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    val = read_json(files["ls6i_validation"])
    val["status"] = "WRONG"
    write_json(files["ls6i_validation"], val)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("LS-6I validation status mismatch" in e for e in out["errors"])


def test_validate_not_ready_when_ls6c_payload_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    run_phase(files)

    payload = read_json(files["ls6c_payload"])
    payload["status"] = "WRONG"
    write_json(files["ls6c_payload"], payload)

    cp = validate_phase(files)
    assert cp.returncode == 0
    out = read_json(files["validation_output"])
    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATION_NOT_READY"
    assert any("LS-6C payload status mismatch" in e for e in out["errors"])
