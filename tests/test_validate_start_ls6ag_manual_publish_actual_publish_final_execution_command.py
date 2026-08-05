from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ag_manual_publish_actual_publish_final_execution_command import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def set_nested(doc: dict, path: list[str], value) -> None:
    cur = doc
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "command": tmp_path / "exchange/human_review/command.json",
        "ls6af_run": tmp_path / "exchange/logs/ls6af_run.json",
        "ls6af_validation": tmp_path / "exchange/logs/ls6af_validation.json",
        "ls6af_runtime": tmp_path / "exchange/runtime/ls6af_runtime.json",
        "ls6af_lock": tmp_path / "exchange/locks/ls6af_lock.json",
        "ls6ae_validation": tmp_path / "exchange/logs/ls6ae_validation.json",
        "ls6ae_wp": tmp_path / "exchange/runtime/ls6ae_wp.json",
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
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AG",
            "execution_mode": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_GATE_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
        },
    )

    template = {
        "phase": "LS-6AG",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_TEMPLATE",
        "command_status": "TEMPLATE_NOT_COMMANDED",
        "target_post": {
            "post_id": 183,
            "post_link": "https://hoshido.jp/?p=183",
            "title": "2.5次元の誘惑",
            "asin": "B07X2G67B4",
            "expected_current_status": "draft",
        },
        "actual_publish_final_execution_command": {
            "actual_publish_final_execution_command_label": "",
            "required_actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
            "command_reason": "",
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
    write_json(files["template"], template)

    command = {
        "phase": "LS-6AG",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND",
        "command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
        "target_post": dict(template["target_post"]),
        "actual_publish_final_execution_command": {
            **template["actual_publish_final_execution_command"],
            "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
            "command_reason": "record only",
            "requires_next_phase": "LS-6AH",
        },
        "upstream_consumption_state": dict(template["upstream_consumption_state"]),
        "current_phase_execution": dict(template["current_phase_execution"]),
        "human_command_text": "record gate only",
    }
    write_json(files["command"], command)

    write_json(
        files["ls6af_run"],
        {
            "status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_PASSED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "actual_publish_runner_final_gate_ready": True,
            "actual_publish_runner_final_gate_consumed": False,
            "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "requires_actual_publish_final_execution_command": True,
            "publish_execution_still_blocked": True,
            "next_phase": {"phase": "LS-6AG"},
        },
    )
    write_json(files["ls6af_validation"], {"status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6af_runtime"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_READY_NO_PUBLISH", "actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6af_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_LOCKED_NO_PUBLISH"})

    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "draft_verified": True, "returned_post_status": "draft"})
    write_json(files["ls6ae_wp"], {"returned_post_status": "draft"})
    write_json(files["ls6ae_final"], {"actual_publish_final_preflight_ready": True, "actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ae_lock"], {"actual_publish_final_preflight_consumed": False})

    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_boundary"], {"actual_publish_execution_boundary_ready": True, "actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})

    write_json(
        files["ls6ac_ready"],
        {
            "status": "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH",
            "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
            "actual_publish_execute_now_final_confirmation_consumed": False,
            "explicit_execute_now_for_actual_publish_required": True,
            "explicit_execute_now_for_actual_publish_received": True,
            "explicit_execute_now_for_actual_publish_consumed": False,
        },
    )
    write_json(files["ls6ac_confirmation"], {"actual_publish_execute_now_final_confirmation": {"actual_publish_execute_now_final_confirmation_consumed": False}})

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"actual_publish_execution_runner_ready": True, "actual_publish_execution_runner_executed": False, "actual_publish_execution_runner_blocked": True})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"actual_publish_execution_final_preflight_consumed": False})
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

    return files


def build_argv(files: dict[str, Path], *, allow_template: bool = False) -> list[str]:
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--template", str(files["template"]),
        "--command", str(files["command"]),
        "--ls6af-run-result", str(files["ls6af_run"]),
        "--ls6af-validation-result", str(files["ls6af_validation"]),
        "--ls6af-runner-final-gate-result", str(files["ls6af_runtime"]),
        "--ls6af-runner-final-gate-lock", str(files["ls6af_lock"]),
        "--ls6ae-validation-result", str(files["ls6ae_validation"]),
        "--ls6ae-wordpress-current-draft-status-result", str(files["ls6ae_wp"]),
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
    if allow_template:
        argv.append("--allow-template")
    return argv


def invoke(monkeypatch, files: dict[str, Path], *, allow_template: bool = False) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, allow_template=allow_template))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def mutate_json(path: Path, key_path: list[str], value) -> None:
    doc = read_json(path)
    set_nested(doc, key_path, value)
    write_json(path, doc)


def test_01_template_allow(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, allow_template=True)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_command_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH"


