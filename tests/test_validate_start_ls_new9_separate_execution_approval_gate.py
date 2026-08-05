from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-9"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-9"}


def _base_request() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST_CREATED_NO_EXECUTION",
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_GATE_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new8_validated": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "required_approval_label": "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
        "approval_label": "",
        "approval_label_consumed": False,
        "request_scope": [
            "Approve moving to the next no-execution execution-prep phase only",
            "Do not approve WordPress API call in LS-NEW-9",
            "Do not approve credential.env read in LS-NEW-9",
            "Do not approve WordPress draft creation in LS-NEW-9",
        ],
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
    }


def _base_checklist() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_CHECKLIST_TEMPLATE",
        "candidate_review": {
            "content_item_id_checked": False,
            "title_checked": False,
            "volume_checked": False,
            "author_checked": False,
            "publisher_checked": False,
            "release_date_checked": False,
            "post_status_target_checked": False,
        },
        "preflight_review": {
            "ls_new8_validated_checked": False,
            "freeze_boundary_checked": False,
            "rollback_boundary_checked": False,
            "abort_conditions_checked": False,
            "handoff_ready_checked": False,
            "abort_triggered_false_checked": False,
        },
        "safety_review": {
            "runner_execution_not_allowed_checked": False,
            "final_execution_command_not_created_checked": False,
            "wordpress_api_not_executed_checked": False,
            "wordpress_draft_not_created_checked": False,
            "credential_env_not_read_checked": False,
            "credential_existence_not_checked": False,
            "target_post_id_not_allocated_checked": False,
            "post119_not_updated_checked": False,
            "post183_not_updated_checked": False,
            "secret_not_output_checked": False,
        },
        "human_decision": {
            "human_approval_completed": False,
            "human_approved_for_execution": False,
            "approval_label": "",
            "reviewer_notes": "",
        },
    }


def _base_decision_template() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_TEMPLATE",
        "instructions": "Human reviewer must fill this manually. AI must not auto-approve.",
        "allowed_approval_label": "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
    }


def _base_decision_record() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORD",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "reviewer_notes": "",
        "ready_for_ls_new_9_decision": True,
        "ready_for_ls_new_10": False,
        "execution_allowed": False,
    }


def _base_scope_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-9 Separate Execution Approval Gate Scope Summary",
            "",
            "- Phase: LS-NEW-9",
            "- Status: WAITING_FOR_SEPARATE_EXECUTION_APPROVAL",
            "- Human approval required: true",
            "- Human approval completed: false",
            "- Human approved for execution: false",
            "- Required approval label: APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
            "- Approval label consumed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Credential existence check executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "",
            "この承認ゲートは、次段の実行準備フェーズへ進むための判断ゲートであり、",
            "LS-NEW-9 自体では WordPress API / credential.env / draft creation を許可しない。",
            "",
        ]
    )


