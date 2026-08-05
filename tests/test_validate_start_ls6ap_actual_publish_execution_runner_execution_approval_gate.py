from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ap_actual_publish_execution_runner_execution_approval_gate import (
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_TEMPLATE_READY,
    main,
)


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
        "approval_gate": tmp_path / "exchange/human_review/approval_gate.json",
        "ls6ao_result": tmp_path / "exchange/runtime/ls6ao_result.json",
        "ls6ao_lock": tmp_path / "exchange/locks/ls6ao_lock.json",
        "ls6ao_log": tmp_path / "exchange/logs/ls6ao_log.json",
        "output": tmp_path / "exchange/logs/out.json",
        "report": tmp_path / "reports/out.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AP",
            "execution_mode": "EXECUTION_APPROVAL_GATE_ONLY_NO_PUBLISH",
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
            },
            "required_previous_phase": {
                "ls6ao": {
                    "required_validation_status": "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH",
                    "required_post_id": 183,
                    "required_returned_post_status": "draft",
                    "required_ls6an_fix_a_status_normalization_validated": True,
                    "required_ls6an_no_execution_implementation_validated": True,
                    "required_runner_skeleton_static_safety_validated": True,
                    "required_source_artifacts_unchanged": True,
                    "required_runner_skeleton_reexecuted_by_this_phase": False,
                    "required_actual_publish_execution_runner_reexecuted_by_this_phase": False,
                    "required_actual_publish_execution_runner_network_call_enabled": False,
                    "required_actual_publish_execution_runner_credential_read_enabled": False,
                    "required_actual_publish_execution_runner_publish_enabled": False,
                    "required_actual_publish_execution_runner_execution_enabled": False,
                    "required_actual_publish_execution_runner_executed": False,
                    "required_manual_publish_executed": False,
                    "required_publish_execution_still_blocked": True,
                }
            },
            "approval_gate_policy": {
                "actual_publish_execution_runner_execution_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
                "requires_actual_publish_execution_runner_final_boundary": True,
                "requires_actual_publish_execution_runner_credential_preflight": True,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
            "must_remain_false_flags": {
                "wordpress_api_call_executed": False,
                "wordpress_get_executed": False,
                "wordpress_post_executed": False,
                "wordpress_put_executed": False,
                "wordpress_patch_executed": False,
                "wordpress_delete_executed": False,
                "wordpress_write_executed_by_this_phase": False,
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
                "actual_publish_execution_runner_execution_approval_gate_consumed": False,
                "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": False,
                "runner_skeleton_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_reexecuted_by_this_phase": False,
                "actual_publish_execution_runner_network_call_enabled": False,
                "actual_publish_execution_runner_credential_read_enabled": False,
                "actual_publish_execution_runner_publish_enabled": False,
                "actual_publish_execution_runner_execution_enabled": False,
                "actual_publish_execution_runner_executed": False,
                "manual_publish_executed": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "manual_publish_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "rerun_allowed": False,
                "ls6oc1_rerun_executed": False,
            },
            "next_phase": {
                "phase": "LS-6AQ",
                "execution_allowed_by_this_phase": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execution_runner_final_boundary": True,
                "requires_actual_publish_execution_runner_credential_preflight": True,
                "requires_actual_publish_execution_runner_final_command": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
        },
    )

    base_target = {
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "title": "2.5次元の誘惑",
        "asin": "B07X2G67B4",
        "expected_current_status": "draft",
    }

    base_approval = {
        "actual_publish_execution_runner_execution_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
        "required_actual_publish_execution_runner_execution_approval_gate_label": "APPROVED_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_GATE_ONLY",
        "gate_reason": "ready",
        "actual_publish_execution_runner_execution_approval_gate_consumed": False,
        "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": False,
        "actual_publish_execution_runner_execution_approved_for_later_phase": True,
        "actual_publish_execution_runner_execution_requires_later_final_boundary": True,
        "actual_publish_execution_runner_execution_requires_later_credential_preflight": True,
        "actual_publish_execution_runner_execution_requires_later_final_command": True,
        "actual_publish_execution_runner_execution_requires_separate_publish_execution_phase": True,
        "actual_publish_execution_runner_no_execution_implementation_validated": True,
        "ls6ao_validation_validated": True,
        "runner_skeleton_static_safety_validated": True,
        "source_artifacts_unchanged": True,
        "runner_skeleton_reexecuted_by_this_phase": False,
        "actual_publish_execution_runner_reexecuted_by_this_phase": False,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
    }

    base_current = {
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
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
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
    }

    template = {
        "phase": "LS-6AP",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE",
        "gate_status": "TEMPLATE_NOT_CONFIRMED",
        "target_post": dict(base_target),
        "approval_gate": dict(base_approval, actual_publish_execution_runner_execution_approval_gate_label="", gate_reason=""),
        "current_phase_execution": dict(base_current),
    }
    write_json(files["template"], template)

    gate = {
        "phase": "LS-6AP",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE",
        "gate_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION",
        "target_post": dict(base_target),
        "approval_gate": dict(base_approval),
        "current_phase_execution": dict(base_current),
    }
    write_json(files["approval_gate"], gate)

    ls6ao_result = {
        "status": "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH",
        "post_id": 183,
        "returned_post_status": "draft",
        "ls6an_fix_a_status_normalization_validated": True,
        "ls6an_no_execution_implementation_validated": True,
        "runner_skeleton_static_safety_validated": True,
        "source_artifacts_unchanged": True,
        "runner_skeleton_reexecuted_by_this_phase": False,
        "actual_publish_execution_runner_reexecuted_by_this_phase": False,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "publish_execution_still_blocked": True,
    }
    write_json(files["ls6ao_result"], ls6ao_result)
    write_json(files["ls6ao_lock"], {"post_id": 183, "status": "LOCK"})
    write_json(files["ls6ao_log"], dict(ls6ao_result))

    return files


