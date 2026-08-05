from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-5", "document_type": "START_LS_NEW5_HUMAN_REVIEW_GATE_POLICY"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-5", "document_type": "START_LS_NEW5_HUMAN_REVIEW_CHECKLIST_SCHEMA"}


def _base_review_request() -> dict:
    return {
        "phase": "LS-NEW-5",
        "review_required": True,
        "review_completed": False,
        "human_approved": False,
        "approval_label_required_for_next": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_checklist() -> dict:
    return {
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_CHECKLIST_TEMPLATE",
        "human_decision": {"approval_label": ""},
    }


def _base_decision_template() -> dict:
    return {
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_TEMPLATE",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
    }


def _base_decision_record() -> dict:
    return {
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_RECORD",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "ready_for_ls_new_6": False,
    }


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-5",
        "status": "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION",
        "production_status": "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION",
        "ls_new4_validated": True,
        "review_request_created": True,
        "checklist_template_created": True,
        "decision_template_created": True,
        "decision_record_created": True,
        "wp_review_snapshot_created": True,
        "x_review_snapshot_created": True,
        "human_review_required": True,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "required_approval_label_for_next": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
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
        "recommended_next_action": "WAIT_FOR_HUMAN_REVIEW_DECISION",
        "recommended_next_phase_options": ["LS-NEW-5-DECISION", "LS-MON-2"],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-5",
        "status": "LSNEW5_HUMAN_REVIEW_GATE_LOCKED_WAITING_FOR_HUMAN_NO_EXECUTION",
        "locked": True,
        "human_review_required": True,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label_consumed": False,
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
    }


def _base_ls4_validation() -> dict:
    return {"validation_status": "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION"}


def _prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "review_request": tmp_path / "in/review_request.json",
        "checklist": tmp_path / "in/checklist.json",
        "decision_template": tmp_path / "in/decision_template.json",
        "decision_record": tmp_path / "in/decision_record.json",
        "wp_snapshot": tmp_path / "in/wp_snapshot.md",
        "x_snapshot": tmp_path / "in/x_snapshot.md",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls4_validation": tmp_path / "in/ls4_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["review_request"], _base_review_request())
    _write_json(p["checklist"], _base_checklist())
    _write_json(p["decision_template"], _base_decision_template())
    _write_json(p["decision_record"], _base_decision_record())
    p["wp_snapshot"].write_text("WordPress write executed: false\n", encoding="utf-8")
    p["x_snapshot"].write_text("X post executed: false\n#PR\nURL: https://example.invalid\n", encoding="utf-8")
    result = _base_result()
    _write_json(p["result"], result)
    _write_json(p["run_result"], dict(result))
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls4_validation"], _base_ls4_validation())
    return p


