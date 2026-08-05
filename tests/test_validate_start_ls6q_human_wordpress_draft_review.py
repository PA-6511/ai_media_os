from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6q_human_wordpress_draft_review.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "review_result": tmp_path / "exchange/human_review/review_result.json",
        "ls6p_verify": tmp_path / "exchange/runtime/ls6p_verify.json",
        "ls6p_freeze": tmp_path / "exchange/runtime/ls6p_freeze.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6p_validation": tmp_path / "exchange/logs/ls6p_validation.json",
        "output": tmp_path / "exchange/logs/ls6q_result.json",
        "report": tmp_path / "reports/ls6q_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6Q",
            "execution_mode": "HUMAN_REVIEW_AND_MANUAL_DECISION_ONLY",
            "production_status": "NO_PUBLISH",
            "required_previous_phase": {
                "ls6p": {
                    "required_validation_status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"
                }
            },
            "human_review_policy": {
                "allowed_decisions": [
                    "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
                    "NEEDS_EDIT_BEFORE_PUBLISH",
                    "HOLD_AS_DRAFT",
                    "REJECT_AND_KEEP_DRAFT",
                ]
            },
        },
    )

    write_json(
        files["template"],
        {
            "phase": "LS-6Q",
            "review_status": "TEMPLATE_NOT_DECIDED",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_status": "draft",
            },
            "review_checklist": {
                "post_id_checked": False,
                "title_checked": False,
            },
            "human_decision": {
                "decision": "UNDECIDED",
                "manual_publish_allowed_by_this_phase": False,
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
                "manual_publish_executed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    write_json(
        files["review_result"],
        {
            "phase": "LS-6Q",
            "review_status": "HUMAN_REVIEW_COMPLETED_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_status": "draft",
            },
            "review_checklist": {
                "post_id_checked": True,
                "title_checked": True,
                "draft_status_checked": True,
                "affiliate_link_checked": True,
                "advertising_disclosure_checked": True,
                "content_rendering_checked": True,
                "smartphone_rendering_checked": True,
                "no_publish_checked": True,
                "no_schedule_checked": True,
                "no_existing_post_update_checked": True,
                "no_delete_checked": True,
                "rerun_prevention_checked": True,
                "manual_publish_requires_next_phase_checked": True,
            },
            "human_decision": {
                "decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_executed": False,
                "requires_next_phase": "LS-6R",
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
                "manual_publish_executed": False,
                "ls6oc1_rerun_executed": False,
            },
        },
    )

    write_json(
        files["ls6p_verify"],
        {
            "status": "WORDPRESS_DRAFT_VERIFIED",
            "post_id": 183,
            "draft_verified": True,
            "returned_post_status": "draft",
        },
    )
    write_json(files["ls6p_freeze"], {"runtime_freeze_restored": True})
    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False, "ls6oc1_rerun_executed": False})
    write_json(
        files["ls6p_validation"],
        {"status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"},
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
        "--review-result",
        str(files["review_result"]),
        "--ls6p-wordpress-draft-verification-result",
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
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_TEMPLATE_READY_NO_DECISION"


def test_02_valid_review_result_returns_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    cp = run_validator(files)
    assert cp.returncode == 0
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH"


def test_03_review_result_missing_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    files["review_result"].unlink()
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_04_wrong_decision_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["human_decision"]["decision"] = "HOLD_AS_DRAFT"
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_05_manual_publish_allowed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["human_decision"]["manual_publish_allowed_by_this_phase"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_06_manual_publish_executed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["human_decision"]["manual_publish_executed"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_07_checklist_false_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["review_checklist"]["title_checked"] = False
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_08_current_wordpress_api_call_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["wordpress_api_call_executed"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_09_current_wordpress_write_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["wordpress_write_executed"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_10_current_publish_executed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["publish_executed"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_11_credential_env_read_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["credential_env_read_executed"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_12_credential_value_output_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["credential_value_output"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_13_authorization_header_output_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["current_phase_execution"]["authorization_header_output"] = True
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_14_post_id_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["target_post"]["post_id"] = 999
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_15_expected_status_not_draft_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["review_result"])
    payload["target_post"]["expected_status"] = "future"
    write_json(files["review_result"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_16_ls6p_validation_status_mismatch_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6p_validation"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_17_ls6p_draft_verified_false_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_verify"])
    payload["draft_verified"] = False
    write_json(files["ls6p_verify"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_18_ls6p_runtime_freeze_restored_false_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_freeze"])
    payload["runtime_freeze_restored"] = False
    write_json(files["ls6p_freeze"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_19_ls6p_rerun_allowed_true_returns_not_ready(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    payload = read_json(files["ls6p_lock"])
    payload["rerun_allowed"] = True
    write_json(files["ls6p_lock"], payload)
    run_validator(files)
    assert read_json(files["output"])["status"] == "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def test_20_result_keeps_manual_publish_allowed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["manual_publish_allowed_by_this_phase"] is False


def test_21_result_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["manual_publish_executed"] is False


def test_22_result_keeps_publish_executed_false(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["publish_executed"] is False


def test_23_result_next_phase_ls6r(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["next_phase"]["phase"] == "LS-6R"


def test_24_result_requires_separate_manual_publish_approval_true(tmp_path: Path) -> None:
    files = build_fixture(tmp_path)
    run_validator(files)
    out = read_json(files["output"])
    assert out["next_phase"]["requires_separate_manual_publish_approval"] is True