def build_argv(files: dict[str, Path], allow_template: bool = False) -> list[str]:
    argv = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--template",
        str(files["template"]),
        "--approval-gate",
        str(files["approval_gate"]),
        "--ls6ao-validation-result",
        str(files["ls6ao_result"]),
        "--ls6ao-validation-lock",
        str(files["ls6ao_lock"]),
        "--ls6ao-validation-log",
        str(files["ls6ao_log"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]
    if allow_template:
        argv.append("--allow-template")
    return argv


def invoke(monkeypatch, files: dict[str, Path], allow_template: bool = False) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, allow_template=allow_template))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_01_allow_template_template_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, allow_template=True)
    assert out["status"] == STATUS_TEMPLATE_READY


def test_02_valid_approval_gate_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_READY


@pytest.mark.parametrize(
    "missing_key",
    [
        "policy",
        "template",
        "approval_gate",
        "ls6ao_result",
        "ls6ao_lock",
        "ls6ao_log",
    ],
)
def test_03_to_08_missing_required_files_not_ready(monkeypatch, tmp_path: Path, missing_key: str) -> None:
    files = make_inputs(tmp_path)
    files[missing_key].unlink()
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_09_post_id_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ao_result"], ("post_id",), 999)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_10_returned_post_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ao_result"], ("returned_post_status",), "publish")
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_11_ls6ao_validation_status_mismatch_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ao_result"], ("status",), "BROKEN")
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "key",
    [
        "ls6an_fix_a_status_normalization_validated",
        "ls6an_no_execution_implementation_validated",
        "runner_skeleton_static_safety_validated",
        "source_artifacts_unchanged",
    ],
)
def test_12_to_15_required_true_flags_false_not_ready(monkeypatch, tmp_path: Path, key: str) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ao_result"], (key,), False)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "key",
    [
        "runner_skeleton_reexecuted_by_this_phase",
        "actual_publish_execution_runner_reexecuted_by_this_phase",
        "actual_publish_execution_runner_network_call_enabled",
        "actual_publish_execution_runner_credential_read_enabled",
        "actual_publish_execution_runner_publish_enabled",
        "actual_publish_execution_runner_execution_enabled",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
    ],
)
def test_16_to_23_required_false_flags_true_not_ready(monkeypatch, tmp_path: Path, key: str) -> None:
    files = make_inputs(tmp_path)
    mutate(files["ls6ao_result"], (key,), True)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


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
        "rerun_allowed",
        "ls6oc1_rerun_executed",
    ],
)
def test_24_to_32_and_45_to_46_current_phase_true_not_ready(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    mutate(files["approval_gate"], ("current_phase_execution", field), True)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_33_wrong_approval_gate_label_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    mutate(
        files["approval_gate"],
        ("approval_gate", "actual_publish_execution_runner_execution_approval_gate_label"),
        "WRONG",
    )
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual_publish_execution_runner_execution_approval_gate_consumed", True),
        ("actual_publish_execution_runner_execution_approval_allowed_by_this_phase", True),
        ("actual_publish_execution_runner_execution_approved_for_later_phase", False),
        ("actual_publish_execution_runner_execution_requires_later_final_boundary", False),
        ("actual_publish_execution_runner_execution_requires_later_credential_preflight", False),
        ("actual_publish_execution_runner_execution_requires_later_final_command", False),
        ("actual_publish_execution_runner_execution_requires_separate_publish_execution_phase", False),
        ("actual_publish_execution_allowed_by_this_phase", True),
        ("actual_runner_execution_allowed_by_this_phase", True),
        ("manual_publish_allowed_by_this_phase", True),
        ("manual_publish_execution_allowed_by_this_phase", True),
    ],
)
def test_34_to_44_approval_gate_flag_violations_not_ready(
    monkeypatch, tmp_path: Path, field: str, value
) -> None:
    files = make_inputs(tmp_path)
    mutate(files["approval_gate"], ("approval_gate", field), value)
    out = invoke(monkeypatch, files)
    assert out["status"] == STATUS_NOT_READY