def test_03_command_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["command"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


@pytest.mark.parametrize(
    "path_key",
    [
        ("command", ["actual_publish_final_execution_command", "actual_publish_final_execution_command_label"], "WRONG"),
        ("command", ["actual_publish_final_execution_command", "actual_publish_final_execution_command_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_runner_final_gate_ready"], False),
        ("command", ["actual_publish_final_execution_command", "actual_publish_runner_final_gate_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_final_preflight_ready"], False),
        ("command", ["actual_publish_final_execution_command", "actual_publish_final_preflight_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_boundary_ready"], False),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_boundary_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execute_now_final_confirmation_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "explicit_execute_now_for_actual_publish_required"], False),
        ("command", ["actual_publish_final_execution_command", "explicit_execute_now_for_actual_publish_received"], False),
        ("command", ["actual_publish_final_execution_command", "explicit_execute_now_for_actual_publish_consumed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_runner_ready"], False),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_runner_executed"], True),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_runner_blocked"], False),
        ("command", ["actual_publish_final_execution_command", "actual_publish_execution_allowed_by_this_phase"], True),
        ("command", ["actual_publish_final_execution_command", "actual_runner_execution_allowed_by_this_phase"], True),
        ("command", ["actual_publish_final_execution_command", "manual_publish_allowed_by_this_phase"], True),
        ("command", ["actual_publish_final_execution_command", "manual_publish_execution_allowed_by_this_phase"], True),
        ("command", ["actual_publish_final_execution_command", "manual_publish_executed"], True),
        ("command", ["upstream_consumption_state", "final_explicit_publish_execution_command_consumed"], True),
        ("command", ["upstream_consumption_state", "actual_publish_execution_final_preflight_consumed"], True),
        ("command", ["upstream_consumption_state", "actual_publish_runner_boundary_consumed"], True),
        ("command", ["upstream_consumption_state", "actual_publish_execution_gate_consumed"], True),
        ("command", ["upstream_consumption_state", "final_execution_command_consumed"], True),
        ("command", ["upstream_consumption_state", "approval_label_consumed"], True),
        ("command", ["upstream_consumption_state", "execute_now_confirmation_consumed"], True),
        ("command", ["current_phase_execution", "wordpress_api_call_executed"], True),
        ("command", ["current_phase_execution", "wordpress_get_executed"], True),
        ("command", ["current_phase_execution", "wordpress_post_executed"], True),
        ("command", ["current_phase_execution", "wordpress_write_executed_by_this_phase"], True),
        ("command", ["current_phase_execution", "wordpress_publish_executed"], True),
        ("command", ["current_phase_execution", "publish_executed"], True),
        ("command", ["current_phase_execution", "credential_env_read_executed"], True),
        ("command", ["current_phase_execution", "credential_value_output"], True),
        ("command", ["current_phase_execution", "authorization_header_output"], True),
    ],
)
def test_04_to_39_command_guards(monkeypatch, tmp_path: Path, path_key) -> None:
    files = make_inputs(tmp_path)
    file_key, key_path, value = path_key
    mutate_json(files[file_key], key_path, value)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_40_post_id_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["command"], ["target_post", "post_id"], 999)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_41_expected_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["command"], ["target_post", "expected_current_status"], "publish")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_42_ls6af_validation_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6af_validation"], ["status"], "BROKEN")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_43_ls6af_runner_final_gate_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6af_runtime"], ["actual_publish_runner_final_gate_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_44_ls6af_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6af_run"], ["next_phase", "phase"], "LS-6ZZ")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_45_ls6ae_validation_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ae_validation"], ["status"], "BROKEN")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_46_ls6ae_draft_verified_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ae_validation"], ["draft_verified"], False)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_47_ls6ae_returned_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ae_validation"], ["returned_post_status"], "publish")
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_48_ls6ae_final_preflight_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ae_final"], ["actual_publish_final_preflight_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_49_ls6ad_boundary_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ad_boundary"], ["actual_publish_execution_boundary_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_50_ls6ac_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ac_ready"], ["actual_publish_execute_now_final_confirmation_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_51_ls6ab_runner_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6ab_blocked"], ["actual_publish_execution_runner_executed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_52_ls6aa_preflight_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6aa_preflight"], ["actual_publish_execution_final_preflight_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_53_ls6z_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6z_ready"], ["final_explicit_publish_execution_command_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_54_ls6y_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6y_validation"], ["actual_publish_runner_boundary_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_55_ls6x_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6x_ready"], ["actual_publish_execution_gate_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_56_ls6v_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6v_ready"], ["final_execution_command_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_57_ls6t_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6t_ready"], ["execute_now_confirmation_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_58_ls6r_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6r_ready"], ["approval_label_consumed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_59_ls6oc1_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files["ls6oc1_lock"], ["rerun_allowed"], True)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def test_60_result_keeps_command_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_final_execution_command_consumed"] is False


def test_61_result_keeps_runner_gate_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_runner_final_gate_consumed"] is False


def test_62_result_keeps_final_preflight_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_final_preflight_consumed"] is False


def test_63_result_keeps_execution_boundary_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_boundary_consumed"] is False


def test_64_result_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_executed"] is False


def test_65_result_keeps_execution_allowed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_allowed_by_this_phase"] is False


def test_66_result_keeps_runner_allowed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_runner_execution_allowed_by_this_phase"] is False


def test_67_result_keeps_manual_publish_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["manual_publish_executed"] is False


def test_68_result_keeps_wordpress_api_call_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False


def test_69_result_keeps_credential_read_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["credential_env_read_executed"] is False


def test_70_result_next_phase_ls6ah(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["next_phase"]["phase"] == "LS-6AH"


def test_71_result_requires_runner_boundary_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_actual_publish_execution_runner_boundary"] is True


def test_72_result_requires_separate_phase_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_separate_publish_execution_phase"] is True


def test_73_result_publish_execution_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["publish_execution_still_blocked"] is True
