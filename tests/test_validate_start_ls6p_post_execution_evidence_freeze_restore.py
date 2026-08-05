from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6p_post_execution_evidence_freeze_restore.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "verification": tmp_path / "exchange/runtime/verification.json",
        "freeze_restore": tmp_path / "exchange/runtime/freeze_restore.json",
        "rerun_lock": tmp_path / "exchange/locks/rerun_lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "ls6oc1_execution": tmp_path / "exchange/runtime/ls6oc1_execution.json",
        "ls6oc1_consumption": tmp_path / "exchange/locks/ls6oc1_consumption.json",
        "ls6oc1_validation": tmp_path / "exchange/logs/ls6oc1_validation.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }
    write_json(files["policy"], {"required_previous_phase": {"ls6oc1": {"required_validation_status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"}}})
    write_json(files["verification"], {
        "status": "WORDPRESS_DRAFT_VERIFIED",
        "post_id": 183,
        "returned_post_status": "draft",
        "wordpress_get_executed": True,
        "wordpress_get_post_id": 183,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "credential_env_read_executed": True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
    })
    write_json(files["freeze_restore"], {"status": "RUNTIME_FREEZE_RESTORE_RECORDED", "runtime_freeze_was_active": True, "runtime_freeze_restored": True, "runtime_freeze_state_deleted": False, "runtime_freeze_lock_deleted": False})
    write_json(files["rerun_lock"], {"status": "RERUN_PREVENTION_FINALIZED", "locked": True, "rerun_allowed": False, "ls6oc1_rerun_allowed": False, "ls6oc1_rerun_executed": False, "target_post_id": 183, "created_count": 1})
    write_json(files["run_result"], {"status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_PASSED"})
    write_json(files["ls6oc1_execution"], {"created_count": 1, "returned_post_status": "draft", "publish_executed": False, "delete_executed": False})
    write_json(files["ls6oc1_consumption"], {"rerun_allowed": False})
    write_json(files["ls6oc1_validation"], {"status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"})
    return files


def run_validate(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable, str(SCRIPT),
        "--policy", str(files["policy"]),
        "--wordpress-draft-verification-result", str(files["verification"]),
        "--runtime-freeze-restore-result", str(files["freeze_restore"]),
        "--rerun-prevention-lock", str(files["rerun_lock"]),
        "--run-result", str(files["run_result"]),
        "--ls6oc1-execution-result", str(files["ls6oc1_execution"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_consumption"]),
        "--ls6oc1-validation-result", str(files["ls6oc1_validation"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_validator_valid_result(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    cp = run_validate(files)
    assert cp.returncode == 0
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"


def test_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["verification"])
    payload["publish_executed"] = True
    write_json(files["verification"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def test_validator_detects_wordpress_write_executed_by_this_phase_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["verification"])
    payload["wordpress_write_executed_by_this_phase"] = True
    write_json(files["verification"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def test_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["verification"])
    payload["credential_value_output"] = True
    write_json(files["verification"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def test_validator_detects_runtime_freeze_restored_false(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["freeze_restore"])
    payload["runtime_freeze_restored"] = False
    write_json(files["freeze_restore"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def test_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["rerun_lock"])
    payload["rerun_allowed"] = True
    write_json(files["rerun_lock"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"


def test_validator_detects_target_post_id_mismatch(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["rerun_lock"])
    payload["target_post_id"] = 999
    write_json(files["rerun_lock"], payload)
    run_validate(files)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATION_NOT_READY"