def test_47_result_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["output"].exists()


def test_48_report_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    assert files["report"].exists()


def test_49_result_keeps_ls6ao_validation_validated_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["ls6ao_validation_validated"] is True


def test_50_result_keeps_approval_gate_recorded_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_approval_gate_recorded"] is True


def test_51_result_keeps_approval_gate_consumed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_approval_gate_consumed"] is False


def test_52_result_keeps_execution_approval_allowed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_approval_allowed_by_this_phase"] is False


def test_53_result_keeps_approved_for_later_phase_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_approved_for_later_phase"] is True


def test_54_result_keeps_later_final_boundary_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_requires_later_final_boundary"] is True


def test_55_result_keeps_later_credential_preflight_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_requires_later_credential_preflight"] is True


def test_56_result_keeps_later_final_command_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_requires_later_final_command"] is True


def test_57_result_keeps_separate_publish_phase_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_requires_separate_publish_execution_phase"] is True


def test_58_result_keeps_runner_skeleton_reexecuted_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["runner_skeleton_reexecuted_by_this_phase"] is False


def test_59_result_keeps_actual_runner_reexecuted_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_reexecuted_by_this_phase"] is False


def test_60_result_keeps_network_call_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_network_call_enabled"] is False


def test_61_result_keeps_credential_read_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_credential_read_enabled"] is False


def test_62_result_keeps_publish_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_publish_enabled"] is False


def test_63_result_keeps_execution_enabled_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_execution_enabled"] is False


def test_64_result_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["actual_publish_execution_runner_executed"] is False


def test_65_result_keeps_wordpress_api_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["wordpress_api_call_executed"] is False


def test_66_result_keeps_credential_env_read_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["credential_env_read_executed"] is False


def test_67_result_keeps_publish_false(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["publish_executed"] is False


def test_68_result_requires_final_boundary_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_actual_publish_execution_runner_final_boundary"] is True


def test_69_result_requires_credential_preflight_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_actual_publish_execution_runner_credential_preflight"] is True


def test_70_result_requires_final_command_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["requires_actual_publish_execution_runner_final_command"] is True


def test_71_result_next_phase_ls6aq(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["next_phase"]["phase"] == "LS-6AQ"


def test_72_result_publish_execution_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["publish_execution_still_blocked"] is True