def _run_validate(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new5_human_review_gate.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--review-request",
        str(p["review_request"]),
        "--checklist-template",
        str(p["checklist"]),
        "--decision-template",
        str(p["decision_template"]),
        "--decision-record",
        str(p["decision_record"]),
        "--wp-review-snapshot",
        str(p["wp_snapshot"]),
        "--x-review-snapshot",
        str(p["x_snapshot"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new4-validation-result",
        str(p["ls4_validation"]),
        "--output",
        str(tmp_path / "out/validation.json"),
        "--report",
        str(tmp_path / "out/validation.md"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_success(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    res = _run_validate(tmp_path, p)
    assert res.returncode == 0, res.stderr

    v = _load(tmp_path / "out/validation.json")
    assert v["validation_status"] == "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION"
    assert v["run_status"] == "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION"
    assert v["production_status"] == "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION"
    assert v["errors"] == []


@pytest.mark.parametrize(
    "path_key",
    [
        "policy",
        "schema",
        "review_request",
        "checklist",
        "decision_template",
        "decision_record",
        "wp_snapshot",
        "x_snapshot",
        "result",
        "lock",
        "run_result",
        "ls4_validation",
    ],
)
def test_missing_input_file(tmp_path: Path, path_key: str) -> None:
    p = _prepare_inputs(tmp_path)
    p[path_key].unlink()

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert v["validation_status"] == "LSNEW5_HUMAN_REVIEW_GATE_NOT_VALIDATED"
    assert any("missing" in e for e in v["errors"])


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("review_request", "review_required", False, "review_required=false"),
        ("review_request", "review_completed", True, "review_completed=true"),
        ("review_request", "human_approved", True, "request human_approved=true"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new4_validated", False, "ls_new4_validated mismatch"),
        ("result", "execution_allowed", True, "execution_allowed=true"),
        ("result", "human_review_completed", True, "human_review_completed=true"),
        ("result", "human_approved", True, "human_approved=true"),
        ("result", "approval_label", "BAD", "approval_label must be empty"),
        ("result", "ready_for_ls_new_6", True, "ready_for_ls_new_6=true"),
        ("result", "auto_approval_executed", True, "auto_approval_executed=true"),
        ("result", "x_post_executed", True, "x_post_executed=true"),
        ("result", "wordpress_write_executed", True, "wordpress_write_executed=true"),
        ("result", "credential_env_read_executed", True, "credential_env_read_executed=true"),
        ("result", "candidate_selected", True, "candidate_selected=true"),
        ("result", "ls_next1_fill_updated", True, "ls_next1_fill_updated=true"),
        ("result", "post119_update_executed", True, "post119_update_executed=true"),
        ("result", "post183_update_executed", True, "post183_update_executed=true"),
        ("result", "rerun_allowed", True, "rerun_allowed=true"),
        ("result", "publish_rerun_allowed", True, "publish_rerun_allowed=true"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
        ("lock", "execution_allowed", True, "lock execution_allowed=true"),
    ],
)
def test_validate_detects_mismatch(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    data = _load(p[target])
    data[key] = value
    _write_json(p[target], data)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert error in v["errors"]


def test_result_run_result_mismatch(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    run = _load(p["run_result"])
    run["status"] = "BAD"
    _write_json(p["run_result"], run)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert "result and run_result mismatch" in v["errors"]


def test_ls4_validation_mismatch(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    bad = _load(p["ls4_validation"])
    bad["validation_status"] = "BAD"
    _write_json(p["ls4_validation"], bad)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert "ls-new4 validation mismatch" in v["errors"]


@pytest.mark.parametrize(
    "file_key,new_content,error",
    [
        ("wp_snapshot", "no marker\n", "snapshot missing WordPress no-write notice"),
        ("x_snapshot", "X post executed: false\nURL\n", "x snapshot missing #PR"),
        ("x_snapshot", "X post executed: false\n#PR\n", "x snapshot missing URL placeholder"),
        ("x_snapshot", "#PR\nURL\n", "snapshot missing X no-post notice"),
    ],
)
def test_snapshot_checks(tmp_path: Path, file_key: str, new_content: str, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    p[file_key].write_text(new_content, encoding="utf-8")

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert error in v["errors"]


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("decision_template", "human_review_completed", True, "decision template review completed true"),
        ("decision_template", "human_approved", True, "decision template approved true"),
        ("decision_template", "approval_label", "X", "decision template approval label not empty"),
        ("decision_record", "human_review_completed", True, "decision record review completed true"),
        ("decision_record", "human_approved", True, "decision record approved true"),
        ("decision_record", "approval_label", "X", "decision record approval label not empty"),
        ("decision_record", "approval_label_consumed", True, "decision record approval label consumed true"),
        ("decision_record", "ready_for_ls_new_6", True, "decision record ready_for_ls_new_6 true"),
    ],
)
def test_decision_template_record_constraints(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert error in v["errors"]


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("checklist", "document_type", "BAD", "checklist document_type mismatch"),
        ("decision_template", "document_type", "BAD", "decision template document_type mismatch"),
        ("decision_record", "document_type", "BAD", "decision record document_type mismatch"),
    ],
)
def test_document_type_mismatch(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare_inputs(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    v = _load(tmp_path / "out/validation.json")
    assert error in v["errors"]


def test_validation_report_written(tmp_path: Path) -> None:
    p = _prepare_inputs(tmp_path)
    d = _load(p["result"])
    d["status"] = "BAD"
    _write_json(p["result"], d)

    res = _run_validate(tmp_path, p)
    assert res.returncode != 0
    report = (tmp_path / "out/validation.md").read_text(encoding="utf-8")
    assert "LS-NEW-5 Human Review Gate Validation Report" in report
    assert "result status mismatch" in report


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new5_human_review_gate.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.get(",
        "httpx.get(",
        "boto3",
        "tweepy",
        "wp-json/wp/v2",
    ]
    assert all(p not in src for p in forbidden)
