from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6r_separate_manual_publish_approval.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "approval": tmp_path / "exchange/human_review/approval.json",
        "ls6q_ready": tmp_path / "exchange/logs/ls6q_ready.json",
        "ls6q_review": tmp_path / "exchange/human_review/ls6q_review.json",
        "ls6p_verify": tmp_path / "exchange/runtime/ls6p_verify.json",
        "ls6p_freeze": tmp_path / "exchange/runtime/ls6p_freeze.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6p_validation": tmp_path / "exchange/logs/ls6p_validation.json",
        "output": tmp_path / "exchange/logs/ls6r_result.json",
        "report": tmp_path / "reports/ls6r_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6R",
            "execution_mode": "SEPARATE_APPROVAL_GATE_ONLY",
            "production_status": "NO_PUBLISH",
            "required_previous_phase": {
                "ls6q": {
                    "required_ready_status": "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH",
                    "required_human_decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
                },
                "ls6p": {
                    "required_validation_status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"
                },
            },
        },
    )

    write_json(
        files["template"],
        {
            "phase": "LS-6R",
            "document_type": "SEPARATE_MANUAL_PUBLISH_APPROVAL_TEMPLATE",
            "approval_status": "TEMPLATE_NOT_APPROVED",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "approval": {
                "approval_label": "",
                "required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                "approval_reason": "",
                "approval_label_consumed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "manual_publish_executed": False,
            },
            "current_phase_execution": {
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "wordpress_existing_post_update_executed": False,
                "wordpress_publish_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "post119_update_executed": False,
                "credential_env_read_executed": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "ls6oc1_rerun_executed": False,
                "rerun_allowed": False,
            },
        },
    )

    write_json(
        files["approval"],
        {
            "phase": "LS-6R",
            "document_type": "SEPARATE_MANUAL_PUBLISH_APPROVAL",
            "approval_status": "APPROVED_NO_PUBLISH_EXECUTION",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "approval": {
                "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                "required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                "approval_reason": "record only",
                "approval_label_consumed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "manual_publish_executed": False,
                "requires_next_phase": "LS-6S",
            },
            "current_phase_execution": {
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "wordpress_existing_post_update_executed": False,
                "wordpress_publish_executed": False,
                "publish_executed": False,
                "future_schedule_executed": False,
                "delete_executed": False,
                "post119_update_executed": False,
                "credential_env_read_executed": False,
                "credential_value_output": False,
                "credential_value_persisted": False,
                "credential_secret_output": False,
                "secret_length_output": False,
                "secret_hash_output": False,
                "authorization_header_output": False,
                "ls6oc1_rerun_executed": False,
                "rerun_allowed": False,
            },
            "human_confirmation_text": "approved",
        },
    )

    write_json(
        files["ls6q_ready"],
        {
            "status": "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH",
            "human_review_completed": True,
            "human_decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "next_phase": {"phase": "LS-6R"},
        },
    )

    write_json(
        files["ls6q_review"],
        {
            "human_decision": {
                "decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY"
            }
        },
    )

    write_json(
        files["ls6p_verify"],
        {
            "post_id": 183,
            "draft_verified": True,
            "returned_post_status": "draft",
        },
    )

    write_json(files["ls6p_freeze"], {"runtime_freeze_restored": True})
    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(
        files["ls6p_validation"],
        {
            "status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED",
            "post_id": 183,
            "draft_verified": True,
            "runtime_freeze_restored": True,
        },
    )

    return files


def run_validator(files: dict[str, Path], allow_template: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy",
        str(files["policy"]),
        "--template",
        str(files["template"]),
        "--approval",
        str(files["approval"]),
        "--ls6q-ready-result",
        str(files["ls6q_ready"]),
        "--ls6q-review-result",
        str(files["ls6q_review"]),
        "--ls6p-draft-verification-result",
        str(files["ls6p_verify"]),
        "--ls6p-runtime-freeze-restore-result",
        str(files["ls6p_freeze"]),
        "--ls6p-rerun-prevention-lock",
        str(files["ls6p_lock"]),
        "--ls6p-validation-result",
        str(files["ls6p_validation"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    if allow_template:
        cmd.append("--allow-template")
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_01_template_allow_returns_template_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    cp = run_validator(files, allow_template=True)
    assert cp.returncode == 0
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_approval_returns_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    cp = run_validator(files)
    assert cp.returncode == 0
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH"


def test_03_approval_missing_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    files["approval"].unlink()
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_04_wrong_approval_label_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["approval"]["approval_label"] = "WRONG"
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_05_approval_label_consumed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["approval"]["approval_label_consumed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_06_manual_publish_allowed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["approval"]["manual_publish_allowed_by_this_phase"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_07_manual_publish_execution_allowed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["approval"]["manual_publish_execution_allowed_by_this_phase"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_08_manual_publish_executed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["approval"]["manual_publish_executed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_09_current_wordpress_api_call_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["wordpress_api_call_executed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_10_current_wordpress_write_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["wordpress_write_executed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_11_current_publish_executed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["publish_executed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_12_current_credential_env_read_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["credential_env_read_executed"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_13_current_credential_value_output_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["credential_value_output"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_14_current_authorization_header_output_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["current_phase_execution"]["authorization_header_output"] = True
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_15_post_id_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["target_post"]["post_id"] = 999
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_16_expected_current_status_not_draft_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["approval"])
    payload["target_post"]["expected_current_status"] = "future"
    write_json(files["approval"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_17_ls6q_ready_status_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6q_ready"])
    payload["status"] = "WRONG"
    write_json(files["ls6q_ready"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_18_ls6q_human_decision_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6q_ready"])
    payload["human_decision"] = "HOLD_AS_DRAFT"
    write_json(files["ls6q_ready"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_19_ls6q_manual_publish_executed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6q_ready"])
    payload["manual_publish_executed"] = True
    write_json(files["ls6q_ready"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_20_ls6p_validation_status_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6p_validation"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_21_ls6p_draft_verified_false_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_validation"])
    payload["draft_verified"] = False
    write_json(files["ls6p_validation"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_22_ls6p_rerun_allowed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_lock"])
    payload["rerun_allowed"] = True
    write_json(files["ls6p_lock"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def test_23_result_keeps_approval_label_consumed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["approval_label_consumed"] is False


def test_24_result_keeps_manual_publish_allowed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["manual_publish_allowed_by_this_phase"] is False


def test_25_result_keeps_manual_publish_execution_allowed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["manual_publish_execution_allowed_by_this_phase"] is False


def test_26_result_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["manual_publish_executed"] is False


def test_27_result_keeps_publish_executed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["publish_executed"] is False


def test_28_result_next_phase_ls6s(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["next_phase"]["phase"] == "LS-6S"


def test_29_result_requires_final_publish_preflight_true(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["next_phase"]["requires_final_publish_preflight"] is True


def test_30_result_requires_separate_execute_now_confirmation_true(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["next_phase"]["requires_separate_execute_now_confirmation"] is True
