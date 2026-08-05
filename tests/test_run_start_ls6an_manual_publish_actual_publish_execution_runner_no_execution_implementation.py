from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation import (
    STATUS_NOT_READY,
    STATUS_NOT_READY_MISSING_ENFORCE_FLAG,
    STATUS_NOT_READY_MISSING_RECORD_FLAG,
    STATUS_NOT_READY_MISSING_SKELETON_FLAG,
    STATUS_READY,
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
        "ls6am_ready": tmp_path / "exchange/logs/ls6am_ready.json",
        "ls6am_gate": tmp_path / "exchange/human_review/ls6am_gate.json",
        "ls6al_ready": tmp_path / "exchange/logs/ls6al_ready.json",
        "ls6al_gate": tmp_path / "exchange/human_review/ls6al_gate.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1.lock.json",
        "runtime": tmp_path / "exchange/runtime/runtime.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/report.md",
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
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "runner_skeleton": {"path": str(files["skeleton"]).replace(str(tmp_path) + "/", "")},
            "required_previous_phase": {
                "ls6am": {
                    "required_ready_status": "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_READY_NO_PUBLISH",
                    "required_gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_RECORDED_NO_PUBLISH_EXECUTION",
                    "required_actual_publish_execution_runner_implementation_gate_label": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY",
                    "required_actual_publish_execution_runner_implementation_gate_consumed": False,
                    "required_actual_publish_execution_runner_implementation_allowed_by_this_phase": False,
                    "required_actual_publish_execution_runner_implemented_by_this_phase": False,
                    "required_actual_publish_execution_runner_file_created_by_this_phase": False,
                    "required_requires_actual_publish_execution_runner_no_execution_implementation": True,
                    "required_publish_execution_still_blocked": True,
                    "ready_result": str(files["ls6am_ready"]).replace(str(tmp_path) + "/", ""),
                    "implementation_gate_result": str(files["ls6am_gate"]).replace(str(tmp_path) + "/", ""),
                },
                "ls6al": {
                    "required_ready_status": "LS6AL_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PHASE_GATE_READY_NO_PUBLISH",
                    "required_gate_status": "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_RECORDED_NO_PUBLISH_EXECUTION",
                    "required_separated_actual_publish_execution_runner_phase_gate_consumed": False,
                    "ready_result": str(files["ls6al_ready"]).replace(str(tmp_path) + "/", ""),
                    "separated_phase_gate_result": str(files["ls6al_gate"]).replace(str(tmp_path) + "/", ""),
                },
                "ls6oc1": {
                    "required_rerun_allowed": False,
                    "consumption_lock": str(files["ls6oc1_lock"]).replace(str(tmp_path) + "/", ""),
                },
            },
        },
    )

    write_json(
        files["ls6am_ready"],
        {
            "status": "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_READY_NO_PUBLISH",
            "gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_runner_implementation_gate_label": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY",
            "actual_publish_execution_runner_implementation_gate_consumed": False,
            "actual_publish_execution_runner_implementation_allowed_by_this_phase": False,
            "actual_publish_execution_runner_implemented_by_this_phase": False,
            "actual_publish_execution_runner_file_created_by_this_phase": False,
            "requires_actual_publish_execution_runner_no_execution_implementation": True,
            "publish_execution_still_blocked": True,
        },
    )
    write_json(
        files["ls6am_gate"],
        {
            "gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "implementation_gate": {
                "actual_publish_execution_runner_implementation_gate_label": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY",
                "actual_publish_execution_runner_implementation_gate_consumed": False,
                "actual_publish_execution_runner_implementation_allowed_by_this_phase": False,
                "actual_publish_execution_runner_implemented_by_this_phase": False,
                "actual_publish_execution_runner_file_created_by_this_phase": False,
            },
        },
    )
    write_json(
        files["ls6al_ready"],
        {
            "status": "LS6AL_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PHASE_GATE_READY_NO_PUBLISH",
            "gate_status": "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "separated_actual_publish_execution_runner_phase_gate_consumed": False,
        },
    )
    write_json(
        files["ls6al_gate"],
        {
            "gate_status": "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_RECORDED_NO_PUBLISH_EXECUTION",
            "separated_phase_gate": {"separated_actual_publish_execution_runner_phase_gate_consumed": False},
        },
    )
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})
    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--runner-skeleton",
        str(files["skeleton"]),
        "--runtime-output",
        str(files["runtime"]),
        "--lock-output",
        str(files["lock"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
        "--record-no-execution-implementation",
        "--create-runner-skeleton-file",
        "--enforce-no-network-no-credential-no-publish",
    ]


def invoke(monkeypatch, files: dict[str, Path], argv: list[str] | None = None) -> dict:
    monkeypatch.setattr("sys.argv", argv or build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_missing_record_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--record-no-execution-implementation")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == STATUS_NOT_READY_MISSING_RECORD_FLAG


def test_missing_skeleton_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--create-runner-skeleton-file")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == STATUS_NOT_READY_MISSING_SKELETON_FLAG


def test_missing_enforce_flag_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--enforce-no-network-no-credential-no-publish")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == STATUS_NOT_READY_MISSING_ENFORCE_FLAG


def test_valid_run_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_READY
    assert out["publish_execution_still_blocked"] is True


@pytest.mark.parametrize(
    "file_key,key,value",
    [
        ("policy", "phase", "LS-6ZZ"),
        ("policy", "execution_mode", "BROKEN"),
        ("ls6am_ready", "status", "BROKEN"),
        ("ls6am_ready", "gate_status", "BROKEN"),
        ("ls6am_ready", "actual_publish_execution_runner_implementation_gate_label", "BROKEN"),
        ("ls6am_ready", "actual_publish_execution_runner_implementation_gate_consumed", True),
        ("ls6am_ready", "actual_publish_execution_runner_implementation_allowed_by_this_phase", True),
        ("ls6am_ready", "actual_publish_execution_runner_implemented_by_this_phase", True),
        ("ls6am_ready", "actual_publish_execution_runner_file_created_by_this_phase", True),
        ("ls6am_ready", "requires_actual_publish_execution_runner_no_execution_implementation", False),
        ("ls6am_ready", "publish_execution_still_blocked", False),
        ("ls6am_gate", "gate_status", "BROKEN"),
        ("ls6al_ready", "status", "BROKEN"),
        ("ls6al_ready", "gate_status", "BROKEN"),
        ("ls6al_ready", "separated_actual_publish_execution_runner_phase_gate_consumed", True),
        ("ls6al_gate", "gate_status", "BROKEN"),
        ("ls6oc1_lock", "rerun_allowed", True),
    ],
)
def test_required_mismatch_not_ready(monkeypatch, tmp_path: Path, file_key: str, key: str, value) -> None:
    files = make_inputs(tmp_path)
    payload = read_json(files[file_key])
    payload[key] = value
    write_json(files[file_key], payload)

    # Some required values can exist in both ready and human_review docs for the same phase.
    # Mutate the paired doc too so the expected value is fully removed from that phase scope.
    if file_key == "ls6am_ready":
        paired = read_json(files["ls6am_gate"])
        if key in paired:
            paired[key] = value
        if "implementation_gate" in paired and isinstance(paired["implementation_gate"], dict) and key in paired["implementation_gate"]:
            paired["implementation_gate"][key] = value
        write_json(files["ls6am_gate"], paired)
    if file_key == "ls6am_gate":
        paired = read_json(files["ls6am_ready"])
        if key in paired:
            paired[key] = value
        write_json(files["ls6am_ready"], paired)

    if file_key == "ls6al_ready":
        paired = read_json(files["ls6al_gate"])
        if key in paired:
            paired[key] = value
        if "separated_phase_gate" in paired and isinstance(paired["separated_phase_gate"], dict) and key in paired["separated_phase_gate"]:
            paired["separated_phase_gate"][key] = value
        write_json(files["ls6al_gate"], paired)
    if file_key == "ls6al_gate":
        paired = read_json(files["ls6al_ready"])
        if key in paired:
            paired[key] = value
        write_json(files["ls6al_ready"], paired)

    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "missing_key",
    [
        "ls6am_ready",
        "ls6am_gate",
        "ls6al_ready",
        "ls6al_gate",
        "ls6oc1_lock",
    ],
)
def test_missing_upstream_file_not_ready(monkeypatch, tmp_path: Path, missing_key: str) -> None:
    files = make_inputs(tmp_path)
    files[missing_key].unlink()
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
        "separated_actual_publish_execution_runner_phase_gate_consumed",
        "actual_publish_execution_runner_final_boundary_consumed",
        "actual_publish_execution_runner_execute_now_consumed",
        "actual_publish_execution_runner_final_preflight_consumed",
        "actual_publish_execution_runner_boundary_consumed",
        "actual_publish_final_execution_command_consumed",
        "actual_publish_runner_final_gate_consumed",
        "actual_publish_final_preflight_consumed",
        "actual_publish_execution_boundary_consumed",
        "actual_publish_execute_now_final_confirmation_consumed",
        "explicit_execute_now_for_actual_publish_consumed",
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
def test_no_execution_false_flags_fixed(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_READY
    assert out[field] is False


@pytest.mark.parametrize(
    "field",
    [
        "actual_publish_execution_runner_no_execution_implementation_ready",
        "actual_publish_execution_runner_implementation_gate_recorded",
        "actual_publish_execution_runner_implementation_allowed_by_this_phase",
        "actual_publish_execution_runner_implemented_by_this_phase",
        "actual_publish_execution_runner_file_created_by_this_phase",
        "separated_actual_publish_execution_runner_phase_gate_recorded",
        "actual_publish_execution_runner_final_boundary_ready",
        "actual_publish_execution_runner_execute_now_recorded",
        "actual_publish_execution_runner_final_preflight_ready",
        "actual_publish_execution_runner_boundary_ready",
        "actual_publish_final_execution_command_recorded",
        "actual_publish_runner_final_gate_ready",
        "actual_publish_final_preflight_ready",
        "actual_publish_execution_boundary_ready",
        "explicit_execute_now_for_actual_publish_required",
        "explicit_execute_now_for_actual_publish_received",
        "requires_actual_publish_execution_runner_no_execution_validation",
        "requires_actual_publish_execution_runner_execution_approval_gate",
        "requires_separate_publish_execution_phase",
        "publish_execution_still_blocked",
    ],
)
def test_required_true_flags(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_READY
    assert out[field] is True


def test_skeleton_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["skeleton"].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY
