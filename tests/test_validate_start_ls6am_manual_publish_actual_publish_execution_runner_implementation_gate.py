from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, keys: tuple[str, ...], value) -> None:
    doc = read_json(path)
    cur = doc
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, doc)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "gate": tmp_path / "exchange/human_review/gate.json",
        "ls6al_ready": tmp_path / "exchange/logs/ls6al_ready.json",
        "ls6al_gate": tmp_path / "exchange/human_review/ls6al_gate.json",
        "ls6ak_validation": tmp_path / "exchange/logs/ls6ak_validation.json",
        "ls6ak_runtime": tmp_path / "exchange/runtime/ls6ak_runtime.json",
        "ls6ak_lock": tmp_path / "exchange/locks/ls6ak_lock.json",
        "ls6aj_ready": tmp_path / "exchange/logs/ls6aj_ready.json",
        "ls6aj_execute": tmp_path / "exchange/human_review/ls6aj_execute.json",
        "ls6ai_validation": tmp_path / "exchange/logs/ls6ai_validation.json",
        "ls6ai_wp": tmp_path / "exchange/runtime/ls6ai_wp.json",
        "ls6ai_final": tmp_path / "exchange/runtime/ls6ai_final.json",
        "ls6ai_lock": tmp_path / "exchange/locks/ls6ai_lock.json",
        "ls6ah_validation": tmp_path / "exchange/logs/ls6ah_validation.json",
        "ls6ah_boundary": tmp_path / "exchange/runtime/ls6ah_boundary.json",
        "ls6ah_lock": tmp_path / "exchange/locks/ls6ah_lock.json",
        "ls6ag_ready": tmp_path / "exchange/logs/ls6ag_ready.json",
        "ls6ag_command": tmp_path / "exchange/human_review/ls6ag_command.json",
        "ls6af_validation": tmp_path / "exchange/logs/ls6af_validation.json",
        "ls6af_runtime": tmp_path / "exchange/runtime/ls6af_runtime.json",
        "ls6af_lock": tmp_path / "exchange/locks/ls6af_lock.json",
        "ls6ae_validation": tmp_path / "exchange/logs/ls6ae_validation.json",
        "ls6ae_final": tmp_path / "exchange/runtime/ls6ae_final.json",
        "ls6ae_lock": tmp_path / "exchange/locks/ls6ae_lock.json",
        "ls6ad_validation": tmp_path / "exchange/logs/ls6ad_validation.json",
        "ls6ad_boundary": tmp_path / "exchange/runtime/ls6ad_boundary.json",
        "ls6ad_lock": tmp_path / "exchange/locks/ls6ad_lock.json",
        "ls6ac_ready": tmp_path / "exchange/logs/ls6ac_ready.json",
        "ls6ac_confirmation": tmp_path / "exchange/human_review/ls6ac_confirmation.json",
        "ls6ab_validation": tmp_path / "exchange/logs/ls6ab_validation.json",
        "ls6ab_blocked": tmp_path / "exchange/runtime/ls6ab_blocked.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab_lock.json",
        "ls6aa_validation": tmp_path / "exchange/logs/ls6aa_validation.json",
        "ls6aa_final": tmp_path / "exchange/runtime/ls6aa_final.json",
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
        "ls6p_lock": tmp_path / "exchange/locks/start_ls6p_rerun_prevention_final.lock.json",
        "output": tmp_path / "exchange/logs/out.json",
        "report": tmp_path / "reports/out.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AM",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY_NO_PUBLISH",
            "target_post": {"post_id": 183, "expected_current_status": "draft"},
            "required_previous_phase": {
                "ls6p": {
                    "rerun_prevention_final_lock": "exchange/locks/start_ls6p_rerun_prevention_final.lock.json"
                }
            },
        },
    )

    write_json(
        files["ls6al_ready"],
        {
            "status": "LS6AL_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PHASE_GATE_READY_NO_PUBLISH",
            "gate_status": "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "separated_actual_publish_execution_runner_phase_gate_label": "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_ONLY",
            "separated_actual_publish_execution_runner_phase_gate_consumed": False,
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "payload_title": "2.5次元の誘惑",
            "payload_asin": "B07X2G67B4",
            "returned_post_status": "draft",
            "actual_publish_execution_runner_execute_now_label": "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
            "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
            "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "actual_publish_execution_final_preflight_ready": True,
            "requires_actual_publish_execution_runner_implementation": True,
            "publish_execution_still_blocked": True,
        },
    )

    write_json(
        files["ls6al_gate"],
        {
            "separated_phase_gate": {
                "separated_actual_publish_execution_runner_phase_gate_consumed": False,
            }
        },
    )

    write_json(files["ls6ak_validation"], {"status": "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(
        files["ls6ak_runtime"],
        {
            "actual_publish_execution_runner_final_boundary_ready": True,
            "actual_publish_execution_runner_final_boundary_consumed": False,
        },
    )
    write_json(files["ls6ak_lock"], {"actual_publish_execution_runner_final_boundary_consumed": False})

    write_json(files["ls6aj_ready"], {"status": "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_READY_NO_PUBLISH"})
    write_json(
        files["ls6aj_execute"],
        {
            "execute_now_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_runner_execute_now_gate": {
                "actual_publish_execution_runner_execute_now_label": "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
                "actual_publish_execution_runner_execute_now_consumed": False,
            },
        },
    )

    write_json(files["ls6ai_validation"], {"status": "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ai_wp"], {"status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED", "returned_post_status": "draft"})
    write_json(files["ls6ai_final"], {"actual_publish_execution_runner_final_preflight_ready": True, "actual_publish_execution_runner_final_preflight_consumed": False})
    write_json(files["ls6ai_lock"], {"actual_publish_execution_runner_final_preflight_consumed": False})

    write_json(files["ls6ah_validation"], {"status": "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ah_boundary"], {"actual_publish_execution_runner_boundary_ready": True, "actual_publish_execution_runner_boundary_consumed": False})
    write_json(files["ls6ah_lock"], {"actual_publish_execution_runner_boundary_consumed": False})

    write_json(files["ls6ag_ready"], {"status": "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH"})
    write_json(
        files["ls6ag_command"],
        {
            "command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_final_execution_command": {
                "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
                "actual_publish_final_execution_command_consumed": False,
            },
        },
    )

    write_json(files["ls6af_validation"], {"status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6af_runtime"], {"actual_publish_runner_final_gate_ready": True, "actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6af_lock"], {"actual_publish_runner_final_gate_consumed": False})

    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ae_final"], {"actual_publish_final_preflight_ready": True, "actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ae_lock"], {"actual_publish_final_preflight_consumed": False})

    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_boundary"], {"actual_publish_execution_boundary_ready": True, "actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})

    write_json(files["ls6ac_ready"], {"status": "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "actual_publish_execute_now_final_confirmation_consumed": False})
    write_json(
        files["ls6ac_confirmation"],
        {
            "actual_publish_execute_now_final_confirmation": {
                "actual_publish_execute_now_final_confirmation_consumed": False,
                "explicit_execute_now_for_actual_publish_required": True,
                "explicit_execute_now_for_actual_publish_received": True,
                "explicit_execute_now_for_actual_publish_consumed": False,
            }
        },
    )

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"actual_publish_execution_runner_ready": True, "actual_publish_execution_runner_executed": False, "actual_publish_execution_runner_blocked": True})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_final"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})

    write_json(files["ls6z_ready"], {"status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})

    write_json(files["ls6y_validation"], {"status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})

    write_json(files["ls6x_ready"], {"status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_execution_command_consumed": False})
    write_json(files["ls6t_ready"], {"status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False})

    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})
    write_json(files["ls6p_lock"], {"rerun_allowed": False})

    template_doc = {
        "phase": "LS-6AM",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_TEMPLATE",
        "gate_status": "TEMPLATE_NOT_CONFIRMED",
        "target_post": {
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "title": "2.5次元の誘惑",
            "asin": "B07X2G67B4",
            "expected_current_status": "draft",
        },
        "implementation_gate": {
            "actual_publish_execution_runner_implementation_gate_label": "",
            "required_actual_publish_execution_runner_implementation_gate_label": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY",
            "gate_reason": "",
            "actual_publish_execution_runner_implementation_gate_consumed": False,
            "actual_publish_execution_runner_implementation_allowed_by_this_phase": False,
            "actual_publish_execution_runner_implemented_by_this_phase": False,
            "actual_publish_execution_runner_file_created_by_this_phase": False,
            "separated_actual_publish_execution_runner_phase_gate_recorded": True,
            "separated_actual_publish_execution_runner_phase_gate_consumed": False,
            "actual_publish_execution_runner_final_boundary_ready": True,
            "actual_publish_execution_runner_final_boundary_consumed": False,
            "actual_publish_execution_runner_execute_now_recorded": True,
            "actual_publish_execution_runner_execute_now_consumed": False,
            "actual_publish_execution_runner_final_preflight_ready": True,
            "actual_publish_execution_runner_final_preflight_consumed": False,
            "actual_publish_execution_runner_boundary_ready": True,
            "actual_publish_execution_runner_boundary_consumed": False,
            "actual_publish_final_execution_command_recorded": True,
            "actual_publish_final_execution_command_consumed": False,
            "actual_publish_runner_final_gate_ready": True,
            "actual_publish_runner_final_gate_consumed": False,
            "actual_publish_final_preflight_ready": True,
            "actual_publish_final_preflight_consumed": False,
            "actual_publish_execution_boundary_ready": True,
            "actual_publish_execution_boundary_consumed": False,
            "actual_publish_execute_now_final_confirmation_consumed": False,
            "explicit_execute_now_for_actual_publish_required": True,
            "explicit_execute_now_for_actual_publish_received": True,
            "explicit_execute_now_for_actual_publish_consumed": False,
            "actual_publish_execution_runner_ready": True,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_runner_blocked": True,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
        },
        "upstream_consumption_state": {
            "final_explicit_publish_execution_command_consumed": False,
            "actual_publish_execution_final_preflight_consumed": False,
            "actual_publish_runner_boundary_consumed": False,
            "actual_publish_execution_gate_consumed": False,
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_get_executed": False,
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
    }
    write_json(files["template"], template_doc)

    gate_doc = json.loads(json.dumps(template_doc))
    gate_doc["document_type"] = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE"
    gate_doc["gate_status"] = "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_RECORDED_NO_PUBLISH_EXECUTION"
    gate_doc["implementation_gate"]["actual_publish_execution_runner_implementation_gate_label"] = "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY"
    gate_doc["implementation_gate"]["gate_reason"] = "LS-6AL separated phase gate was validated."
    gate_doc["implementation_gate"]["requires_next_phase"] = "LS-6AN"
    write_json(files["gate"], gate_doc)

    return files


def build_argv(files: dict[str, Path], allow_template: bool = False) -> list[str]:
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--template", str(files["template"]),
        "--implementation-gate", str(files["gate"]),
        "--ls6al-ready-result", str(files["ls6al_ready"]),
        "--ls6al-separated-phase-gate-result", str(files["ls6al_gate"]),
        "--ls6ak-validation-result", str(files["ls6ak_validation"]),
        "--ls6ak-final-boundary-result", str(files["ls6ak_runtime"]),
        "--ls6ak-final-boundary-lock", str(files["ls6ak_lock"]),
        "--ls6aj-ready-result", str(files["ls6aj_ready"]),
        "--ls6aj-execute-now-result", str(files["ls6aj_execute"]),
        "--ls6ai-validation-result", str(files["ls6ai_validation"]),
        "--ls6ai-wordpress-current-draft-status-result", str(files["ls6ai_wp"]),
        "--ls6ai-final-preflight-result", str(files["ls6ai_final"]),
        "--ls6ai-final-preflight-lock", str(files["ls6ai_lock"]),
        "--ls6ah-validation-result", str(files["ls6ah_validation"]),
        "--ls6ah-boundary-result", str(files["ls6ah_boundary"]),
        "--ls6ah-boundary-lock", str(files["ls6ah_lock"]),
        "--ls6ag-ready-result", str(files["ls6ag_ready"]),
        "--ls6ag-command-result", str(files["ls6ag_command"]),
        "--ls6af-validation-result", str(files["ls6af_validation"]),
        "--ls6af-runner-final-gate-result", str(files["ls6af_runtime"]),
        "--ls6af-runner-final-gate-lock", str(files["ls6af_lock"]),
        "--ls6ae-validation-result", str(files["ls6ae_validation"]),
        "--ls6ae-final-preflight-result", str(files["ls6ae_final"]),
        "--ls6ae-final-preflight-lock", str(files["ls6ae_lock"]),
        "--ls6ad-validation-result", str(files["ls6ad_validation"]),
        "--ls6ad-boundary-result", str(files["ls6ad_boundary"]),
        "--ls6ad-boundary-lock", str(files["ls6ad_lock"]),
        "--ls6ac-ready-result", str(files["ls6ac_ready"]),
        "--ls6ac-confirmation-result", str(files["ls6ac_confirmation"]),
        "--ls6ab-validation-result", str(files["ls6ab_validation"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_blocked"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
        "--ls6aa-validation-result", str(files["ls6aa_validation"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_final"]),
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
    if allow_template:
        argv.append("--allow-template")
    return argv


def invoke(monkeypatch, files: dict[str, Path], allow_template: bool = False) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, allow_template=allow_template))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_01_template_allow_template_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, allow_template=True)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_implementation_gate_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_READY_NO_PUBLISH"


def test_03_implementation_gate_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["gate"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


@pytest.mark.parametrize(
    "keys,value",
    [
        (("implementation_gate", "actual_publish_execution_runner_implementation_gate_label"), "WRONG_LABEL"),
        (("implementation_gate", "actual_publish_execution_runner_implementation_gate_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_implementation_allowed_by_this_phase"), True),
        (("implementation_gate", "actual_publish_execution_runner_implemented_by_this_phase"), True),
        (("implementation_gate", "actual_publish_execution_runner_file_created_by_this_phase"), True),
        (("implementation_gate", "separated_actual_publish_execution_runner_phase_gate_recorded"), False),
        (("implementation_gate", "separated_actual_publish_execution_runner_phase_gate_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_final_boundary_ready"), False),
        (("implementation_gate", "actual_publish_execution_runner_final_boundary_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_execute_now_recorded"), False),
        (("implementation_gate", "actual_publish_execution_runner_execute_now_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_final_preflight_ready"), False),
        (("implementation_gate", "actual_publish_execution_runner_final_preflight_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_boundary_ready"), False),
        (("implementation_gate", "actual_publish_execution_runner_boundary_consumed"), True),
        (("implementation_gate", "actual_publish_final_execution_command_recorded"), False),
        (("implementation_gate", "actual_publish_final_execution_command_consumed"), True),
        (("implementation_gate", "actual_publish_runner_final_gate_ready"), False),
        (("implementation_gate", "actual_publish_runner_final_gate_consumed"), True),
        (("implementation_gate", "actual_publish_final_preflight_ready"), False),
        (("implementation_gate", "actual_publish_final_preflight_consumed"), True),
        (("implementation_gate", "actual_publish_execution_boundary_ready"), False),
        (("implementation_gate", "actual_publish_execution_boundary_consumed"), True),
        (("implementation_gate", "actual_publish_execute_now_final_confirmation_consumed"), True),
        (("implementation_gate", "explicit_execute_now_for_actual_publish_required"), False),
        (("implementation_gate", "explicit_execute_now_for_actual_publish_received"), False),
        (("implementation_gate", "explicit_execute_now_for_actual_publish_consumed"), True),
        (("implementation_gate", "actual_publish_execution_runner_ready"), False),
        (("implementation_gate", "actual_publish_execution_runner_executed"), True),
        (("implementation_gate", "actual_publish_execution_runner_blocked"), False),
        (("implementation_gate", "actual_publish_execution_allowed_by_this_phase"), True),
        (("implementation_gate", "actual_runner_execution_allowed_by_this_phase"), True),
        (("implementation_gate", "manual_publish_allowed_by_this_phase"), True),
        (("implementation_gate", "manual_publish_execution_allowed_by_this_phase"), True),
        (("implementation_gate", "manual_publish_executed"), True),
    ],
)
def test_04_to_38_gate_field_violations(monkeypatch, tmp_path: Path, keys: tuple[str, ...], value) -> None:
    files = make_inputs(tmp_path)
    mutate(files["gate"], keys, value)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


@pytest.mark.parametrize(
    "keys",
    [
        ("upstream_consumption_state", "final_explicit_publish_execution_command_consumed"),
        ("upstream_consumption_state", "actual_publish_execution_final_preflight_consumed"),
        ("upstream_consumption_state", "actual_publish_runner_boundary_consumed"),
        ("upstream_consumption_state", "actual_publish_execution_gate_consumed"),
        ("upstream_consumption_state", "final_execution_command_consumed"),
        ("upstream_consumption_state", "approval_label_consumed"),
        ("upstream_consumption_state", "execute_now_confirmation_consumed"),
    ],
)
def test_39_to_45_upstream_consumed_true(monkeypatch, tmp_path: Path, keys: tuple[str, ...]) -> None:
    files = make_inputs(tmp_path)
    mutate(files["gate"], keys, True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "authorization_header_output",
    ],
)
def test_46_to_54_current_phase_execution_true(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    mutate(files["gate"], ("current_phase_execution", field), True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


def test_55_post_id_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["gate"], ("target_post", "post_id"), 999)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


def test_56_expected_current_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["gate"], ("target_post", "expected_current_status"), "publish")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("ls6al_ready", ("status",), "WRONG_STATUS"),
        ("ls6al_gate", ("separated_phase_gate", "separated_actual_publish_execution_runner_phase_gate_consumed"), True),
        ("ls6ak_runtime", ("actual_publish_execution_runner_final_boundary_consumed",), True),
        ("ls6aj_execute", ("actual_publish_execution_runner_execute_now_gate", "actual_publish_execution_runner_execute_now_consumed"), True),
        ("ls6ai_final", ("actual_publish_execution_runner_final_preflight_consumed",), True),
        ("ls6ah_boundary", ("actual_publish_execution_runner_boundary_consumed",), True),
        ("ls6ag_command", ("actual_publish_final_execution_command", "actual_publish_final_execution_command_consumed"), True),
        ("ls6af_runtime", ("actual_publish_runner_final_gate_consumed",), True),
        ("ls6ae_final", ("actual_publish_final_preflight_consumed",), True),
        ("ls6ad_boundary", ("actual_publish_execution_boundary_consumed",), True),
        ("ls6ac_confirmation", ("actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed"), True),
        ("ls6ab_blocked", ("actual_publish_execution_runner_executed",), True),
        ("ls6aa_final", ("actual_publish_execution_final_preflight_consumed",), True),
        ("ls6z_command", ("final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed"), True),
        ("ls6y_validation", ("actual_publish_runner_boundary_consumed",), True),
        ("ls6x_gate", ("actual_publish_execution_gate", "actual_publish_execution_gate_consumed"), True),
        ("ls6v_ready", ("final_execution_command_consumed",), True),
        ("ls6t_ready", ("execute_now_confirmation_consumed",), True),
        ("ls6r_ready", ("approval_label_consumed",), True),
        ("ls6oc1_lock", ("rerun_allowed",), True),
    ],
)
def test_57_to_76_upstream_state_violations(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_inputs(tmp_path)
    mutate(files[path_key], keys, value)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"


@pytest.mark.parametrize(
    "field,expected",
    [
        ("actual_publish_execution_runner_implementation_gate_consumed", False),
        ("actual_publish_execution_runner_implementation_allowed_by_this_phase", False),
        ("actual_publish_execution_runner_implemented_by_this_phase", False),
        ("actual_publish_execution_runner_file_created_by_this_phase", False),
        ("actual_publish_execution_runner_executed", False),
        ("actual_publish_execution_allowed_by_this_phase", False),
        ("actual_runner_execution_allowed_by_this_phase", False),
        ("manual_publish_executed", False),
        ("wordpress_api_call_executed", False),
        ("credential_env_read_executed", False),
    ],
)
def test_77_to_86_result_false_flags(monkeypatch, tmp_path: Path, field: str, expected: bool) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_READY_NO_PUBLISH"
    assert out[field] is expected


@pytest.mark.parametrize(
    "path,value",
    [
        (("next_phase", "phase"), "LS-6AN"),
        (("requires_actual_publish_execution_runner_implementation_phase",), True),
        (("requires_actual_publish_execution_runner_no_execution_implementation",), True),
        (("requires_separated_actual_publish_execution_runner_phase",), True),
        (("requires_separate_publish_execution_phase",), True),
        (("publish_execution_still_blocked",), True),
    ],
)
def test_87_to_92_result_handoff_and_requirements(monkeypatch, tmp_path: Path, path: tuple[str, ...], value) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    cur = out
    for key in path:
        cur = cur[key]
    assert cur == value
