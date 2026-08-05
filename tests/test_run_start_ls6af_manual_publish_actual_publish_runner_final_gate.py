from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6af_manual_publish_actual_publish_runner_final_gate import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6ae_run": tmp_path / "exchange/logs/ls6ae_run.json",
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
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "runtime_out": tmp_path / "exchange/runtime/ls6af_runtime.json",
        "lock_out": tmp_path / "exchange/locks/ls6af_lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AF",
            "execution_mode": "ACTUAL_PUBLISH_RUNNER_FINAL_GATE_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
        },
    )

    write_json(
        files["ls6ae_run"],
        {
            "status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "draft_verified": True,
            "wordpress_get_executed": True,
            "wordpress_get_post_id": 183,
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
            "actual_publish_execution_final_preflight_consumed": False,
            "final_explicit_publish_execution_command_consumed": False,
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
            "publish_execution_still_blocked": True,
            "requires_actual_publish_runner_final_gate": True,
            "requires_separate_publish_execution_phase": True,
            "next_phase": {"phase": "LS-6AF"},
        },
    )
    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ae_wp"], {"returned_post_status": "draft", "wordpress_get_executed": True})
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
    write_json(
        files["ls6ac_confirmation"],
        {
            "actual_publish_execute_now_final_confirmation": {
                "actual_publish_execute_now_final_confirmation_consumed": False,
                "explicit_execute_now_for_actual_publish_consumed": False,
            }
        },
    )

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"actual_publish_execution_runner_ready": True, "actual_publish_execution_runner_executed": False, "actual_publish_execution_runner_blocked": True})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})

    write_json(files["ls6z_ready"], {"status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})

    write_json(files["ls6y_validation"], {"status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})

    write_json(files["ls6x_ready"], {"status": "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6v_ready"], {"status": "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_execution_command_consumed": False})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})

    write_json(files["ls6t_ready"], {"status": "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"confirmation": {"execute_now_confirmation_consumed": False}})

    write_json(files["ls6r_ready"], {"status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})

    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6ae-run-result", str(files["ls6ae_run"]),
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
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--actual-publish-runner-final-gate-output", str(files["runtime_out"]),
        "--actual-publish-runner-final-gate-lock-output", str(files["lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--record-actual-publish-runner-final-gate",
        "--require-actual-publish-final-execution-command",
        "--require-separate-publish-execution-phase",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_01_missing_record_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-actual-publish-runner-final-gate")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_RECORD_FLAG"


def test_02_missing_final_execution_command_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-actual-publish-final-execution-command")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_FINAL_EXECUTION_COMMAND_FLAG"


def test_03_missing_separate_execution_phase_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda f: mutate(f["ls6ae_validation"], "status", "BROKEN"),
        lambda f: mutate(f["ls6ae_run"], "draft_verified", False),
        lambda f: mutate(f["ls6ae_run"], "returned_post_status", "publish"),
        lambda f: mutate(f["ls6ae_final"], "actual_publish_final_preflight_consumed", True),
        lambda f: mutate(f["ls6ad_boundary"], "actual_publish_execution_boundary_consumed", True),
        lambda f: mutate(f["ls6ac_ready"], "actual_publish_execute_now_final_confirmation_consumed", True),
        lambda f: mutate(f["ls6ac_ready"], "explicit_execute_now_for_actual_publish_consumed", True),
        lambda f: mutate(f["ls6ab_blocked"], "actual_publish_execution_runner_executed", True),
        lambda f: mutate(f["ls6aa_preflight"], "actual_publish_execution_final_preflight_consumed", True),
        lambda f: mutate(f["ls6z_ready"], "final_explicit_publish_execution_command_consumed", True),
        lambda f: mutate(f["ls6y_validation"], "actual_publish_runner_boundary_consumed", True),
        lambda f: mutate(f["ls6x_ready"], "actual_publish_execution_gate_consumed", True),
        lambda f: mutate(f["ls6v_ready"], "final_execution_command_consumed", True),
        lambda f: mutate(f["ls6t_ready"], "execute_now_confirmation_consumed", True),
        lambda f: mutate(f["ls6r_ready"], "approval_label_consumed", True),
        lambda f: mutate(f["ls6oc1_lock"], "rerun_allowed", True),
    ],
)
def test_04_to_19_not_ready_by_upstream_mismatch(monkeypatch, tmp_path: Path, mutator) -> None:
    files = make_inputs(tmp_path)
    mutator(files)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY"


def mutate(path: Path, key: str, value) -> None:
    p = read_json(path)
    p[key] = value
    write_json(path, p)


def test_20_valid_runner_final_gate_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_PASSED_NO_PUBLISH"


def test_21_no_wordpress_no_credential_read(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False
    assert out["wordpress_get_executed"] is False
    assert out["credential_env_read_executed"] is False


@pytest.mark.parametrize(
    "field",
    [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "credential_env_read_executed",
        "actual_publish_runner_final_gate_consumed",
        "actual_publish_final_preflight_consumed",
        "actual_publish_execution_boundary_consumed",
        "actual_publish_execute_now_final_confirmation_consumed",
        "explicit_execute_now_for_actual_publish_consumed",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
    ],
)
def test_22_to_31_output_false_guards(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out[field] is False


def test_32_runner_final_gate_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    lock = read_json(files["lock_out"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_LOCKED_NO_PUBLISH"
