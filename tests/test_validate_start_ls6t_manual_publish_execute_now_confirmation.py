from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/validate_start_ls6t_manual_publish_execute_now_confirmation.py")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "confirmation": tmp_path / "exchange/human_review/confirmation.json",
        "ls6s_validation": tmp_path / "exchange/logs/ls6s_validation.json",
        "ls6s_preflight": tmp_path / "exchange/runtime/ls6s_preflight.json",
        "ls6s_lock": tmp_path / "exchange/locks/ls6s_lock.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/ls6t_result.json",
        "report": tmp_path / "reports/ls6t_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6T",
            "execution_mode": "EXECUTE_NOW_CONFIRMATION_GATE_ONLY",
            "production_status": "NO_PUBLISH",
            "required_previous_phase": {
                "ls6s": {
                    "required_validation_status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
                    "required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                },
                "ls6r": {
                    "required_ready_status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
                },
            },
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
        files["template"],
        {
            "phase": "LS-6T",
            "document_type": "MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_TEMPLATE",
            "confirmation_status": "TEMPLATE_NOT_CONFIRMED",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "confirmation": {
                "execute_now_confirmation_label": "",
                "required_execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
                "execute_now_confirmation_consumed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "manual_publish_executed": False,
            },
            "current_phase_execution": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
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
                "approval_label_consumed": False,
                "ls6oc1_rerun_executed": False,
                "rerun_allowed": False,
            },
        },
    )

    write_json(
        files["confirmation"],
        {
            "phase": "LS-6T",
            "document_type": "MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION",
            "confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "confirmation": {
                "execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
                "required_execute_now_confirmation_label": "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY",
                "execute_now_confirmation_consumed": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "manual_publish_executed": False,
                "requires_next_phase": "LS-6U",
            },
            "current_phase_execution": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
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
                "approval_label_consumed": False,
                "ls6oc1_rerun_executed": False,
                "rerun_allowed": False,
            },
        },
    )

    write_json(
        files["ls6s_validation"],
        {
            "status": "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
            "draft_verified": True,
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
            "manual_publish_executed": False,
            "separate_execute_now_confirmation_required": True,
            "publish_execution_still_blocked": True,
            "next_phase": {"phase": "LS-6T"},
        },
    )
    write_json(
        files["ls6s_preflight"],
        {
            "status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "returned_post_status": "draft",
            "manual_publish_executed": False,
        },
    )
    write_json(
        files["ls6s_lock"],
        {
            "status": "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH",
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
        },
    )
    write_json(
        files["ls6r_ready"],
        {
            "status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
            "approval_label_consumed": False,
            "manual_publish_executed": False,
        },
    )
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})
    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def run_validator(files: dict[str, Path], allow_template: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--policy", str(files["policy"]),
        "--template", str(files["template"]),
        "--confirmation", str(files["confirmation"]),
        "--ls6s-validation-result", str(files["ls6s_validation"]),
        "--ls6s-final-preflight-result", str(files["ls6s_preflight"]),
        "--ls6s-final-preflight-lock", str(files["ls6s_lock"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if allow_template:
        cmd.append("--allow-template")
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def test_01_template_allow_template_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f, allow_template=True)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_confirmation_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH"


def test_03_confirmation_missing_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    f["confirmation"].unlink()
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_04_wrong_execute_label_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["confirmation"]["execute_now_confirmation_label"] = "WRONG"
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_05_execute_now_confirmation_consumed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["confirmation"]["execute_now_confirmation_consumed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_06_manual_publish_allowed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["confirmation"]["manual_publish_allowed_by_this_phase"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_07_manual_publish_execution_allowed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["confirmation"]["manual_publish_execution_allowed_by_this_phase"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_08_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["confirmation"]["manual_publish_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_09_current_wordpress_api_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["wordpress_api_call_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_10_current_wordpress_get_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["wordpress_get_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_11_current_wordpress_write_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["wordpress_write_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_12_current_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["publish_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_13_current_credential_env_read_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["credential_env_read_executed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_14_current_credential_value_output_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["credential_value_output"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_15_current_authorization_header_output_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["authorization_header_output"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_16_approval_label_consumed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["current_phase_execution"]["approval_label_consumed"] = True
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_17_post_id_mismatch_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["target_post"]["post_id"] = 999
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_18_expected_current_status_not_draft_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["confirmation"])
    p["target_post"]["expected_current_status"] = "publish"
    write_json(f["confirmation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_19_ls6s_validation_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["status"] = "WRONG"
    write_json(f["ls6s_validation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_20_ls6s_final_preflight_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_preflight"])
    p["status"] = "WRONG"
    write_json(f["ls6s_preflight"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_21_ls6s_returned_status_not_draft_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_preflight"])
    p["returned_post_status"] = "publish"
    write_json(f["ls6s_preflight"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_22_ls6s_manual_publish_executed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["manual_publish_executed"] = True
    write_json(f["ls6s_validation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_23_ls6s_publish_execution_still_blocked_false_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["publish_execution_still_blocked"] = False
    write_json(f["ls6s_validation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_24_ls6s_next_phase_not_ls6t_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6s_validation"])
    p["next_phase"] = {"phase": "LS-6U"}
    write_json(f["ls6s_validation"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_25_ls6r_ready_status_mismatch_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6r_ready"])
    p["status"] = "WRONG"
    write_json(f["ls6r_ready"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_26_ls6p_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6p_lock"])
    p["rerun_allowed"] = True
    write_json(f["ls6p_lock"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_27_ls6oc1_consumption_rerun_allowed_true_not_ready(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    p = read_json(f["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(f["ls6oc1_lock"], p)
    run_validator(f)
    assert read_json(f["output"])["status"] == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def test_28_result_keeps_execute_consumed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["execute_now_confirmation_consumed"] is False


def test_29_result_keeps_approval_label_consumed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["approval_label_consumed"] is False


def test_30_result_keeps_manual_publish_allowed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["manual_publish_allowed_by_this_phase"] is False


def test_31_result_keeps_manual_publish_execution_allowed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["manual_publish_execution_allowed_by_this_phase"] is False


def test_32_result_keeps_manual_publish_executed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["manual_publish_executed"] is False


def test_33_result_keeps_publish_executed_false(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["publish_executed"] is False


def test_34_result_next_phase_ls6u(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["next_phase"]["phase"] == "LS-6U"


def test_35_result_requires_execution_runner_boundary_preflight_true(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["next_phase"]["requires_execution_runner_boundary_preflight"] is True


def test_36_result_requires_final_execute_command_true(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["next_phase"]["requires_final_execute_command"] is True


def test_37_result_publish_execution_still_blocked_true(tmp_path: Path) -> None:
    f = build_fixture(tmp_path)
    run_validator(f)
    out = read_json(f["output"])
    assert out["publish_execution_still_blocked"] is True
