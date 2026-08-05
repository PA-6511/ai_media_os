from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ae_manual_publish_actual_publish_final_preflight import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "wp": tmp_path / "exchange/runtime/wp.json",
        "final_pf": tmp_path / "exchange/runtime/final_pf.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "ls6ad_run": tmp_path / "exchange/logs/ls6ad_run.json",
        "ls6ad_validation": tmp_path / "exchange/logs/ls6ad_validation.json",
        "ls6ad_boundary": tmp_path / "exchange/runtime/ls6ad_boundary.json",
        "ls6ad_lock": tmp_path / "exchange/locks/ls6ad_lock.json",
        "ls6ac_ready": tmp_path / "exchange/logs/ls6ac_ready.json",
        "ls6ac_confirmation": tmp_path / "exchange/human_review/ls6ac_confirmation.json",
        "ls6ab_validation": tmp_path / "exchange/logs/ls6ab_validation.json",
        "ls6ab_blocked": tmp_path / "exchange/runtime/ls6ab_blocked.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab_lock.json",
        "ls6aa_validation": tmp_path / "exchange/logs/ls6aa_validation.json",
        "ls6aa_preflight": tmp_path / "exchange/runtime/ls6aa_preflight.json",
        "ls6aa_lock": tmp_path / "exchange/locks/ls6aa_lock.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_command": tmp_path / "exchange/human_review/ls6z_command.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y_lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"phase": "LS-6AE"})

    run = {
        "status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "draft_verified": True,
        "returned_post_status": "draft",
        "wordpress_get_executed": True,
        "wordpress_get_post_id": 183,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "actual_publish_final_preflight_ready": True,
        "actual_publish_final_preflight_consumed": False,
        "actual_publish_execution_boundary_ready": True,
        "actual_publish_execution_boundary_consumed": False,
        "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
        "actual_publish_execute_now_final_confirmation_consumed": False,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": True,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_ready": True,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "credential_env_read_executed": True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_runner_final_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AF",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_runner_final_gate": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
    }
    write_json(files["run"], run)

    write_json(files["wp"], {"status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED", "wordpress_get_executed": True, "credential_env_read_executed": True, "returned_post_status": "draft"})

    fp = dict(run)
    fp["status"] = "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
    fp["document_type"] = "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_RESULT"
    fp["current_post_status_verified"] = True
    write_json(files["final_pf"], fp)

    write_json(files["lock"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH", "locked": True, "rerun_allowed": False, "ls6oc1_rerun_executed": False, "requires_next_phase": "LS-6AF"})

    write_json(files["ls6ad_run"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"})
    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_boundary"], {"actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ac_ready"], {"actual_publish_execute_now_final_confirmation_consumed": False})
    write_json(files["ls6ac_confirmation"], {"actual_publish_execute_now_final_confirmation": {"actual_publish_execute_now_final_confirmation_consumed": False}})
    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"actual_publish_execution_runner_executed": False})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})
    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6z_ready"], {"final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})
    write_json(files["ls6y_validation"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})
    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--wordpress-current-draft-status-result", str(files["wp"]),
        "--actual-publish-final-preflight-result", str(files["final_pf"]),
        "--actual-publish-final-preflight-lock", str(files["lock"]),
        "--run-result", str(files["run"]),
        "--ls6ad-run-result", str(files["ls6ad_run"]),
        "--ls6ad-validation-result", str(files["ls6ad_validation"]),
        "--ls6ad-boundary-result", str(files["ls6ad_boundary"]),
        "--ls6ad-boundary-lock", str(files["ls6ad_lock"]),
        "--ls6ac-ready-result", str(files["ls6ac_ready"]),
        "--ls6ac-confirmation-result", str(files["ls6ac_confirmation"]),
        "--ls6ab-validation-result", str(files["ls6ab_validation"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_blocked"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
        "--ls6aa-validation-result", str(files["ls6aa_validation"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_preflight"]),
        "--ls6aa-final-preflight-lock", str(files["ls6aa_lock"]),
        "--ls6z-ready-result", str(files["ls6z_ready"]),
        "--ls6z-command-result", str(files["ls6z_command"]),
        "--ls6y-validation-result", str(files["ls6y_validation"]),
        "--ls6y-boundary-lock", str(files["ls6y_lock"]),
        "--ls6x-ready-result", str(files["ls6x_ready"]),
        "--ls6x-gate-result", str(files["ls6x_gate"]),
        "--ls6v-ready-result", str(files["ls6v_ready"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]


def invoke(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_27_validator_validated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "manual_publish_executed",
        "actual_publish_final_preflight_consumed",
        "actual_publish_execution_boundary_consumed",
        "actual_publish_execute_now_final_confirmation_consumed",
        "explicit_execute_now_for_actual_publish_consumed",
        "actual_publish_execution_runner_executed",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "credential_value_output",
        "authorization_header_output",
        "rerun_allowed",
    ],
)
def test_28_to_48_detect_true_flags(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p[field] = True
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_49_detect_returned_post_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["returned_post_status"] = "publish"
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_50_detect_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["next_phase"]["phase"] = "LS-6ZZ"
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_51_detect_requires_runner_final_gate_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["requires_actual_publish_runner_final_gate"] = False
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_52_detect_publish_execution_still_blocked_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["run"])
    p["publish_execution_still_blocked"] = False
    write_json(files["run"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"
