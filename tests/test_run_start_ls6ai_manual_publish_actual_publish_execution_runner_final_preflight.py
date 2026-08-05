from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, key: str, value) -> None:
    data = read_json(path)
    data[key] = value
    write_json(path, data)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6ah_run": tmp_path / "exchange/logs/ls6ah_run.json",
        "ls6ah_validation": tmp_path / "exchange/logs/ls6ah_validation.json",
        "ls6ah_boundary": tmp_path / "exchange/runtime/ls6ah_boundary.json",
        "ls6ah_lock": tmp_path / "exchange/locks/ls6ah_boundary.lock.json",
        "ls6ag_ready": tmp_path / "exchange/logs/ls6ag_ready.json",
        "ls6ag_command": tmp_path / "exchange/human_review/ls6ag_command.json",
        "ls6af_validation": tmp_path / "exchange/logs/ls6af_validation.json",
        "ls6af_result": tmp_path / "exchange/runtime/ls6af_result.json",
        "ls6af_lock": tmp_path / "exchange/locks/ls6af.lock.json",
        "ls6ae_validation": tmp_path / "exchange/logs/ls6ae_validation.json",
        "ls6ae_wp": tmp_path / "exchange/runtime/ls6ae_wp.json",
        "ls6ae_result": tmp_path / "exchange/runtime/ls6ae_result.json",
        "ls6ae_lock": tmp_path / "exchange/locks/ls6ae.lock.json",
        "ls6ad_validation": tmp_path / "exchange/logs/ls6ad_validation.json",
        "ls6ad_result": tmp_path / "exchange/runtime/ls6ad_result.json",
        "ls6ad_lock": tmp_path / "exchange/locks/ls6ad.lock.json",
        "ls6ac_ready": tmp_path / "exchange/logs/ls6ac_ready.json",
        "ls6ac_confirmation": tmp_path / "exchange/human_review/ls6ac_confirmation.json",
        "ls6ab_validation": tmp_path / "exchange/logs/ls6ab_validation.json",
        "ls6ab_result": tmp_path / "exchange/runtime/ls6ab_result.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab.lock.json",
        "ls6aa_validation": tmp_path / "exchange/logs/ls6aa_validation.json",
        "ls6aa_result": tmp_path / "exchange/runtime/ls6aa_result.json",
        "ls6aa_lock": tmp_path / "exchange/locks/ls6aa.lock.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_command": tmp_path / "exchange/human_review/ls6z_command.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y.lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p.lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1.lock.json",
        "credential_env": tmp_path / "credential.env",
        "wp_out": tmp_path / "exchange/runtime/wp_result.json",
        "pf_out": tmp_path / "exchange/runtime/final_preflight.json",
        "lock_out": tmp_path / "exchange/locks/final_preflight.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6AI", "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY_NO_PUBLISH", "production_status": "NO_PUBLISH"})

    write_json(
        files["ls6ah_run"],
        {
            "status": "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "actual_publish_execution_runner_boundary_consumed": False,
            "actual_publish_final_execution_command_consumed": False,
            "actual_publish_runner_final_gate_consumed": False,
            "actual_publish_final_preflight_consumed": False,
            "actual_publish_execution_boundary_consumed": False,
            "actual_publish_execute_now_final_confirmation_consumed": False,
            "explicit_execute_now_for_actual_publish_consumed": False,
            "actual_publish_execution_runner_executed": False,
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
            "next_phase": {"phase": "LS-6AI"},
        },
    )
    write_json(files["ls6ah_validation"], {"status": "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ah_boundary"], {"actual_publish_execution_runner_boundary_ready": True, "actual_publish_execution_runner_boundary_consumed": False})
    write_json(files["ls6ah_lock"], {"actual_publish_execution_runner_boundary_consumed": False})

    write_json(files["ls6ag_ready"], {"status": "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "actual_publish_final_execution_command_consumed": False})
    write_json(files["ls6ag_command"], {"command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "actual_publish_final_execution_command": {"actual_publish_final_execution_command_consumed": False}})

    write_json(files["ls6af_validation"], {"status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6af_result"], {"actual_publish_runner_final_gate_ready": True, "actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6af_lock"], {"actual_publish_runner_final_gate_consumed": False})

    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "draft_verified": True, "returned_post_status": "draft"})
    write_json(files["ls6ae_wp"], {"returned_post_status": "draft"})
    write_json(files["ls6ae_result"], {"actual_publish_final_preflight_ready": True, "actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ae_lock"], {"actual_publish_final_preflight_consumed": False})

    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_result"], {"actual_publish_execution_boundary_ready": True, "actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})

    write_json(files["ls6ac_ready"], {"status": "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "actual_publish_execute_now_final_confirmation_consumed": False, "explicit_execute_now_for_actual_publish_required": True, "explicit_execute_now_for_actual_publish_received": True, "explicit_execute_now_for_actual_publish_consumed": False})
    write_json(files["ls6ac_confirmation"], {"actual_publish_execute_now_final_confirmation": {"actual_publish_execute_now_final_confirmation_consumed": False, "explicit_execute_now_for_actual_publish_consumed": False}})

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_result"], {"actual_publish_execution_runner_ready": True, "actual_publish_execution_runner_executed": False, "actual_publish_execution_runner_blocked": True})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_result"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
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

    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://hoshido.jp\nWORDPRESS_USERNAME=user\nWORDPRESS_APP_PASSWORD=pass\n",
        encoding="utf-8",
    )

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6ah-run-result", str(files["ls6ah_run"]),
        "--ls6ah-validation-result", str(files["ls6ah_validation"]),
        "--ls6ah-boundary-result", str(files["ls6ah_boundary"]),
        "--ls6ah-boundary-lock", str(files["ls6ah_lock"]),
        "--ls6ag-ready-result", str(files["ls6ag_ready"]),
        "--ls6ag-command-result", str(files["ls6ag_command"]),
        "--ls6af-validation-result", str(files["ls6af_validation"]),
        "--ls6af-runner-final-gate-result", str(files["ls6af_result"]),
        "--ls6af-runner-final-gate-lock", str(files["ls6af_lock"]),
        "--ls6ae-validation-result", str(files["ls6ae_validation"]),
        "--ls6ae-wordpress-current-draft-status-result", str(files["ls6ae_wp"]),
        "--ls6ae-final-preflight-result", str(files["ls6ae_result"]),
        "--ls6ae-final-preflight-lock", str(files["ls6ae_lock"]),
        "--ls6ad-validation-result", str(files["ls6ad_validation"]),
        "--ls6ad-boundary-result", str(files["ls6ad_result"]),
        "--ls6ad-boundary-lock", str(files["ls6ad_lock"]),
        "--ls6ac-ready-result", str(files["ls6ac_ready"]),
        "--ls6ac-confirmation-result", str(files["ls6ac_confirmation"]),
        "--ls6ab-validation-result", str(files["ls6ab_validation"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_result"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
        "--ls6aa-validation-result", str(files["ls6aa_validation"]),
        "--ls6aa-final-preflight-result", str(files["ls6aa_result"]),
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
        "--credential-env", str(files["credential_env"]),
        "--wordpress-current-draft-status-output", str(files["wp_out"]),
        "--actual-publish-execution-runner-final-preflight-output", str(files["pf_out"]),
        "--actual-publish-execution-runner-final-preflight-lock-output", str(files["lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--verify-current-draft",
        "--record-actual-publish-execution-runner-final-preflight",
        "--require-actual-publish-execution-runner-execute-now",
        "--require-separate-publish-execution-phase",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def mock_fetch(monkeypatch, code: int, payload: dict, calls: list[int] | None = None) -> None:
    def _fake(base_url: str, username: str, app_password: str, post_id: int):
        if calls is not None:
            calls.append(post_id)
        return code, payload

    monkeypatch.setattr(
        "scripts.run_start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight.fetch_wordpress_post",
        _fake,
    )


def test_01_missing_verify_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--verify-current-draft")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"


def test_02_missing_record_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-actual-publish-execution-runner-final-preflight")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"


def test_03_missing_execute_now_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-actual-publish-execution-runner-execute-now")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_EXECUTE_NOW_FLAG"


def test_04_missing_separate_phase_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda f: mutate(f["ls6ah_validation"], "status", "BROKEN"),
        lambda f: mutate(f["ls6ah_boundary"], "actual_publish_execution_runner_boundary_consumed", True),
        lambda f: mutate(f["ls6ag_ready"], "actual_publish_final_execution_command_consumed", True),
        lambda f: mutate(f["ls6af_result"], "actual_publish_runner_final_gate_consumed", True),
        lambda f: mutate(f["ls6ae_result"], "actual_publish_final_preflight_consumed", True),
        lambda f: mutate(f["ls6ad_result"], "actual_publish_execution_boundary_consumed", True),
        lambda f: mutate(f["ls6ac_ready"], "actual_publish_execute_now_final_confirmation_consumed", True),
        lambda f: mutate(f["ls6ac_ready"], "explicit_execute_now_for_actual_publish_consumed", True),
        lambda f: mutate(f["ls6ab_result"], "actual_publish_execution_runner_executed", True),
        lambda f: mutate(f["ls6aa_result"], "actual_publish_execution_final_preflight_consumed", True),
        lambda f: mutate(f["ls6z_ready"], "final_explicit_publish_execution_command_consumed", True),
        lambda f: mutate(f["ls6y_validation"], "actual_publish_runner_boundary_consumed", True),
        lambda f: mutate(f["ls6x_ready"], "actual_publish_execution_gate_consumed", True),
        lambda f: mutate(f["ls6v_ready"], "final_execution_command_consumed", True),
        lambda f: mutate(f["ls6t_ready"], "execute_now_confirmation_consumed", True),
        lambda f: mutate(f["ls6r_ready"], "approval_label_consumed", True),
        lambda f: mutate(f["ls6oc1_lock"], "rerun_allowed", True),
    ],
)
def test_05_to_21_not_ready(monkeypatch, tmp_path: Path, mutator) -> None:
    files = make_inputs(tmp_path)
    mutator(files)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"


def test_22_credential_key_missing_failed_before_get(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://hoshido.jp\nWORDPRESS_USERNAME=user\n", encoding="utf-8")
    calls: list[int] = []
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"}, calls)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
    assert calls == []


def test_23_wordpress_get_http_500_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 500, {"error": "x"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_24_wordpress_get_id_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 999, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_25_wordpress_get_status_not_draft_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "publish"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_26_valid_mocked_wordpress_get_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"


def test_27_post_put_patch_delete_not_called(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["wordpress_post_executed"] is False
    assert out["wordpress_put_executed"] is False
    assert out["wordpress_patch_executed"] is False
    assert out["wordpress_delete_executed"] is False


def test_28_credential_value_not_output(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["credential_value_output"] is False
    assert out["authorization_header_output"] is False
    assert "WORDPRESS_APP_PASSWORD" not in json.dumps(out, ensure_ascii=False)


def test_29_final_preflight_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    invoke(monkeypatch, files)
    lock = read_json(files["lock_out"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"
