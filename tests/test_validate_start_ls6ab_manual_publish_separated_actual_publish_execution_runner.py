from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ab_manual_publish_separated_actual_publish_execution_runner import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "blocked": tmp_path / "exchange/runtime/blocked.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "ls6aa_run": tmp_path / "exchange/logs/ls6aa_run.json",
        "ls6aa_val": tmp_path / "exchange/logs/ls6aa_val.json",
        "ls6aa_pf": tmp_path / "exchange/runtime/ls6aa_pf.json",
        "ls6aa_lock": tmp_path / "exchange/locks/ls6aa_lock.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_command": tmp_path / "exchange/human_review/ls6z_command.json",
        "ls6y_val": tmp_path / "exchange/logs/ls6y_val.json",
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

    write_json(files["policy"], {"phase": "LS-6AB"})

    base = {
        "phase": "LS-6AB",
        "post_id": 183,
        "returned_post_status": "draft",
        "ls6aa_final_preflight_validated": True,
        "ls6aa_fix_a_test_coverage_completed": True,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": False,
        "explicit_execute_now_for_actual_publish_consumed": False,
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
        "requires_actual_publish_execute_now_confirmation": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }

    write_json(
        files["run"],
        {
            "status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "next_phase": {
                "phase": "LS-6AC",
                "execution_allowed": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execute_now_confirmation": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
            **base,
        },
    )

    write_json(
        files["blocked"],
        {
            "document_type": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_RESULT",
            "status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            **base,
        },
    )

    write_json(
        files["lock"],
        {
            "status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "requires_next_phase": "LS-6AC",
        },
    )

    write_json(files["ls6aa_run"], {"actual_publish_execution_final_preflight_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6aa_val"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_pf"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6aa_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"})

    write_json(files["ls6z_ready"], {"final_explicit_publish_execution_command_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})
    write_json(files["ls6y_val"], {"actual_publish_runner_boundary_consumed": False})
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
        "--blocked-runner-result", str(files["blocked"]),
        "--blocked-runner-lock", str(files["lock"]),
        "--run-result", str(files["run"]),
        "--ls6aa-run-result", str(files["ls6aa_run"]),
        "--ls6aa-validation-result", str(files["ls6aa_val"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_pf"]),
        "--ls6aa-final-preflight-lock", str(files["ls6aa_lock"]),
        "--ls6z-ready-result", str(files["ls6z_ready"]),
        "--ls6z-command-result", str(files["ls6z_command"]),
        "--ls6y-validation-result", str(files["ls6y_val"]),
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


def test_validator_valid_result(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "manual_publish_executed",
        "actual_publish_execution_runner_executed",
        "explicit_execute_now_for_actual_publish_received",
        "explicit_execute_now_for_actual_publish_consumed",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "credential_env_read_executed",
        "credential_value_output",
        "authorization_header_output",
    ],
)
def test_validator_detects_true_flags(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload[field] = True
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_validator_detects_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    lock_payload = read_json(files["lock"])
    lock_payload["rerun_allowed"] = True
    write_json(files["lock"], lock_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_validator_detects_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload["next_phase"]["phase"] = "LS-6ZZ"
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"


def test_validator_detects_publish_blocked_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload["publish_execution_still_blocked"] = False
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"
