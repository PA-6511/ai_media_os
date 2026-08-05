from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-9-DECISION"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-9-DECISION"}


def _base_input() -> dict:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_INPUT",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "ready_for_ls_new_10": False,
    }


def _base_record() -> dict:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_RESULT_RECORD",
        "status": "LSNEW9_DECISION_NOT_APPROVED_NO_EXECUTION",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "normalized_approval_label": "",
        "approval_label_consumed": False,
        "reviewer_notes": "",
        "ready_for_ls_new_10": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "warnings": [],
        "recommended_next_action": "WAIT_OR_REVIEW_REWORK",
    }


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_RESULT",
        "status": "LSNEW9_DECISION_NOT_APPROVED_NO_EXECUTION",
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_DECISION_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORDED",
        "ls_new9_validated": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "normalized_approval_label": "",
        "approval_label_consumed": False,
        "ready_for_ls_new_10": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "warnings": [],
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-10", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_LOCK",
        "status": "LSNEW9_DECISION_LOCKED_NO_EXECUTION",
        "locked": True,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "target_post_id_allocated": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls9_validation() -> dict:
    return {"validation_status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "input": tmp_path / "in/input.json",
        "record": tmp_path / "in/record.json",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls9_validation": tmp_path / "in/ls9_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["input"], _base_input())
    _write_json(p["record"], _base_record())
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls9_validation"], _base_ls9_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new9_decision.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--decision-input",
        str(p["input"]),
        "--decision-record",
        str(p["record"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new9-validation-result",
        str(p["ls9_validation"]),
        "--output",
        str(tmp_path / "out/validation.json"),
        "--report",
        str(tmp_path / "out/validation.md"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_success_not_approved(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"


def test_validate_success_approved(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    approved_input = _load(p["input"])
    approved_input["human_approval_completed"] = True
    approved_input["human_approved_for_execution"] = True
    approved_input["approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    _write_json(p["input"], approved_input)

    approved_record = _load(p["record"])
    approved_record["status"] = "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"
    approved_record["human_approval_completed"] = True
    approved_record["human_approved_for_execution"] = True
    approved_record["approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    approved_record["normalized_approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    approved_record["ready_for_ls_new_10"] = True
    approved_record["recommended_next_action"] = "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY"
    _write_json(p["record"], approved_record)

    approved_result = _load(p["result"])
    approved_result["status"] = "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"
    approved_result["human_approval_completed"] = True
    approved_result["human_approved_for_execution"] = True
    approved_result["approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    approved_result["normalized_approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    approved_result["ready_for_ls_new_10"] = True
    approved_result["recommended_next_action"] = "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY"
    _write_json(p["result"], approved_result)
    _write_json(p["run_result"], approved_result)

    res = _run(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize("path_key", ["policy", "schema", "input", "record", "result", "lock", "run_result", "ls9_validation"])
def test_missing_files(path_key: str, tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p[path_key].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW9_DECISION_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls9_validation", "validation_status", "BAD", "ls-new9 validation status mismatch"),
        ("input", "phase", "BAD", "decision-input phase mismatch"),
        ("input", "document_type", "BAD", "decision-input document_type mismatch"),
        ("record", "phase", "BAD", "decision record phase mismatch"),
        ("record", "document_type", "BAD", "decision record document_type mismatch"),
        ("record", "status", "BAD", "decision record status mismatch"),
        ("record", "ready_for_ls_new_10", True, "decision record ready_for_ls_new_10 mismatch"),
        ("record", "execution_allowed", True, "decision record execution_allowed=true"),
        ("record", "runner_execution_allowed", True, "decision record runner_execution_allowed=true"),
        ("record", "final_execution_command_created", True, "decision record final_execution_command_created=true"),
        ("record", "approval_label_consumed", True, "decision record approval_label_consumed=true"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new9_validated", False, "result ls_new9_validated mismatch"),
        ("result", "execution_allowed", True, "result execution_allowed=true"),
        ("result", "runner_execution_allowed", True, "result runner_execution_allowed=true"),
        ("result", "final_execution_command_created", True, "result final_execution_command_created=true"),
        ("result", "approval_label_consumed", True, "result approval_label_consumed=true"),
        ("result", "auto_approval_executed", True, "auto_approval_executed=true"),
        ("result", "ai_self_approval_executed", True, "ai_self_approval_executed=true"),
        ("result", "approval_label_autofill_executed", True, "approval_label_autofill_executed=true"),
        ("result", "wordpress_draft_created", True, "wordpress_draft_created=true"),
        ("result", "x_post_executed", True, "x_post_executed=true"),
        ("result", "credential_env_read_executed", True, "credential_env_read_executed=true"),
        ("result", "credential_existence_check_executed", True, "credential_existence_check_executed=true"),
        ("result", "credential_secret_output", True, "credential_secret_output=true"),
        ("result", "target_post_id_allocated", True, "target_post_id_allocated=true"),
        ("result", "target_post_id", 1, "target_post_id must be null"),
        ("lock", "phase", "BAD", "lock phase mismatch"),
        ("lock", "document_type", "BAD", "lock document_type mismatch"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
    ],
)
def test_structure_constraints(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    if target == "result":
        _write_json(p["run_result"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_detect_ready_true_without_approval_conditions(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    r = _load(p["result"])
    r["ready_for_ls_new_10"] = True
    _write_json(p["result"], r)
    _write_json(p["run_result"], r)
    rec = _load(p["record"])
    rec["ready_for_ls_new_10"] = True
    _write_json(p["record"], rec)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert any("ready_for_ls_new_10 mismatch" in e for e in out["errors"])


@pytest.mark.parametrize(
    "key,error",
    [
        ("approval_label_consumed", "lock approval_label_consumed=true"),
        ("execution_allowed", "lock execution_allowed=true"),
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("auto_approval_executed", "lock auto_approval_executed=true"),
        ("ai_self_approval_executed", "lock ai_self_approval_executed=true"),
        ("approval_label_autofill_executed", "lock approval_label_autofill_executed=true"),
        ("wordpress_api_call_executed", "lock wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "lock wordpress_write_executed=true"),
        ("wordpress_draft_created", "lock wordpress_draft_created=true"),
        ("wordpress_publish_executed", "lock wordpress_publish_executed=true"),
        ("x_api_call_executed", "lock x_api_call_executed=true"),
        ("x_post_executed", "lock x_post_executed=true"),
        ("external_fetch_executed", "lock external_fetch_executed=true"),
        ("http_get_executed", "lock http_get_executed=true"),
        ("credential_env_read_executed", "lock credential_env_read_executed=true"),
        ("credential_existence_check_executed", "lock credential_existence_check_executed=true"),
        ("target_post_id_allocated", "lock target_post_id_allocated=true"),
        ("candidate_selected", "lock candidate_selected=true"),
        ("ls_next1_fill_updated", "lock ls_next1_fill_updated=true"),
        ("rerun_allowed", "lock rerun_allowed=true"),
        ("publish_rerun_allowed", "lock publish_rerun_allowed=true"),
    ],
)
def test_lock_true_detections(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    lock = _load(p["lock"])
    lock[key] = True
    _write_json(p["lock"], lock)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_result_run_result_mismatch(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    rr = _load(p["run_result"])
    rr["status"] = "DIFF"
    _write_json(p["run_result"], rr)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "result and run_result mismatch" in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new9_decision.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.",
        "urllib.request",
        "/etc/ai-media-os/credential.env",
        "Authorization:",
        "http.client",
        "base64",
        "b64encode",
    ]
    assert all(x not in src for x in forbidden)
