from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/run_start_ls6ob_actual_execution_runner_final_preflight.py")


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
        "output": root / "exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_result.json",
        "report": root / "reports/start_ls6ob_actual_execution_runner_final_preflight_gate_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6O-B",
            "execution_mode": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY",
            "production_status": "NO_GO",
        },
    )
    write_json(
        files["ls6oa_ready"],
        {"status": "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"},
    )
    write_json(
        files["ls6oa_go"],
        {
            "go_status": "HUMAN_CONFIRMED_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO",
            "go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY",
            "decision": {"actual_wordpress_go_consumed": False},
        },
    )
    write_json(
        files["ls6n_run"],
        {"status": "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE"},
    )
    write_json(
        files["ls6n_validation"],
        {"status": "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE"},
    )
    write_json(
        files["one_shot_lock"],
        {
            "one_shot_actual_execution_lock_active": True,
            "one_shot_actual_execution_lock_consumed": False,
        },
    )
    write_json(
        files["final_preflight"],
        {
            "status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE",
            "final_execution_preflight_passed": True,
        },
    )
    write_json(
        files["ls6m_validation"],
        {"status": "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE"},
    )
    write_json(
        files["credential_presence"],
        {"required_keys_present": True, "required_keys_non_empty": True},
    )
    write_json(
        files["runtime_state"],
        {
            "runtime_freeze_active": True,
            "runtime_freeze_applied": True,
            "runtime_freeze_restored": False,
        },
    )
    write_json(files["runtime_lock"], {"locked": True})
    write_json(
        files["ls6i_validation"],
        {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"},
    )
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
    write_json(
        files["ls6c_result"],
        {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"},
    )
    write_json(files["ls6b_lock"], {"rerun_allowed": False})

    return files


def run_cmd(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(files["policy"]),
        "--ls6oa-ready-result",
        str(files["ls6oa_ready"]),
        "--ls6oa-go",
        str(files["ls6oa_go"]),
        "--ls6n-run-result",
        str(files["ls6n_run"]),
        "--ls6n-validation-result",
        str(files["ls6n_validation"]),
        "--one-shot-lock",
        str(files["one_shot_lock"]),
        "--final-execution-preflight",
        str(files["final_preflight"]),
        "--ls6m-validation-result",
        str(files["ls6m_validation"]),
        "--credential-presence-result",
        str(files["credential_presence"]),
        "--runtime-freeze-state",
        str(files["runtime_state"]),
        "--runtime-freeze-lock",
        str(files["runtime_lock"]),
        "--ls6i-validation-result",
        str(files["ls6i_validation"]),
        "--ls6c-payload",
        str(files["ls6c_payload"]),
        "--ls6c-result",
        str(files["ls6c_result"]),
        "--ls6b-lock",
        str(files["ls6b_lock"]),
        "--preflight-output",
        str(files["preflight_output"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_run_pass(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    result = run_cmd(files)
    assert result.returncode == 0

    out = read_json(files["output"])
    preflight = read_json(files["preflight_output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE"
    assert out["actual_wordpress_go_ready"] is True
    assert out["actual_wordpress_go_consumed"] is False
    assert out["one_shot_actual_execution_lock_active"] is True
    assert out["one_shot_actual_execution_lock_consumed"] is False
    assert out["runtime_freeze_active"] is True
    assert out["runtime_freeze_restored"] is False
    assert out["runner_executed"] is False
    assert out["actual_execution_executed"] is False

    assert preflight["status"] == "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE"
    assert preflight["payload_title"] == "2.5次元の誘惑"
    assert preflight["payload_asin"] == "B07X2G67B4"
    assert preflight["payload_post_status"] == "draft"


def test_run_not_ready_missing_actual_go(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    files["ls6oa_go"].unlink()

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_ACTUAL_GO"
    assert out["actual_wordpress_go_ready"] is False
    assert files["preflight_output"].exists() is False


def test_run_not_ready_on_go_label_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6oa_go"])
    payload["go_label"] = "WRONG_LABEL"
    write_json(files["ls6oa_go"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("go label mismatch" in e for e in out["errors"])


def test_run_not_ready_if_lock_consumed(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["one_shot_lock"])
    payload["one_shot_actual_execution_lock_consumed"] = True
    write_json(files["one_shot_lock"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("lock consumed" in e for e in out["errors"])


def test_run_not_ready_if_runtime_freeze_restored(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["runtime_state"])
    payload["runtime_freeze_restored"] = True
    write_json(files["runtime_state"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("runtime_freeze_restored" in e for e in out["errors"])


def test_run_not_ready_if_payload_title_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["title"] = "別タイトル"
    write_json(files["ls6c_payload"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("title mismatch" in e for e in out["errors"])


def test_run_not_ready_if_payload_asin_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["content"] = '<a href="https://www.amazon.co.jp/dp/XXXXXXXXXX?tag=test">x</a>'
    write_json(files["ls6c_payload"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("asin mismatch" in e for e in out["errors"])


def test_run_not_ready_if_payload_post_status_not_draft(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["post_status"] = "publish"
    write_json(files["ls6c_payload"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("post_status" in e for e in out["errors"])


def test_run_not_ready_if_ls6b_rerun_allowed_true(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6b_lock"])
    payload["rerun_allowed"] = True
    write_json(files["ls6b_lock"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("rerun_allowed" in e for e in out["errors"])


def test_run_not_ready_if_ls6m_validation_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6m_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6m_validation"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("LS-6M validation status mismatch" in e for e in out["errors"])


def test_run_not_ready_if_ls6i_validation_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6i_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6i_validation"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("LS-6I validation status mismatch" in e for e in out["errors"])


def test_run_not_ready_if_ls6n_run_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6n_run"])
    payload["status"] = "WRONG"
    write_json(files["ls6n_run"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("LS-6N run status mismatch" in e for e in out["errors"])


def test_run_not_ready_if_ls6n_validation_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["ls6n_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6n_validation"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("LS-6N validation status mismatch" in e for e in out["errors"])


def test_run_not_ready_if_final_preflight_status_mismatch(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["final_preflight"])
    payload["status"] = "WRONG"
    write_json(files["final_preflight"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("final execution preflight status mismatch" in e for e in out["errors"])


def test_run_not_ready_if_credential_presence_false(tmp_path: Path) -> None:
    files = base_files(tmp_path)
    payload = read_json(files["credential_presence"])
    payload["required_keys_present"] = False
    write_json(files["credential_presence"], payload)

    result = run_cmd(files)
    assert result.returncode == 0
    out = read_json(files["output"])

    assert out["status"] == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
    assert any("required_keys_present" in e for e in out["errors"])
