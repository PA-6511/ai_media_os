from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "template": tmp_path / "exchange/human_review/template.json",
        "confirmation": tmp_path / "exchange/human_review/confirmation.json",
        "ls6ab_run": tmp_path / "exchange/logs/ls6ab_run.json",
        "ls6ab_val": tmp_path / "exchange/logs/ls6ab_val.json",
        "ls6ab_blocked": tmp_path / "exchange/runtime/ls6ab_blocked.json",
        "ls6ab_lock": tmp_path / "exchange/locks/ls6ab_lock.json",
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
        "output": tmp_path / "exchange/logs/output.json",
        "report": tmp_path / "reports/output.md",
    }

    write_json(files["policy"], {"phase": "LS-6AC", "execution_mode": "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_GATE_ONLY_NO_PUBLISH", "production_status": "NO_PUBLISH"})

    target = {
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "title": "2.5次元の誘惑",
        "asin": "B07X2G67B4",
        "expected_current_status": "draft",
    }

    current = {
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
    }

    upstream = {
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
    }

    write_json(
        files["template"],
        {
            "phase": "LS-6AC",
            "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_TEMPLATE",
            "confirmation_status": "TEMPLATE_NOT_CONFIRMED",
            "target_post": target,
            "actual_publish_execute_now_final_confirmation": {
                "actual_publish_execute_now_final_confirmation_label": "",
                "required_actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
                "confirmation_reason": "",
                "actual_publish_execute_now_final_confirmation_consumed": False,
                "explicit_execute_now_for_actual_publish_required": True,
                "explicit_execute_now_for_actual_publish_received": False,
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
            "upstream_consumption_state": upstream,
            "current_phase_execution": current,
        },
    )

    write_json(
        files["confirmation"],
        {
            "phase": "LS-6AC",
            "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION",
            "confirmation_status": "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION",
            "target_post": target,
            "actual_publish_execute_now_final_confirmation": {
                "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
                "required_actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
                "confirmation_reason": "ok",
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
                "requires_next_phase": "LS-6AD",
            },
            "upstream_consumption_state": upstream,
            "current_phase_execution": current,
        },
    )

    write_json(
        files["ls6ab_run"],
        {
            "status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "actual_publish_execution_runner_ready": True,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_runner_blocked": True,
            "explicit_execute_now_for_actual_publish_required": True,
            "explicit_execute_now_for_actual_publish_received": False,
            "explicit_execute_now_for_actual_publish_consumed": False,
            "publish_execution_still_blocked": True,
            "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
            "next_phase": {"phase": "LS-6AC"},
        },
    )
    write_json(files["ls6ab_val"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_lock"], {"status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})

    write_json(files["ls6aa_val"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_pf"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
    write_json(files["ls6aa_lock"], {"actual_publish_execution_final_preflight_consumed": False})

    write_json(files["ls6z_ready"], {"status": "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "final_explicit_publish_execution_command_consumed": False})
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


def build_argv(files: dict[str, Path], allow_template: bool = False) -> list[str]:
    argv = [
        "prog",
        "--policy", str(files["policy"]),
        "--template", str(files["template"]),
        "--confirmation", str(files["confirmation"]),
        "--ls6ab-run-result", str(files["ls6ab_run"]),
        "--ls6ab-validation-result", str(files["ls6ab_val"]),
        "--ls6ab-blocked-runner-result", str(files["ls6ab_blocked"]),
        "--ls6ab-blocked-runner-lock", str(files["ls6ab_lock"]),
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
    if allow_template:
        argv.append("--allow-template")
    return argv


def invoke(monkeypatch, files: dict[str, Path], allow_template: bool = False) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files, allow_template=allow_template))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def set_path(doc: dict, path: list[str], value) -> None:
    cur = doc
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = value


def assert_not_ready(monkeypatch, files: dict[str, Path], allow_template: bool = False) -> None:
    out = invoke(monkeypatch, files, allow_template=allow_template)
    assert out["status"] == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_NOT_READY"


def test_01_template_allow_template_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files, allow_template=True)
    assert out["status"] == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_TEMPLATE_READY_NO_PUBLISH"


def test_02_valid_confirmation_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH"


def test_03_confirmation_missing_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    files["confirmation"].unlink()
    assert_not_ready(monkeypatch, files)


def test_04_wrong_confirmation_label_not_ready(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    set_path(p, ["actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_label"], "WRONG")
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


@pytest.mark.parametrize(
    "path,value",
    [
        (["actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed"], True),
        (["actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_required"], False),
        (["actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_received"], False),
        (["actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_consumed"], True),
        (["actual_publish_execute_now_final_confirmation", "actual_publish_execution_runner_ready"], False),
        (["actual_publish_execute_now_final_confirmation", "actual_publish_execution_runner_executed"], True),
        (["actual_publish_execute_now_final_confirmation", "actual_publish_execution_runner_blocked"], False),
        (["actual_publish_execute_now_final_confirmation", "actual_publish_execution_allowed_by_this_phase"], True),
        (["actual_publish_execute_now_final_confirmation", "actual_runner_execution_allowed_by_this_phase"], True),
        (["actual_publish_execute_now_final_confirmation", "manual_publish_allowed_by_this_phase"], True),
        (["actual_publish_execute_now_final_confirmation", "manual_publish_execution_allowed_by_this_phase"], True),
        (["actual_publish_execute_now_final_confirmation", "manual_publish_executed"], True),
    ],
)
def test_05_to_16_confirmation_flags(monkeypatch, tmp_path: Path, path: list[str], value) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    set_path(p, path, value)
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


@pytest.mark.parametrize(
    "key",
    [
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
    ],
)
def test_17_to_23_upstream_consumption_true(monkeypatch, tmp_path: Path, key: str) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    p["upstream_consumption_state"][key] = True
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


@pytest.mark.parametrize(
    "key",
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
    ],
)
def test_24_to_32_current_phase_true(monkeypatch, tmp_path: Path, key: str) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    p["current_phase_execution"][key] = True
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


def test_33_post_id_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    p["target_post"]["post_id"] = 999
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


def test_34_expected_status_not_draft(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["confirmation"])
    p["target_post"]["expected_current_status"] = "publish"
    write_json(files["confirmation"], p)
    assert_not_ready(monkeypatch, files)


def test_35_ls6ab_validation_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_val"])
    p["status"] = "BROKEN"
    write_json(files["ls6ab_val"], p)
    assert_not_ready(monkeypatch, files)


def test_36_ls6ab_blocked_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_blocked"])
    p["status"] = "BROKEN"
    write_json(files["ls6ab_blocked"], p)
    assert_not_ready(monkeypatch, files)


def test_37_ls6ab_runner_executed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_run"])
    p["actual_publish_execution_runner_executed"] = True
    write_json(files["ls6ab_run"], p)
    assert_not_ready(monkeypatch, files)


def test_38_ls6ab_explicit_received_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_run"])
    p["explicit_execute_now_for_actual_publish_received"] = True
    write_json(files["ls6ab_run"], p)
    assert_not_ready(monkeypatch, files)


def test_39_ls6ab_explicit_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_run"])
    p["explicit_execute_now_for_actual_publish_consumed"] = True
    write_json(files["ls6ab_run"], p)
    assert_not_ready(monkeypatch, files)


def test_40_ls6ab_next_phase_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6ab_run"])
    p["next_phase"]["phase"] = "LS-6ZZ"
    write_json(files["ls6ab_run"], p)
    assert_not_ready(monkeypatch, files)


def test_41_ls6aa_validation_status_mismatch(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_val"])
    p["status"] = "BROKEN"
    write_json(files["ls6aa_val"], p)
    assert_not_ready(monkeypatch, files)


def test_42_ls6aa_preflight_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6aa_pf"])
    p["actual_publish_execution_final_preflight_consumed"] = True
    write_json(files["ls6aa_pf"], p)
    assert_not_ready(monkeypatch, files)


def test_43_ls6z_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6z_ready"])
    p["final_explicit_publish_execution_command_consumed"] = True
    write_json(files["ls6z_ready"], p)
    assert_not_ready(monkeypatch, files)


def test_44_ls6y_boundary_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6y_val"])
    p["actual_publish_runner_boundary_consumed"] = True
    write_json(files["ls6y_val"], p)
    assert_not_ready(monkeypatch, files)


def test_45_ls6x_gate_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6x_ready"])
    p["actual_publish_execution_gate_consumed"] = True
    write_json(files["ls6x_ready"], p)
    assert_not_ready(monkeypatch, files)


def test_46_ls6v_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6v_ready"])
    p["final_execution_command_consumed"] = True
    write_json(files["ls6v_ready"], p)
    assert_not_ready(monkeypatch, files)


def test_47_ls6t_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6t_ready"])
    p["execute_now_confirmation_consumed"] = True
    write_json(files["ls6t_ready"], p)
    assert_not_ready(monkeypatch, files)


def test_48_ls6r_consumed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6r_ready"])
    p["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], p)
    assert_not_ready(monkeypatch, files)


def test_49_ls6oc1_rerun_allowed_true(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    p = read_json(files["ls6oc1_lock"])
    p["rerun_allowed"] = True
    write_json(files["ls6oc1_lock"], p)
    assert_not_ready(monkeypatch, files)


def test_50_result_keeps_confirmation_consumed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execute_now_final_confirmation_consumed"] is False


def test_51_result_keeps_explicit_consumed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["explicit_execute_now_for_actual_publish_consumed"] is False


def test_52_result_keeps_runner_executed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execution_runner_executed"] is False


def test_53_result_keeps_publish_allowed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_publish_execution_allowed_by_this_phase"] is False


def test_54_result_keeps_runner_allowed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["actual_runner_execution_allowed_by_this_phase"] is False


def test_55_result_keeps_manual_executed_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["manual_publish_executed"] is False


def test_56_result_keeps_wordpress_api_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["wordpress_api_call_executed"] is False


def test_57_result_keeps_cread_false(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["credential_env_read_executed"] is False


def test_58_result_next_phase_ls6ad(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["next_phase"]["phase"] == "LS-6AD"


def test_59_result_requires_boundary_true(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["requires_actual_publish_execution_boundary"] is True


def test_60_result_requires_separate_phase_true(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["requires_separate_publish_execution_phase"] is True


def test_61_result_publish_still_blocked_true(monkeypatch, tmp_path: Path) -> None:
    out = invoke(monkeypatch, make_inputs(tmp_path))
    assert out["publish_execution_still_blocked"] is True