def _base_safety() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_APPROVAL_GATE_SAFETY_SUMMARY",
        "status": "LSNEW9_APPROVAL_GATE_SAFETY_SUMMARY_READY_NO_EXECUTION",
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
        "approval_label_consumed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
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
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
    }


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_RESULT",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION",
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_GATE_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new8_validated": True,
        "approval_request_created": True,
        "approval_checklist_template_created": True,
        "approval_decision_template_created": True,
        "approval_decision_record_created": True,
        "approval_scope_summary_created": True,
        "approval_gate_safety_summary_created": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "required_approval_label": "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
        "approval_label": "",
        "approval_label_consumed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
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
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_9_decision": True,
        "ready_for_ls_new_10": False,
        "recommended_next_action": "WAIT_FOR_SEPARATE_EXECUTION_APPROVAL_DECISION",
        "recommended_next_phase_options": ["LS-NEW-9-DECISION", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCK",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION",
        "locked": True,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label_consumed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "execution_allowed": False,
        "target_post_id_allocated": False,
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
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls8_validation() -> dict:
    return {"validation_status": "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "request": tmp_path / "in/request.json",
        "checklist": tmp_path / "in/checklist.template.json",
        "decision_template": tmp_path / "in/decision.template.json",
        "decision_record": tmp_path / "in/decision.json",
        "scope_summary": tmp_path / "in/scope.md",
        "safety": tmp_path / "in/safety.json",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls8_validation": tmp_path / "in/ls8_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["request"], _base_request())
    _write_json(p["checklist"], _base_checklist())
    _write_json(p["decision_template"], _base_decision_template())
    _write_json(p["decision_record"], _base_decision_record())
    p["scope_summary"].parent.mkdir(parents=True, exist_ok=True)
    p["scope_summary"].write_text(_base_scope_summary(), encoding="utf-8")
    _write_json(p["safety"], _base_safety())
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls8_validation"], _base_ls8_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new9_separate_execution_approval_gate.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--request",
        str(p["request"]),
        "--checklist-template",
        str(p["checklist"]),
        "--decision-template",
        str(p["decision_template"]),
        "--decision-record",
        str(p["decision_record"]),
        "--scope-summary",
        str(p["scope_summary"]),
        "--safety-summary",
        str(p["safety"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new8-validation-result",
        str(p["ls8_validation"]),
        "--output",
        str(tmp_path / "out/validation.json"),
        "--report",
        str(tmp_path / "out/validation.md"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_success(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "path_key",
    [
        "policy",
        "schema",
        "request",
        "checklist",
        "decision_template",
        "decision_record",
        "scope_summary",
        "safety",
        "result",
        "lock",
        "run_result",
        "ls8_validation",
    ],
)
def test_missing_files(path_key: str, tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p[path_key].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls8_validation", "validation_status", "BAD", "ls-new8 validation status mismatch"),
        ("request", "phase", "BAD", "request phase mismatch"),
        ("request", "document_type", "BAD", "request document_type mismatch"),
        ("request", "status", "BAD", "request status mismatch"),
        ("request", "execution_mode", "BAD", "request execution_mode mismatch"),
        ("request", "production_status", "BAD", "request production_status mismatch"),
        ("request", "ls_new8_validated", False, "request ls_new8_validated mismatch"),
        ("request", "target_post_id", 1, "request target_post_id must be null"),
        ("request", "human_approval_required", False, "request human_approval_required mismatch"),
        ("request", "human_approval_completed", True, "request human_approval_completed=true"),
        ("request", "human_approved_for_execution", True, "request human_approved_for_execution=true"),
        ("request", "required_approval_label", "BAD", "request required_approval_label mismatch"),
        ("request", "approval_label", "X", "request approval_label must be empty"),
        ("request", "approval_label_consumed", True, "request approval_label_consumed=true"),
        ("request", "execution_allowed", True, "request execution_allowed=true"),
        ("request", "runner_execution_allowed", True, "request runner_execution_allowed=true"),
        ("request", "final_execution_command_created", True, "request final_execution_command_created=true"),
        ("checklist", "phase", "BAD", "checklist phase mismatch"),
        ("checklist", "document_type", "BAD", "checklist document_type mismatch"),
        ("decision_template", "phase", "BAD", "decision template phase mismatch"),
        ("decision_template", "document_type", "BAD", "decision template document_type mismatch"),
        ("decision_template", "allowed_approval_label", "BAD", "decision template label mismatch"),
        ("decision_template", "human_approval_completed", True, "decision template human_approval_completed=true"),
        ("decision_template", "human_approved_for_execution", True, "decision template human_approved_for_execution=true"),
        ("decision_template", "approval_label", "X", "decision template approval_label must be empty"),
        ("decision_template", "execution_allowed", True, "decision template execution_allowed=true"),
        ("decision_record", "phase", "BAD", "decision record phase mismatch"),
        ("decision_record", "document_type", "BAD", "decision record document_type mismatch"),
        ("decision_record", "status", "BAD", "decision record status mismatch"),
        ("decision_record", "human_approval_completed", True, "decision record human_approval_completed=true"),
        ("decision_record", "human_approved_for_execution", True, "decision record human_approved_for_execution=true"),
        ("decision_record", "approval_label", "X", "decision record approval_label must be empty"),
        ("decision_record", "approval_label_consumed", True, "decision record approval_label_consumed=true"),
        ("decision_record", "ready_for_ls_new_9_decision", False, "decision record ready_for_ls_new_9_decision=false"),
        ("decision_record", "ready_for_ls_new_10", True, "decision record ready_for_ls_new_10=true"),
        ("decision_record", "execution_allowed", True, "decision record execution_allowed=true"),
        ("safety", "phase", "BAD", "safety summary phase mismatch"),
        ("safety", "document_type", "BAD", "safety summary document_type mismatch"),
        ("safety", "status", "BAD", "safety summary status mismatch"),
        ("safety", "auto_approval_executed", True, "auto_approval_executed=true"),
        ("safety", "ai_self_approval_executed", True, "ai_self_approval_executed=true"),
        ("safety", "approval_label_autofill_executed", True, "approval_label_autofill_executed=true"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new8_validated", False, "result ls_new8_validated mismatch"),
        ("result", "approval_request_created", False, "result approval_request_created mismatch"),
        ("result", "approval_checklist_template_created", False, "result approval_checklist_template_created mismatch"),
        ("result", "approval_decision_template_created", False, "result approval_decision_template_created mismatch"),
        ("result", "approval_decision_record_created", False, "result approval_decision_record_created mismatch"),
        ("result", "approval_scope_summary_created", False, "result approval_scope_summary_created mismatch"),
        ("result", "approval_gate_safety_summary_created", False, "result approval_gate_safety_summary_created mismatch"),
        ("result", "target_post_id", 1, "result target_post_id must be null"),
        ("result", "human_approval_required", False, "result human_approval_required mismatch"),
        ("result", "human_approval_completed", True, "result human_approval_completed=true"),
        ("result", "human_approved_for_execution", True, "result human_approved_for_execution=true"),
        ("result", "required_approval_label", "BAD", "result required_approval_label mismatch"),
        ("result", "approval_label", "X", "result approval_label must be empty"),
        ("result", "ready_for_ls_new_9_decision", False, "result ready_for_ls_new_9_decision=false"),
        ("result", "ready_for_ls_new_10", True, "result ready_for_ls_new_10=true"),
        ("result", "recommended_next_action", "BAD", "result recommended_next_action mismatch"),
        ("lock", "phase", "BAD", "lock phase mismatch"),
        ("lock", "document_type", "BAD", "lock document_type mismatch"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
        ("lock", "human_approval_required", False, "lock human_approval_required mismatch"),
        ("lock", "human_approval_completed", True, "lock human_approval_completed=true"),
        ("lock", "human_approved_for_execution", True, "lock human_approved_for_execution=true"),
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


@pytest.mark.parametrize(
    "key,error",
    [
        ("human_approval_completed", "result human_approval_completed=true"),
        ("human_approved_for_execution", "result human_approved_for_execution=true"),
        ("approval_label_consumed", "result approval_label_consumed=true"),
        ("runner_execution_allowed", "result runner_execution_allowed=true"),
        ("final_execution_command_created", "result final_execution_command_created=true"),
        ("wordpress_api_call_executed", "result wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "result wordpress_write_executed=true"),
        ("wordpress_draft_created", "result wordpress_draft_created=true"),
        ("wordpress_publish_executed", "result wordpress_publish_executed=true"),
        ("x_post_executed", "result x_post_executed=true"),
        ("external_fetch_executed", "result external_fetch_executed=true"),
        ("http_get_executed", "result http_get_executed=true"),
        ("credential_env_read_executed", "result credential_env_read_executed=true"),
        ("credential_existence_check_executed", "result credential_existence_check_executed=true"),
        ("credential_secret_output", "result credential_secret_output=true"),
        ("target_post_id_allocated", "result target_post_id_allocated=true"),
        ("post119_update_executed", "result post119_update_executed=true"),
        ("post183_update_executed", "result post183_update_executed=true"),
        ("execution_allowed", "result execution_allowed=true"),
    ],
)
def test_result_forbidden_true_detection(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    r = _load(p["result"])
    r[key] = True
    _write_json(p["result"], r)
    _write_json(p["run_result"], r)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
        ("approval_label_consumed", "lock approval_label_consumed=true"),
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("execution_allowed", "lock execution_allowed=true"),
        ("target_post_id_allocated", "lock target_post_id_allocated=true"),
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
        ("candidate_selected", "lock candidate_selected=true"),
        ("ls_next1_fill_updated", "lock ls_next1_fill_updated=true"),
        ("rerun_allowed", "lock rerun_allowed=true"),
        ("publish_rerun_allowed", "lock publish_rerun_allowed=true"),
    ],
)
def test_lock_forbidden_true_detection(tmp_path: Path, key: str, error: str) -> None:
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
    r = _load(p["run_result"])
    r["status"] = "DIFF"
    _write_json(p["run_result"], r)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "result and run_result mismatch" in out["errors"]


@pytest.mark.parametrize(
    "text,error",
    [
        ("bad", "scope summary header mismatch"),
        (
            "# LS-NEW-9 Separate Execution Approval Gate Scope Summary\n",
            "scope summary missing line: - Phase: LS-NEW-9",
        ),
    ],
)
def test_scope_summary_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["scope_summary"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_decision_template_instruction_check(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_template"])
    d["instructions"] = "bad"
    _write_json(p["decision_template"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "decision template instructions mismatch" in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
        ("content_item_id_checked", "checklist candidate_review content_item_id_checked=true"),
        ("title_checked", "checklist candidate_review title_checked=true"),
        ("volume_checked", "checklist candidate_review volume_checked=true"),
        ("author_checked", "checklist candidate_review author_checked=true"),
        ("publisher_checked", "checklist candidate_review publisher_checked=true"),
        ("release_date_checked", "checklist candidate_review release_date_checked=true"),
        ("post_status_target_checked", "checklist candidate_review post_status_target_checked=true"),
    ],
)
def test_checklist_candidate_review_false(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    c = _load(p["checklist"])
    c["candidate_review"][key] = True
    _write_json(p["checklist"], c)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new9_separate_execution_approval_gate.py").read_text(encoding="utf-8")
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
