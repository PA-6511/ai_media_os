from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation import (
    STATUS_NOT_READY,
    STATUS_VALIDATED,
    main,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "skeleton": tmp_path / "scripts/skeleton.py",
        "runtime": tmp_path / "exchange/runtime/runtime.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run": tmp_path / "exchange/logs/run.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    files["skeleton"].parent.mkdir(parents=True, exist_ok=True)
    files["skeleton"].write_text(
        "#!/usr/bin/env python3\n"
        "def build_no_execution_runner_blueprint():\n"
        "    return {\n"
        "        'execution_enabled': False,\n"
        "        'network_call_enabled': False,\n"
        "        'credential_read_enabled': False,\n"
        "        'publish_enabled': False,\n"
        "    }\n",
        encoding="utf-8",
    )

    write_json(
        files["policy"],
        {
            "phase": "LS-6AN",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        },
    )

    run_payload = {
        "phase": "LS-6AN",
        "status": "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH",
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "returned_post_status": "draft",
        "actual_publish_execution_runner_no_execution_implementation_ready": True,
        "actual_publish_execution_runner_no_execution_implementation_consumed": False,
        "actual_publish_execution_runner_implementation_gate_recorded": True,
        "actual_publish_execution_runner_implementation_gate_consumed": False,
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": True,
        "actual_publish_execution_runner_implemented_by_this_phase": True,
        "actual_publish_execution_runner_file_created_by_this_phase": True,
        "actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase": False,
        "actual_publish_execution_runner_live_publish_path_implemented_by_this_phase": False,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
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
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
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
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_no_execution_validation": True,
        "requires_actual_publish_execution_runner_execution_approval_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AO",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_no_execution_validation": True,
            "requires_actual_publish_execution_runner_execution_approval_gate": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
    }

    runtime_payload = {
        "phase": "LS-6AN",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RECORDED_NO_PUBLISH",
        "locked": True,
    }

    lock_payload = {
        "phase": "LS-6AN",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCKED_NO_PUBLISH",
        "locked": True,
        "requires_next_phase": "LS-6AO",
    }

    write_json(files["run"], run_payload)
    write_json(files["runtime"], runtime_payload)
    write_json(files["lock"], lock_payload)
    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--runner-skeleton",
        str(files["skeleton"]),
        "--runtime-result",
        str(files["runtime"]),
        "--lock-result",
        str(files["lock"]),
        "--run-result",
        str(files["run"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]


def invoke(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_validator_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "BROKEN"),
        ("post_id", 999),
        ("returned_post_status", "publish"),
        ("actual_publish_execution_runner_no_execution_implementation_ready", False),
        ("actual_publish_execution_runner_implementation_gate_recorded", False),
        ("actual_publish_execution_runner_implementation_allowed_by_this_phase", False),
        ("actual_publish_execution_runner_implemented_by_this_phase", False),
        ("actual_publish_execution_runner_file_created_by_this_phase", False),
    ],
)
def test_validator_detects_required_true_break(monkeypatch, tmp_path: Path, key: str, value) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload[key] = value
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "field",
    [
        "actual_publish_execution_runner_no_execution_implementation_consumed",
        "actual_publish_execution_runner_implementation_gate_consumed",
        "actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase",
        "actual_publish_execution_runner_live_publish_path_implemented_by_this_phase",
        "actual_publish_execution_runner_network_call_enabled",
        "actual_publish_execution_runner_credential_read_enabled",
        "actual_publish_execution_runner_publish_enabled",
        "actual_publish_execution_runner_execution_enabled",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_draft_creation_executed_by_this_phase",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "rerun_allowed",
        "ls6oc1_rerun_executed",
    ],
)
def test_validator_detects_false_flags(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload[field] = True
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "where,key,value",
    [
        ("runtime", "status", "BROKEN"),
        ("runtime", "locked", False),
        ("lock", "status", "BROKEN"),
        ("lock", "locked", False),
        ("lock", "requires_next_phase", "LS-6ZZ"),
    ],
)
def test_validator_detects_runtime_lock_break(monkeypatch, tmp_path: Path, where: str, key: str, value) -> None:
    files = make_inputs(tmp_path)
    payload = read_json(files[where])
    payload[key] = value
    write_json(files[where], payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "key,value",
    [
        ("phase", "LS-6ZZ"),
        ("execution_mode", "BROKEN"),
    ],
)
def test_validator_detects_policy_break(monkeypatch, tmp_path: Path, key: str, value) -> None:
    files = make_inputs(tmp_path)
    payload = read_json(files["policy"])
    payload[key] = value
    write_json(files["policy"], payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "next_key,next_value",
    [
        ("phase", "LS-6ZZ"),
        ("execution_allowed", True),
        ("requires_actual_publish_execution_runner_no_execution_validation", False),
        ("requires_actual_publish_execution_runner_execution_approval_gate", False),
        ("requires_separate_publish_execution_phase", False),
        ("publish_execution_still_blocked", False),
    ],
)
def test_validator_detects_next_phase_break(monkeypatch, tmp_path: Path, next_key: str, next_value) -> None:
    files = make_inputs(tmp_path)
    run_payload = read_json(files["run"])
    run_payload["next_phase"][next_key] = next_value
    write_json(files["run"], run_payload)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_validator_detects_missing_skeleton(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["skeleton"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "banned_line",
    [
        "import urllib.request\n",
        "import http.client\n",
        "import requests\n",
        "from dotenv import load_dotenv\n",
        "token = 'Authorization'\n",
        "url = '/wp-json/wp/v2/posts'\n",
        "execution_enabled = True\n",
        "publish_enabled = True\n",
    ],
)
def test_validator_detects_banned_tokens_in_skeleton(monkeypatch, tmp_path: Path, banned_line: str) -> None:
    files = make_inputs(tmp_path)
    content = files["skeleton"].read_text(encoding="utf-8")
    files["skeleton"].write_text(content + banned_line, encoding="utf-8")
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY
