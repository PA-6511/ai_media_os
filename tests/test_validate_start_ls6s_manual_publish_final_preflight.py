from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6s_manual_publish_final_preflight.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "wp_result": tmp_path / "exchange/runtime/wp_result.json",
        "preflight_result": tmp_path / "exchange/runtime/preflight_result.json",
        "preflight_lock": tmp_path / "exchange/locks/preflight.lock.json",
        "run_result": tmp_path / "exchange/logs/run_result.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_validation": tmp_path / "exchange/logs/ls6p_validation.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1.lock.json",
        "output": tmp_path / "exchange/logs/validation_result.json",
        "report": tmp_path / "reports/validation_report.md",
    }

    write_json(
        files["policy"],
        {
            "target_post": {"post_id": 183},
            "required_previous_phase": {
                "ls6r": {"required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY"},
                "ls6p": {"required_validation_status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"},
            },
        },
    )

    write_json(
        files["wp_result"],
        {
            "status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED",
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
            "wordpress_publish_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "post119_update_executed": False,
        },
    )

    write_json(
        files["preflight_result"],
        {
            "status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "current_post_status_verified": True,
            "ls6r_approval_verified": True,
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "separate_execute_now_confirmation_required": True,
            "publish_execution_still_blocked": True,
        },
    )

    write_json(
        files["preflight_lock"],
        {
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "requires_next_phase": "LS-6T",
        },
    )

    write_json(
        files["run_result"],
        {
            "status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "post_id": 183,
            "draft_verified": True,
            "returned_post_status": "draft",
            "wordpress_get_executed": True,
            "wordpress_write_executed_by_this_phase": False,
            "wordpress_draft_creation_executed_by_this_phase": False,
            "wordpress_publish_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "post119_update_executed": False,
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "separate_execute_now_confirmation_required": True,
            "publish_execution_still_blocked": True,
            "credential_env_read_executed": True,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
            "next_phase": {"phase": "LS-6T"},
        },
    )

    write_json(files["ls6r_ready"], {"approval_label_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})
    write_json(files["ls6p_validation"], {"status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def run_validator(files: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--wordpress-current-draft-status-result", str(files["wp_result"]),
        "--manual-publish-final-preflight-result", str(files["preflight_result"]),
        "--manual-publish-final-preflight-lock", str(files["preflight_lock"]),
        "--run-result", str(files["run_result"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-validation-result", str(files["ls6p_validation"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_20_validator_valid_result_validated(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    cp = run_validator(files)
    assert cp.returncode == 0
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_21_validator_detects_wordpress_write_executed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["wordpress_write_executed_by_this_phase"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_22_validator_detects_wordpress_publish_executed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["wordpress_publish_executed"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_23_validator_detects_publish_executed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["publish_executed"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_24_validator_detects_manual_publish_executed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["manual_publish_executed"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_25_validator_detects_approval_label_consumed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["approval_label_consumed"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_26_validator_detects_credential_value_output_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["credential_value_output"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_27_validator_detects_authorization_header_output_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["authorization_header_output"] = True
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_28_validator_detects_rerun_allowed_true(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["preflight_lock"])
    payload["rerun_allowed"] = True
    write_json(files["preflight_lock"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_29_validator_detects_returned_post_status_not_draft(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["returned_post_status"] = "publish"
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_30_validator_detects_next_phase_not_ls6t(tmp_path: Path) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["run_result"])
    payload["next_phase"] = {"phase": "LS-6U"}
    write_json(files["run_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] != "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"
