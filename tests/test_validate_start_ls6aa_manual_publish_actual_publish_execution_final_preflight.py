from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6aa_manual_publish_actual_publish_execution_final_preflight import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "wp": tmp_path / "exchange/runtime/wp.json",
        "preflight": tmp_path / "exchange/runtime/preflight.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "ls6z_ready": tmp_path / "exchange/logs/ls6z_ready.json",
        "ls6z_cmd": tmp_path / "exchange/human_review/ls6z_cmd.json",
        "ls6y_validation": tmp_path / "exchange/logs/ls6y_validation.json",
        "ls6y_lock": tmp_path / "exchange/locks/ls6y_lock.json",
        "ls6x_ready": tmp_path / "exchange/logs/ls6x_ready.json",
        "ls6w_validation": tmp_path / "exchange/logs/ls6w_validation.json",
        "ls6v_ready": tmp_path / "exchange/logs/ls6v_ready.json",
        "ls6t_ready": tmp_path / "exchange/logs/ls6t_ready.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1.lock.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"phase": "LS-6AA"})

    write_json(
        files["wp"],
        {
            "status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED",
            "post_id": 183,
            "returned_post_status": "draft",
            "wordpress_get_executed": True,
            "wordpress_get_post_id": 183,
            "wordpress_post_executed": False,
            "wordpress_put_executed": False,
            "wordpress_patch_executed": False,
            "wordpress_delete_executed": False,
        },
    )

    base_false = {
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "final_explicit_publish_execution_command_consumed": False,
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
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
    }

    write_json(
        files["preflight"],
        {
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "current_post_status_verified": True,
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "actual_publish_execution_final_preflight_ready": True,
            "requires_separate_actual_publish_execution_phase": True,
            "requires_explicit_execute_now_for_actual_publish": True,
            "publish_execution_still_blocked": True,
            **base_false,
        },
    )

    write_json(
        files["lock"],
        {
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "requires_next_phase": "LS-6AB",
            "actual_publish_runner_boundary_consumed": False,
        },
    )

    write_json(
        files["run"],
        {
            "status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH",
            "post_id": 183,
            "draft_verified": True,
            "returned_post_status": "draft",
            "wordpress_get_executed": True,
            "wordpress_get_post_id": 183,
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "actual_publish_execution_final_preflight_ready": True,
            "requires_separate_actual_publish_execution_phase": True,
            "requires_explicit_execute_now_for_actual_publish": True,
            "publish_execution_still_blocked": True,
            "credential_env_read_executed": True,
            "next_phase": {
                "phase": "LS-6AB",
                "requires_explicit_execute_now_for_actual_publish": True,
            },
            **base_false,
        },
    )

    write_json(files["ls6z_ready"], {"final_explicit_publish_execution_command_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6z_cmd"], {"final_explicit_publish_execution_command": {"final_explicit_publish_execution_command_consumed": False}})
    write_json(files["ls6y_validation"], {"actual_publish_runner_boundary_consumed": False, "manual_publish_executed": False})
    write_json(files["ls6y_lock"], {"actual_publish_runner_boundary_consumed": False})
    write_json(files["ls6x_ready"], {"actual_publish_execution_gate_consumed": False})
    write_json(files["ls6w_validation"], {"returned_post_status": "draft"})
    write_json(files["ls6v_ready"], {"final_execution_command_consumed": False})
    write_json(files["ls6t_ready"], {"execute_now_confirmation_consumed": False})
    write_json(files["ls6r_ready"], {"approval_label_consumed": False})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--wordpress-current-draft-status-result",
        str(files["wp"]),
        "--actual-publish-execution-final-preflight-result",
        str(files["preflight"]),
        "--actual-publish-execution-final-preflight-lock",
        str(files["lock"]),
        "--run-result",
        str(files["run"]),
        "--ls6z-ready-result",
        str(files["ls6z_ready"]),
        "--ls6z-command-result",
        str(files["ls6z_cmd"]),
        "--ls6y-validation-result",
        str(files["ls6y_validation"]),
        "--ls6y-boundary-lock",
        str(files["ls6y_lock"]),
        "--ls6x-ready-result",
        str(files["ls6x_ready"]),
        "--ls6w-validation-result",
        str(files["ls6w_validation"]),
        "--ls6v-ready-result",
        str(files["ls6v_ready"]),
        "--ls6t-ready-result",
        str(files["ls6t_ready"]),
        "--ls6r-ready-result",
        str(files["ls6r_ready"]),
        "--ls6oc1-consumption-lock",
        str(files["ls6oc1_lock"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]


def read_status(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["status"]


def test_validated_success(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"


def test_not_ready_when_run_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    run_payload = json.loads(files["run"].read_text(encoding="utf-8"))
    run_payload["status"] = "BROKEN"
    write_json(files["run"], run_payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_wp_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    wp_payload = json.loads(files["wp"].read_text(encoding="utf-8"))
    wp_payload["status"] = "FAILED"
    write_json(files["wp"], wp_payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_wp_returned_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    wp_payload = json.loads(files["wp"].read_text(encoding="utf-8"))
    wp_payload["returned_post_status"] = "publish"
    write_json(files["wp"], wp_payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_preflight_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["preflight"].read_text(encoding="utf-8"))
    payload["status"] = "BROKEN"
    write_json(files["preflight"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_lock_not_locked(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["lock"].read_text(encoding="utf-8"))
    payload["locked"] = False
    write_json(files["lock"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_lock_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["lock"].read_text(encoding="utf-8"))
    payload["rerun_allowed"] = True
    write_json(files["lock"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_run_false_flags_broken(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["run"].read_text(encoding="utf-8"))
    payload["publish_executed"] = True
    write_json(files["run"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_preflight_false_flags_broken(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["preflight"].read_text(encoding="utf-8"))
    payload["manual_publish_executed"] = True
    write_json(files["preflight"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_secret_flags_broken(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["run"].read_text(encoding="utf-8"))
    payload["credential_secret_output"] = True
    write_json(files["run"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6z_consumed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6z_ready"].read_text(encoding="utf-8"))
    payload["final_explicit_publish_execution_command_consumed"] = True
    write_json(files["ls6z_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6y_consumed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6y_validation"].read_text(encoding="utf-8"))
    payload["actual_publish_runner_boundary_consumed"] = True
    write_json(files["ls6y_validation"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6x_consumed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6x_ready"].read_text(encoding="utf-8"))
    payload["actual_publish_execution_gate_consumed"] = True
    write_json(files["ls6x_ready"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["run"].read_text(encoding="utf-8"))
    payload["next_phase"]["phase"] = "LS-6ZZ"
    write_json(files["run"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_report_created(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert files["report"].exists()
    assert "Validation Report" in files["report"].read_text(encoding="utf-8")


def test_output_contains_ls6ab_next_phase(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    payload = json.loads(files["output"].read_text(encoding="utf-8"))
    assert payload["next_phase"]["phase"] == "LS-6AB"
    assert payload["next_phase"]["requires_explicit_execute_now_for_actual_publish"] is True


@pytest.mark.parametrize(
    "flag_name",
    [
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "authorization_header_output",
    ],
)
def test_not_ready_when_run_flag_true(monkeypatch, tmp_path: Path, flag_name: str) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["run"].read_text(encoding="utf-8"))
    payload[flag_name] = True
    write_json(files["run"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"


def test_not_ready_when_ls6oc1_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    payload = json.loads(files["ls6oc1_lock"].read_text(encoding="utf-8"))
    payload["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], payload)

    monkeypatch.setattr("sys.argv", build_argv(files))

    rc = main()

    assert rc == 0
    assert read_status(files["output"]) == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"
