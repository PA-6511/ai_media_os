from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "allowed_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_schema() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "allowed_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_decision_input() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_INPUT",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
        "ready_for_ls_new_6": False,
    }


def _base_decision_record() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_RESULT_RECORD",
        "status": "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "normalized_approval_label": "",
        "approval_label_consumed": False,
        "reviewer_notes": "",
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
        "warnings": [],
        "recommended_next_action": "WAIT_OR_REVIEW_REWORK",
    }


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_RESULT",
        "status": "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION",
        "execution_mode": "HUMAN_REVIEW_DECISION_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_HUMAN_REVIEW_DECISION_RECORDED",
        "ls_new5_validated": True,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "normalized_approval_label": "",
        "approval_label_consumed": False,
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
        "warnings": [],
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-6", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_LOCK",
        "status": "LSNEW5_DECISION_LOCKED_NO_EXECUTION",
        "locked": True,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls_new5_validation() -> dict:
    return {
        "validation_status": "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION",
    }


def _prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "decision_input": tmp_path / "in/decision_input.json",
        "decision_record": tmp_path / "in/decision_record.json",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls_new5_validation": tmp_path / "in/ls_new5_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["decision_input"], _base_decision_input())
    _write_json(p["decision_record"], _base_decision_record())
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls_new5_validation"], _base_ls_new5_validation())
    return p


def _run_validate(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new5_decision.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--decision-input",
        str(p["decision_input"]),
        "--decision-record",
        str(p["decision_record"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new5-validation-result",
        str(p["ls_new5_validation"]),
        "--output",
        str(tmp_path / "out/validation.json"),
        "--report",
        str(tmp_path / "out/validation.md"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_success_not_approved(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    res = _run_validate(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"
    assert out["run_status"] == "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION"


def test_validate_success_approved(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    rec = _load(p["decision_record"])
    rec["status"] = "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION"
    rec["human_review_completed"] = True
    rec["human_approved"] = True
    rec["approval_label"] = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    rec["normalized_approval_label"] = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    rec["ready_for_ls_new_6"] = True
    rec["recommended_next_action"] = "PROCEED_TO_LS_NEW_6_PREP_ONLY"
    _write_json(p["decision_record"], rec)

    result = _load(p["result"])
    result.update(
        {
            "status": rec["status"],
            "human_review_completed": True,
            "human_approved": True,
            "approval_label": rec["approval_label"],
            "normalized_approval_label": rec["normalized_approval_label"],
            "ready_for_ls_new_6": True,
            "recommended_next_action": "PROCEED_TO_LS_NEW_6_PREP_ONLY",
        }
    )
    _write_json(p["result"], result)
    _write_json(p["run_result"], result)

    res = _run_validate(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "path_key",
    [
        "policy",
        "schema",
        "decision_input",
        "decision_record",
        "result",
        "lock",
        "run_result",
        "ls_new5_validation",
    ],
)
def test_missing_required_input(path_key: str, tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    p[path_key].unlink()
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW5_DECISION_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("policy", "allowed_approval_label", "BAD", "policy allowed approval label mismatch"),
        ("schema", "allowed_approval_label", "BAD", "schema allowed approval label mismatch"),
        ("decision_input", "phase", "BAD", "decision input phase mismatch"),
        ("decision_input", "document_type", "BAD", "decision input document_type mismatch"),
        ("ls_new5_validation", "validation_status", "BAD", "ls-new5 validation mismatch"),
        ("decision_record", "document_type", "BAD", "decision record document_type mismatch"),
        ("decision_record", "phase", "BAD", "decision record phase mismatch"),
        ("decision_record", "execution_allowed", True, "execution_allowed=true"),
        ("decision_record", "approval_label_consumed", True, "approval_label_consumed=true"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
    ],
)
def test_validate_detects_field_mismatch(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key",
    [
        "auto_approval_executed",
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_validate_detects_forbidden_true_flags(tmp_path: Path, key: str) -> None:
    p = _prepare_inputs(tmp_path)
    result = _load(p["result"])
    result[key] = True
    _write_json(p["result"], result)
    _write_json(p["run_result"], result)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert f"{key}=true" in out["errors"]


@pytest.mark.parametrize(
    "k,v,error",
    [
        ("human_review_completed", "true", "human_review_completed must be boolean"),
        ("human_approved", "true", "human_approved must be boolean"),
        ("execution_allowed", "false", "execution_allowed must be boolean"),
        ("ready_for_ls_new_6", "false", "ready_for_ls_new_6 must be boolean"),
        ("approval_label_consumed", "false", "approval_label_consumed must be boolean"),
    ],
)
def test_validate_boolean_type_enforced(tmp_path: Path, k: str, v, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    rec = _load(p["decision_record"])
    rec[k] = v
    _write_json(p["decision_record"], rec)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_validate_detects_ready_without_conditions(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    rec = _load(p["decision_record"])
    rec["ready_for_ls_new_6"] = True
    _write_json(p["decision_record"], rec)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "ready_for_ls_new_6=true without valid approval conditions" in out["errors"]


def test_validate_detects_result_run_result_mismatch(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    rr = _load(p["run_result"])
    rr["status"] = "DIFF"
    _write_json(p["run_result"], rr)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "result and run_result mismatch" in out["errors"]


@pytest.mark.parametrize(
    "warning",
    [
        "invalid_boolean_type",
        "input_execution_allowed_true_forced_false",
    ],
)
def test_allowed_warnings_are_accepted(tmp_path: Path, warning: str) -> None:
    p = _prepare_inputs(tmp_path)
    rec = _load(p["decision_record"])
    rec["warnings"] = [warning]
    _write_json(p["decision_record"], rec)
    result = _load(p["result"])
    result["warnings"] = [warning]
    _write_json(p["result"], result)
    _write_json(p["run_result"], result)
    res = _run_validate(tmp_path, p)
    assert res.returncode == 0


def test_unexpected_warning_rejected(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    rec = _load(p["decision_record"])
    rec["warnings"] = ["bad_warning"]
    _write_json(p["decision_record"], rec)
    result = _load(p["result"])
    result["warnings"] = ["bad_warning"]
    _write_json(p["result"], result)
    _write_json(p["run_result"], result)
    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "unexpected warning: bad_warning" in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new5_decision.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.",
        "urllib.request",
        "wp-json",
        "/wp/v2/posts",
        "/etc/ai-media-os/credential.env",
        "http.client",
        "Authorization:",
    ]
    assert all(x not in src for x in forbidden)