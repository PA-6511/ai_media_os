from __future__ import annotations

import json
from pathlib import Path

from scripts.run_start_ls6ae_manual_publish_actual_publish_final_preflight import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
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
        "ls6v_command": tmp_path / "exchange/human_review/ls6v_command.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "credential_env": tmp_path / "credential.env",
        "wp_out": tmp_path / "exchange/runtime/wp_verify.json",
        "pf_out": tmp_path / "exchange/runtime/final_preflight.json",
        "lock_out": tmp_path / "exchange/locks/final_preflight.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6AE", "execution_mode": "ACTUAL_PUBLISH_FINAL_PREFLIGHT_ONLY_NO_PUBLISH", "production_status": "NO_PUBLISH"})
    write_json(files["ls6ad_run"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"})
    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "post_id": 183, "returned_post_status": "draft", "publish_execution_still_blocked": True})
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
    write_json(
        files["ls6ab_blocked"],
        {
            "actual_publish_execution_runner_ready": True,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_runner_blocked": True,
        },
    )
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_preflight"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})

    write_json(files["ls6z_ready"], {"status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_explicit_publish_execution_command_consumed": False})
    write_json(files["ls6z_command"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})

    write_json(files["ls6y_validation"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})

    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False})
    write_json(files["ls6v_command"], {"final_execution_command": {"final_execution_command_consumed": False}})

    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"confirmation": {"execute_now_confirmation_consumed": False}})

    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval": {"approval_label_consumed": False}})

    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    files["credential_env"].parent.mkdir(parents=True, exist_ok=True)
    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://hoshido.jp\nWORDPRESS_USERNAME=user\nWORDPRESS_APP_PASSWORD=pass\n",
        encoding="utf-8",
    )

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy", str(files["policy"]),
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
        "--ls6v-command-result", str(files["ls6v_command"]),
        "--ls6t-ready-result", str(files["ls6t_ready"]),
        "--ls6t-confirmation-result", str(files["ls6t_confirmation"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--credential-env", str(files["credential_env"]),
        "--wordpress-current-draft-status-output", str(files["wp_out"]),
        "--actual-publish-final-preflight-output", str(files["pf_out"]),
        "--actual-publish-final-preflight-lock-output", str(files["lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--verify-current-draft",
        "--record-actual-publish-final-preflight",
        "--require-actual-publish-runner-final-gate",
        "--require-separate-publish-execution-phase",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def mock_fetch(monkeypatch, response_code: int, response_body: dict, calls: list[int] | None = None) -> None:
    def _fake(base_url: str, username: str, app_password: str, post_id: int):
        if calls is not None:
            calls.append(post_id)
        return response_code, response_body

    monkeypatch.setattr(
        "scripts.run_start_ls6ae_manual_publish_actual_publish_final_preflight.fetch_wordpress_post",
        _fake,
    )


def test_01_missing_verify_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--verify-current-draft")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"


def test_02_missing_record_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-actual-publish-final-preflight")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"


def test_03_missing_runner_final_gate_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-actual-publish-runner-final-gate")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_RUNNER_FINAL_GATE_FLAG"


def test_04_missing_separate_phase_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def test_05_ls6ad_validation_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ad_validation"])
    p["status"] = "BROKEN"
    write_json(files["ls6ad_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_06_ls6ad_boundary_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ad_boundary"])
    p["actual_publish_execution_boundary_consumed"] = True
    write_json(files["ls6ad_boundary"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_07_ls6ac_confirmation_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["actual_publish_execute_now_final_confirmation_consumed"] = True
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_08_ls6ac_explicit_received_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["explicit_execute_now_for_actual_publish_received"] = False
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_09_ls6ac_explicit_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ac_ready"])
    p["explicit_execute_now_for_actual_publish_consumed"] = True
    write_json(files["ls6ac_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_10_ls6ab_runner_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_blocked"])
    p["actual_publish_execution_runner_executed"] = True
    write_json(files["ls6ab_blocked"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_11_ls6aa_preflight_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_preflight"])
    p["actual_publish_execution_final_preflight_consumed"] = True
    write_json(files["ls6aa_preflight"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_12_ls6z_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6z_ready"])
    p["final_explicit_publish_execution_command_consumed"] = True
    write_json(files["ls6z_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_13_ls6y_boundary_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6y_validation"])
    p["actual_publish_runner_boundary_consumed"] = True
    write_json(files["ls6y_validation"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_14_ls6x_gate_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6x_ready"])
    p["actual_publish_execution_gate_consumed"] = True
    write_json(files["ls6x_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_15_ls6v_final_execution_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6v_ready"])
    p["final_execution_command_consumed"] = True
    write_json(files["ls6v_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_16_ls6t_execute_now_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(files["ls6t_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_17_ls6r_approval_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_18_ls6oc1_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], p)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_19_credential_key_missing_failed_before_get(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://hoshido.jp\nWORDPRESS_USERNAME=user\n", encoding="utf-8")
    calls: list[int] = []
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"}, calls)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
    assert calls == []


def test_20_wordpress_get_http_500_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 500, {"error": "x"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_21_wordpress_get_id_mismatch_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 999, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_22_wordpress_get_status_not_draft_failed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "publish"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_23_valid_mocked_wordpress_get_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"


def test_24_post_put_patch_delete_not_called(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["wordpress_post_executed"] is False
    assert out["wordpress_put_executed"] is False
    assert out["wordpress_patch_executed"] is False
    assert out["wordpress_delete_executed"] is False


def test_25_credential_value_not_output(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    out = invoke(monkeypatch, files)
    assert out["credential_value_output"] is False
    assert out["credential_secret_output"] is False
    assert "WORDPRESS_APP_PASSWORD" not in json.dumps(out, ensure_ascii=False)


def test_26_final_preflight_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mock_fetch(monkeypatch, 200, {"id": 183, "status": "draft"})
    invoke(monkeypatch, files)
    lock = read_json(files["lock_out"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"
