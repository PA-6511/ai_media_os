from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_start_ls6ak_manual_publish_actual_publish_execution_runner_final_boundary import main


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def set_nested(doc: dict, key_path: list[str], value) -> None:
    cur = doc
    for key in key_path[:-1]:
        cur = cur[key]
    cur[key_path[-1]] = value


def mutate_json(path: Path, key_path: list[str], value) -> None:
    doc = read_json(path)
    set_nested(doc, key_path, value)
    write_json(path, doc)


def make_inputs(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6aj_ready": tmp_path / "exchange/logs/ls6aj_ready.json",
        "ls6aj_execute": tmp_path / "exchange/human_review/ls6aj_execute.json",
        "ls6ai_validation": tmp_path / "exchange/logs/ls6ai_validation.json",
        "ls6ai_wp": tmp_path / "exchange/runtime/ls6ai_wp.json",
        "ls6ai_final": tmp_path / "exchange/runtime/ls6ai_final.json",
        "ls6ai_lock": tmp_path / "exchange/locks/ls6ai_lock.json",
        "ls6ah_validation": tmp_path / "exchange/logs/ls6ah_validation.json",
        "ls6ah_boundary": tmp_path / "exchange/runtime/ls6ah_boundary.json",
        "ls6ah_lock": tmp_path / "exchange/locks/ls6ah_lock.json",
        "ls6ag_ready": tmp_path / "exchange/logs/ls6ag_ready.json",
        "ls6ag_command": tmp_path / "exchange/human_review/ls6ag_command.json",
        "ls6af_validation": tmp_path / "exchange/logs/ls6af_validation.json",
        "ls6af_runtime": tmp_path / "exchange/runtime/ls6af_runtime.json",
        "ls6af_lock": tmp_path / "exchange/locks/ls6af_lock.json",
        "ls6ae_validation": tmp_path / "exchange/logs/ls6ae_validation.json",
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
        "ls6aa_final": tmp_path / "exchange/runtime/ls6aa_final.json",
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
        "runtime_out": tmp_path / "exchange/runtime/ls6ak_runtime.json",
        "lock_out": tmp_path / "exchange/locks/ls6ak_lock.json",
        "output": tmp_path / "exchange/logs/ls6ak_run.json",
        "report": tmp_path / "reports/ls6ak_run.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6AK",
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
        },
    )

    write_json(
        files["ls6aj_ready"],
        {
            "status": "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_READY_NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "draft",
            "execute_now_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_runner_execute_now_label": "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
            "actual_publish_execution_runner_execute_now_consumed": False,
            "actual_publish_execution_runner_final_preflight_consumed": False,
            "actual_publish_execution_runner_boundary_consumed": False,
            "actual_publish_final_execution_command_consumed": False,
            "actual_publish_runner_final_gate_consumed": False,
            "actual_publish_final_preflight_consumed": False,
            "actual_publish_execution_boundary_consumed": False,
            "actual_publish_execute_now_final_confirmation_consumed": False,
            "explicit_execute_now_for_actual_publish_consumed": False,
            "actual_publish_execution_runner_executed": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "publish_execution_still_blocked": True,
            "requires_actual_publish_execution_runner_final_boundary": True,
            "next_phase": {"phase": "LS-6AK"},
        },
    )
    write_json(
        files["ls6aj_execute"],
        {
            "execute_now_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION",
            "actual_publish_execution_runner_execute_now_gate": {
                "actual_publish_execution_runner_execute_now_label": "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
                "actual_publish_execution_runner_execute_now_consumed": False,
            },
        },
    )

    write_json(
        files["ls6ai_validation"],
        {
            "status": "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
            "draft_verified": True,
            "returned_post_status": "draft",
        },
    )
    write_json(files["ls6ai_wp"], {"returned_post_status": "draft"})
    write_json(
        files["ls6ai_final"],
        {
            "actual_publish_execution_runner_final_preflight_ready": True,
            "actual_publish_execution_runner_final_preflight_consumed": False,
        },
    )
    write_json(files["ls6ai_lock"], {"actual_publish_execution_runner_final_preflight_consumed": False})

    write_json(files["ls6ah_validation"], {"status": "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ah_boundary"], {"actual_publish_execution_runner_boundary_ready": True, "actual_publish_execution_runner_boundary_consumed": False})
    write_json(files["ls6ah_lock"], {"actual_publish_execution_runner_boundary_consumed": False})

    write_json(files["ls6ag_ready"], {"status": "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "command_status": "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "actual_publish_final_execution_command_consumed": False})
    write_json(files["ls6ag_command"], {"actual_publish_final_execution_command": {"actual_publish_final_execution_command_consumed": False}})

    write_json(files["ls6af_validation"], {"status": "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6af_runtime"], {"actual_publish_runner_final_gate_ready": True, "actual_publish_runner_final_gate_consumed": False})
    write_json(files["ls6af_lock"], {"actual_publish_runner_final_gate_consumed": False})

    write_json(files["ls6ae_validation"], {"status": "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ae_final"], {"actual_publish_final_preflight_ready": True, "actual_publish_final_preflight_consumed": False})
    write_json(files["ls6ae_lock"], {"actual_publish_final_preflight_consumed": False})

    write_json(files["ls6ad_validation"], {"status": "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6ad_boundary"], {"actual_publish_execution_boundary_ready": True, "actual_publish_execution_boundary_consumed": False})
    write_json(files["ls6ad_lock"], {"actual_publish_execution_boundary_consumed": False})

    write_json(files["ls6ac_ready"], {"status": "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "actual_publish_execute_now_final_confirmation_consumed": False, "explicit_execute_now_for_actual_publish_required": True, "explicit_execute_now_for_actual_publish_received": True, "explicit_execute_now_for_actual_publish_consumed": False})
    write_json(files["ls6ac_confirmation"], {"actual_publish_execute_now_final_confirmation": {"actual_publish_execute_now_final_confirmation_consumed": False, "explicit_execute_now_for_actual_publish_consumed": False}})

    write_json(files["ls6ab_validation"], {"status": "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"})
    write_json(files["ls6ab_blocked"], {"actual_publish_execution_runner_ready": True, "actual_publish_execution_runner_executed": False, "actual_publish_execution_runner_blocked": True})
    write_json(files["ls6ab_lock"], {"actual_publish_execution_runner_executed": False})

    write_json(files["ls6aa_validation"], {"status": "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"})
    write_json(files["ls6aa_final"], {"actual_publish_execution_final_preflight_ready": True, "actual_publish_execution_final_preflight_consumed": False})
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
        "--ls6aj-ready-result", str(files["ls6aj_ready"]),
        "--ls6aj-execute-now-result", str(files["ls6aj_execute"]),
        "--ls6ai-validation-result", str(files["ls6ai_validation"]),
        "--ls6ai-wordpress-current-draft-status-result", str(files["ls6ai_wp"]),
        "--ls6ai-final-preflight-result", str(files["ls6ai_final"]),
        "--ls6ai-final-preflight-lock", str(files["ls6ai_lock"]),
        "--ls6ah-validation-result", str(files["ls6ah_validation"]),
        "--ls6ah-boundary-result", str(files["ls6ah_boundary"]),
        "--ls6ah-boundary-lock", str(files["ls6ah_lock"]),
        "--ls6ag-ready-result", str(files["ls6ag_ready"]),
        "--ls6ag-command-result", str(files["ls6ag_command"]),
        "--ls6af-validation-result", str(files["ls6af_validation"]),
        "--ls6af-runner-final-gate-result", str(files["ls6af_runtime"]),
        "--ls6af-runner-final-gate-lock", str(files["ls6af_lock"]),
        "--ls6ae-validation-result", str(files["ls6ae_validation"]),
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
        "--ls6aa-final-preflight-result", str(files["ls6aa_final"]),
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
        "--final-boundary-output", str(files["runtime_out"]),
        "--final-boundary-lock-output", str(files["lock_out"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
        "--record-actual-publish-execution-runner-final-boundary",
        "--require-separated-actual-publish-execution-runner-phase",
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
    argv.remove("--record-actual-publish-execution-runner-final-boundary")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_RECORD_FLAG"


def test_02_missing_separated_runner_phase_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separated-actual-publish-execution-runner-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_SEPARATED_RUNNER_PHASE_FLAG"


def test_03_missing_separate_execution_phase_flag(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    argv = build_argv(files)
    argv.remove("--require-separate-publish-execution-phase")
    out = invoke(monkeypatch, files, argv)
    assert out["status"] == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


MUTATIONS_04_24 = [
    ("ls6aj_ready", ["status"], "BROKEN"),
    ("ls6aj_ready", ["execute_now_status"], "BROKEN"),
    ("ls6aj_ready", ["actual_publish_execution_runner_execute_now_label"], "WRONG"),
    ("ls6aj_ready", ["actual_publish_execution_runner_execute_now_consumed"], True),
    ("ls6ai_final", ["actual_publish_execution_runner_final_preflight_consumed"], True),
    ("ls6ah_boundary", ["actual_publish_execution_runner_boundary_consumed"], True),
    ("ls6ag_ready", ["actual_publish_final_execution_command_consumed"], True),
    ("ls6af_runtime", ["actual_publish_runner_final_gate_consumed"], True),
    ("ls6ae_final", ["actual_publish_final_preflight_consumed"], True),
    ("ls6ad_boundary", ["actual_publish_execution_boundary_consumed"], True),
    ("ls6ac_ready", ["actual_publish_execute_now_final_confirmation_consumed"], True),
    ("ls6ac_ready", ["explicit_execute_now_for_actual_publish_consumed"], True),
    ("ls6ab_blocked", ["actual_publish_execution_runner_executed"], True),
    ("ls6aa_final", ["actual_publish_execution_final_preflight_consumed"], True),
    ("ls6z_ready", ["final_explicit_publish_execution_command_consumed"], True),
    ("ls6y_validation", ["actual_publish_runner_boundary_consumed"], True),
    ("ls6x_ready", ["actual_publish_execution_gate_consumed"], True),
    ("ls6v_ready", ["final_execution_command_consumed"], True),
    ("ls6t_ready", ["execute_now_confirmation_consumed"], True),
    ("ls6r_ready", ["approval_label_consumed"], True),
    ("ls6oc1_lock", ["rerun_allowed"], True),
]


@pytest.mark.parametrize("file_key,key_path,value", MUTATIONS_04_24)
def test_04_to_24_not_ready_cases(monkeypatch, tmp_path: Path, file_key: str, key_path: list[str], value) -> None:
    files = make_inputs(tmp_path)
    mutate_json(files[file_key], key_path, value)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY"


def test_25_valid_final_boundary_passed(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out["status"] == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH"


def test_26_no_wordpress_or_credential_execution(monkeypatch, tmp_path: Path) -> None:
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
        "actual_publish_execution_runner_final_boundary_consumed",
        "actual_publish_execution_runner_execute_now_consumed",
        "actual_publish_execution_runner_final_preflight_consumed",
        "actual_publish_execution_runner_boundary_consumed",
        "actual_publish_final_execution_command_consumed",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
    ],
)
def test_27_to_36_output_keeps_flags_false(monkeypatch, tmp_path: Path, field: str) -> None:
    files = make_inputs(tmp_path)
    out = invoke(monkeypatch, files)
    assert out[field] is False


def test_37_final_boundary_lock_generated(monkeypatch, tmp_path: Path) -> None:
    files = make_inputs(tmp_path)
    invoke(monkeypatch, files)
    lock = read_json(files["lock_out"])
    assert lock["status"] == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_LOCKED_NO_PUBLISH"
    assert lock["locked"] is True
