from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import run_start_ls6aa_manual_publish_actual_publish_execution_final_preflight as run_module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_cmd": tmp_path / "exchange/human_review/ls6z_cmd.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_preflight": tmp_path / "exchange/runtime/ls6y_preflight.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y_lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6x_gate": tmp_path / "exchange/human_review/ls6x_gate.json",
        "ls6w_validation": tmp_path / "exchange/logs/ls6w_validation.json",
        "ls6w_preflight": tmp_path / "exchange/runtime/ls6w_preflight.json",
        "ls6w_lock": tmp_path / "exchange/locks/ls6w_lock.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6v_cmd": tmp_path / "exchange/human_review/ls6v_cmd.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6t_confirmation": tmp_path / "exchange/human_review/ls6t_confirmation.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "credential_env": tmp_path / "credential.env",
        "wp_output": tmp_path / "exchange/runtime/wp_result.json",
        "preflight_output": tmp_path / "exchange/runtime/preflight_result.json",
        "lock_output": tmp_path / "exchange/locks/ls6aa.lock.json",
        "output": tmp_path / "exchange/logs/ls6aa_result.json",
        "report": tmp_path / "reports/ls6aa_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AA",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "title": "【テスト】",
                "asin": "B0TEST",
                "post_link": "https://example.com/?p=183",
            },
        },
    )

    write_json(
        files["ls6z_ready"],
        {
            "status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH",
            "command_status": "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "final_explicit_publish_execution_command_consumed": False,
            "manual_publish_executed": False,
            "actual_publish_execution_gate_consumed": False,
            "actual_publish_runner_boundary_consumed": False,
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_final_preflight": True,
            "publish_execution_still_blocked": True,
            "next_phase": {"phase": "LS-6AA"},
        },
    )
    write_json(
        files["ls6z_cmd"],
        {
            "command_status": "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "final_explicit_publish_execution_command": {
                "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
                "final_explicit_publish_execution_command_consumed": False,
            },
        },
    )

    write_json(
        files["ls6y_validation"],
        {
            "status": "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH",
            "actual_publish_runner_boundary_consumed": False,
            "manual_publish_executed": False,
        },
    )
    write_json(
        files["ls6y_preflight"],
        {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH"},
    )
    write_json(
        files["ls6y_lock"],
        {"status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH"},
    )

    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False})
    write_json(files["ls6x_gate"], {"actual_publish_execution_gate": {"actual_publish_execution_gate_consumed": False}})

    write_json(files["ls6w_validation"], {"status": "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "returned_post_status": "draft"})
    write_json(files["ls6w_preflight"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"})
    write_json(files["ls6w_lock"], {"status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH"})

    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False})
    write_json(files["ls6v_cmd"], {"final_execution_command": {"final_execution_command_consumed": False}})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6t_confirmation"], {"confirmation_status": "CONFIRMED_NO_PUBLISH_EXECUTION"})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6r_approval"], {"approval_status": "APPROVED_NO_PUBLISH_EXECUTION"})

    write_json(files["ls6p_lock"], {"rerun_allowed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    env_map = {
        "WORDPRESS_BASE_URL": "https://example.com",
        "WORDPRESS_USERNAME": "user",
        "WORDPRESS_APP_PASSWORD": "dummy-password",
    }
    files["credential_env"].write_text("\n".join(f"{k}={v}" for k, v in env_map.items()) + "\n", encoding="utf-8")
    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--ls6z-ready-result",
        str(files["ls6z_ready"]),
        "--ls6z-command-result",
        str(files["ls6z_cmd"]),
        "--ls6y-validation-result",
        str(files["ls6y_validation"]),
        "--ls6y-boundary-preflight-result",
        str(files["ls6y_preflight"]),
        "--ls6y-boundary-lock",
        str(files["ls6y_lock"]),
        "--ls6x-ready-result",
        str(files["ls6x_ready"]),
        "--ls6x-gate-result",
        str(files["ls6x_gate"]),
        "--ls6w-validation-result",
        str(files["ls6w_validation"]),
        "--ls6w-final-runner-preflight-result",
        str(files["ls6w_preflight"]),
        "--ls6w-final-runner-preflight-lock",
        str(files["ls6w_lock"]),
        "--ls6v-ready-result",
        str(files["ls6v_ready"]),
        "--ls6v-command-result",
        str(files["ls6v_cmd"]),
        "--ls6t-ready-result",
        str(files["ls6t_ready"]),
        "--ls6t-confirmation-result",
        str(files["ls6t_confirmation"]),
        "--ls6r-ready-result",
        str(files["ls6r_ready"]),
        "--ls6r-approval-result",
        str(files["ls6r_approval"]),
        "--ls6p-rerun-prevention-lock",
        str(files["ls6p_lock"]),
        "--ls6oc1-consumption-lock",
        str(files["ls6oc1_lock"]),
        "--credential-env",
        str(files["credential_env"]),
        "--wordpress-current-draft-status-output",
        str(files["wp_output"]),
        "--actual-publish-execution-final-preflight-output",
        str(files["preflight_output"]),
        "--actual-publish-execution-final-preflight-lock-output",
        str(files["lock_output"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
        "--verify-current-draft",
        "--record-actual-publish-execution-final-preflight",
        "--require-separated-actual-publish-execution-phase",
        "--require-explicit-execute-now-for-actual-publish",
    ]


def read_status(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["status"]


def test_missing_verify_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--verify-current-draft")
    monkeypatch.setattr("sys.argv", argv)

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"


def test_missing_record_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-actual-publish-execution-final-preflight")
    monkeypatch.setattr("sys.argv", argv)

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_PREFLIGHT_FLAG"


def test_missing_separated_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separated-actual-publish-execution-phase")
    monkeypatch.setattr("sys.argv", argv)

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG"


def test_missing_explicit_execute_now_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-explicit-execute-now-for-actual-publish")
    monkeypatch.setattr("sys.argv", argv)

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG"


def test_not_ready_when_upstream_invalid(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    write_json(files["ls6z_ready"], {"status": "BROKEN"})

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_failed_when_credential_env_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].unlink()

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_failed_when_credential_key_missing(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://example.com\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_failed_when_wordpress_get_id_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 999, "status": "draft"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_failed_when_wordpress_get_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "publish"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_failed_when_wordpress_get_http_error(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return None, "wordpress GET failed with HTTP 500"

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_failed_when_wordpress_get_invalid_json(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return None, "wordpress GET returned invalid JSON"

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_passed_with_valid_wordpress_get(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "draft", "title": {"rendered": "ok"}}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    run_payload = json.loads(files["output"].read_text(encoding="utf-8"))
    wp_payload = json.loads(files["wp_output"].read_text(encoding="utf-8"))
    preflight_payload = json.loads(files["preflight_output"].read_text(encoding="utf-8"))
    lock_payload = json.loads(files["lock_output"].read_text(encoding="utf-8"))

    assert run_payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
    assert run_payload["draft_verified"] is True
    assert run_payload["wordpress_get_executed"] is True
    assert run_payload["wordpress_get_post_id"] == 183
    assert run_payload["returned_post_status"] == "draft"
    assert run_payload["publish_execution_still_blocked"] is True
    assert run_payload["requires_explicit_execute_now_for_actual_publish"] is True
    assert run_payload["actual_publish_execution_final_preflight_consumed"] is False

    assert wp_payload["status"] == "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED"
    assert wp_payload["wordpress_get_executed"] is True
    assert wp_payload["returned_post_status"] == "draft"

    assert preflight_payload["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
    assert preflight_payload["current_post_status_verified"] is True
    assert preflight_payload["actual_publish_execution_final_preflight_consumed"] is False

    assert lock_payload["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH"
    assert lock_payload["rerun_allowed"] is False
    assert lock_payload["requires_next_phase"] == "LS-6AB"


def test_report_created(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "draft"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert files["report"].exists()
    body = files["report"].read_text(encoding="utf-8")
    assert "LS-6AA" in body


def test_no_secret_output_flags_stay_false_on_success(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "draft"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    run_payload = json.loads(files["output"].read_text(encoding="utf-8"))
    for key in [
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
    ]:
        assert run_payload[key] is False


def test_next_phase_fixed_ls6ab_on_success(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "draft"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["next_phase"]["phase"] == "LS-6AB"
    assert payload["next_phase"]["requires_explicit_execute_now_for_actual_publish"] is True


def test_not_ready_when_ls6z_manual_publish_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6z_ready"].read_text(encoding="utf-8"))
    payload["manual_publish_executed"] = True
    write_json(files["ls6z_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6v_final_execution_command_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6v_ready"].read_text(encoding="utf-8"))
    payload["final_execution_command_consumed"] = True
    write_json(files["ls6v_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6t_execute_now_confirmation_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6t_ready"].read_text(encoding="utf-8"))
    payload["execute_now_confirmation_consumed"] = True
    write_json(files["ls6t_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6r_approval_label_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6r_ready"].read_text(encoding="utf-8"))
    payload["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6oc1_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6oc1_lock"].read_text(encoding="utf-8"))
    payload["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_failed_when_wordpress_get_connection_error(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return None, "wordpress GET failed with connection error"

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["status"] == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_wordpress_write_methods_stay_false_on_success(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)

    def fake_verify(_base_url: str, _username: str, _password: str, _post_id: int):
        return {"id": 183, "status": "draft"}, None

    monkeypatch.setattr(run_module, "verify_current_draft", fake_verify)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = run_module.main()

    assert rc == 0
    wp_payload = json.loads(files["wp_output"].read_text(encoding="utf-8"))
    assert wp_payload["wordpress_post_executed"] is False
    assert wp_payload["wordpress_put_executed"] is False
    assert wp_payload["wordpress_patch_executed"] is False
    assert wp_payload["wordpress_delete_executed"] is False
