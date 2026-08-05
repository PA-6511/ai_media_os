from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

REQ_LABEL = "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict[str, Any]:
    return {"phase": "LS-NEW-14"}


def _base_schema() -> dict[str, Any]:
    return {"phase": "LS-NEW-14"}


def _fixed_false() -> dict[str, Any]:
    return {
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
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
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ready_for_ls_new_15": False,
    }


def _base_manifest() -> dict[str, Any]:
    d = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_MANIFEST",
        "status": "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION",
        "execution_mode": "SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new13_validated": True,
        "ls_new13_command_prep_ready": True,
        "human_approval_required": True,
        "required_approval_label": REQ_LABEL,
        "approval_label": "",
        "approval_gate_manifest_created": True,
        "approval_request_created": True,
        "approval_checklist_created": True,
        "approval_decision_input_template_created": True,
        "initial_decision_record_created": True,
        "approval_scope_summary_created": True,
        "approval_safety_summary_created": True,
        "decision_handoff_created": True,
        "approval_gate_summary_created": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "ready_for_ls_new_14_decision": True,
        "recommended_next_action": "WAIT_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION",
        "recommended_next_phase_options": ["LS-NEW-14-DECISION", "LS-MON-2"],
        "errors": [],
    }
    d.update(_fixed_false())
    return d


def _base_approval_request() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST_READY",
        "human_approval_required": True,
        "approval_scope": "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY",
        "required_approval_label": REQ_LABEL,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "execution_allowed": False,
    }


def _base_checklist() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST_READY",
        "check_items": {
            "ls_new13_validated": True,
            "blocked_command_template_exists": True,
            "blocked_command_template_not_executable": True,
            "payload_map_confirmed": True,
            "payload_status_is_draft": True,
            "one_shot_execution_target_is_one": True,
            "one_shot_execution_actual_count_is_zero": True,
            "target_post_id_is_null": True,
            "target_post_id_allocated_false": True,
            "post119_update_forbidden": True,
            "post183_update_forbidden": True,
            "wordpress_draft_not_created": True,
            "wordpress_publish_not_executed": True,
            "separate_decision_required": True,
            "human_approval_required": True,
            "auto_approval_forbidden": True,
            "ai_self_approval_forbidden": True,
            "approval_label_autofill_forbidden": True,
            "approval_label_consumption_forbidden_in_gate": True,
        },
        "all_required_checks_passed": True,
        "execution_allowed": False,
    }


def _base_decision_input_template() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14-DECISION",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION_INPUT",
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label": "",
        "reviewer_notes": "",
        "approval_scope_confirmed": False,
        "one_shot_only_confirmed": False,
        "target_post_id_null_confirmed": False,
        "post119_post183_forbidden_confirmed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "wordpress_draft_creation_allowed_for_later_phase": False,
        "ready_for_ls_new_15": False,
    }


def _base_initial_decision_record() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_RECORD",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_NOT_APPROVED",
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "ready_for_ls_new_15": False,
        "execution_allowed": False,
    }


def _base_scope_summary() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_SUMMARY",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_READY",
        "approval_scope": "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY",
        "allowed_future_execution_count_after_later_decision": 1,
        "current_execution_count": 0,
        "publish_scope_allowed": False,
        "update_existing_post_allowed": False,
        "target_post_id_allocation_allowed": False,
        "post119_forbidden": True,
        "post183_forbidden": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "execution_allowed": False,
    }


def _base_safety_summary() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_SUMMARY",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_READY_NO_EXECUTION",
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "credential_env_read_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_decision_handoff() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DECISION_HANDOFF",
        "status": "LSNEW14_DECISION_HANDOFF_READY",
        "next_phase": "LS-NEW-14-DECISION",
        "next_phase_name": "Separate Draft Creation Execution Approval Decision",
        "handoff_ready": True,
        "ready_for_ls_new_14_decision": True,
        "ready_for_ls_new_15": False,
        "required_approval_label": REQ_LABEL,
        "notes": ["n"],
    }


def _base_result() -> dict[str, Any]:
    d = _base_manifest().copy()
    d["document_type"] = "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_RESULT"
    return d


def _base_lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCK",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION",
        "locked": True,
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "credential_env_read_executed": False,
        "target_post_id_allocated": False,
        "ready_for_ls_new_15": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls13_validation() -> dict[str, Any]:
    return {"validation_status": "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"}


def _base_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary",
            "- Human approval required: true",
            "- Human approval completed: false",
            "- Human approved for draft creation: false",
            "- Execution allowed: false",
            "- Actual executable command created: false",
            "- Shell execution performed: false",
            "- Ready for LS-NEW-14-DECISION: true",
            "",
        ]
    )


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "approval_request": tmp_path / "in/approval_request.json",
        "approval_checklist": tmp_path / "in/approval_checklist.json",
        "decision_input_template": tmp_path / "in/decision_input_template.json",
        "initial_decision_record": tmp_path / "in/initial_decision_record.json",
        "approval_scope_summary": tmp_path / "in/approval_scope_summary.json",
        "approval_safety_summary": tmp_path / "in/approval_safety_summary.json",
        "decision_handoff": tmp_path / "in/decision_handoff.json",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "run_result": tmp_path / "in/run_result.json",
        "lock": tmp_path / "in/lock.json",
        "ls13_validation": tmp_path / "in/ls13_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["approval_request"], _base_approval_request())
    _write_json(p["approval_checklist"], _base_checklist())
    _write_json(p["decision_input_template"], _base_decision_input_template())
    _write_json(p["initial_decision_record"], _base_initial_decision_record())
    _write_json(p["approval_scope_summary"], _base_scope_summary())
    _write_json(p["approval_safety_summary"], _base_safety_summary())
    _write_json(p["decision_handoff"], _base_decision_handoff())
    p["summary"].write_text(_base_summary(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls13_validation"], _base_ls13_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new14_draft_creation_execution_approval_gate.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--approval-request",
        str(p["approval_request"]),
        "--approval-checklist",
        str(p["approval_checklist"]),
        "--decision-input-template",
        str(p["decision_input_template"]),
        "--initial-decision-record",
        str(p["initial_decision_record"]),
        "--approval-scope-summary",
        str(p["approval_scope_summary"]),
        "--approval-safety-summary",
        str(p["approval_safety_summary"]),
        "--decision-handoff",
        str(p["decision_handoff"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new13-validation-result",
        str(p["ls13_validation"]),
        "--output",
        str(tmp_path / "out/validation.json"),
        "--report",
        str(tmp_path / "out/validation.md"),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_success(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "manifest",
        "approval_request",
        "approval_checklist",
        "decision_input_template",
        "initial_decision_record",
        "approval_scope_summary",
        "approval_safety_summary",
        "decision_handoff",
        "summary",
        "result",
        "run_result",
        "lock",
        "ls13_validation",
    ],
)
def test_missing_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls13_validation", "validation_status", "BAD", "ls-new13 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new13_validated", False, "manifest ls_new13_validated mismatch"),
        ("manifest", "ls_new13_command_prep_ready", False, "manifest ls_new13_command_prep_ready mismatch"),
        ("manifest", "human_approval_required", False, "manifest human_approval_required mismatch"),
        ("manifest", "required_approval_label", "BAD", "manifest required_approval_label mismatch"),
        ("manifest", "approval_label", "X", "manifest approval_label mismatch"),
        ("manifest", "approval_gate_manifest_created", False, "manifest approval_gate_manifest_created mismatch"),
        ("manifest", "approval_request_created", False, "manifest approval_request_created mismatch"),
        ("manifest", "approval_checklist_created", False, "manifest approval_checklist_created mismatch"),
        ("manifest", "approval_decision_input_template_created", False, "manifest approval_decision_input_template_created mismatch"),
        ("manifest", "initial_decision_record_created", False, "manifest initial_decision_record_created mismatch"),
        ("manifest", "approval_scope_summary_created", False, "manifest approval_scope_summary_created mismatch"),
        ("manifest", "approval_safety_summary_created", False, "manifest approval_safety_summary_created mismatch"),
        ("manifest", "decision_handoff_created", False, "manifest decision_handoff_created mismatch"),
        ("manifest", "approval_gate_summary_created", False, "manifest approval_gate_summary_created mismatch"),
        ("manifest", "one_shot_execution_count_target", 2, "manifest one_shot_execution_count_target mismatch"),
        ("manifest", "one_shot_execution_actual_count", 1, "manifest one_shot_execution_actual_count mismatch"),
        ("manifest", "ready_for_ls_new_14_decision", False, "manifest ready_for_ls_new_14_decision mismatch"),
        ("manifest", "recommended_next_action", "BAD", "manifest recommended_next_action mismatch"),
        ("approval_request", "phase", "BAD", "approval-request phase mismatch"),
        ("approval_request", "document_type", "BAD", "approval-request document_type mismatch"),
        ("approval_request", "status", "BAD", "approval-request status mismatch"),
        ("approval_request", "human_approval_required", False, "approval-request human_approval_required mismatch"),
        ("approval_request", "approval_scope", "BAD", "approval-request approval_scope mismatch"),
        ("approval_request", "required_approval_label", "BAD", "approval-request required_approval_label mismatch"),
        ("approval_request", "target_post_id", 1, "approval-request target_post_id must be null"),
        ("approval_request", "target_post_id_allocated", True, "approval-request target_post_id_allocated=true"),
        ("approval_request", "one_shot_execution_count_target", 2, "approval-request one_shot_execution_count_target mismatch"),
        ("approval_request", "one_shot_execution_actual_count", 1, "approval-request one_shot_execution_actual_count mismatch"),
        ("approval_request", "execution_allowed", True, "approval-request execution_allowed=true"),
        ("approval_checklist", "phase", "BAD", "approval-checklist phase mismatch"),
        ("approval_checklist", "document_type", "BAD", "approval-checklist document_type mismatch"),
        ("approval_checklist", "status", "BAD", "approval-checklist status mismatch"),
        ("approval_checklist", "all_required_checks_passed", False, "approval-checklist all_required_checks_passed mismatch"),
        ("decision_input_template", "phase", "BAD", "decision-input-template phase mismatch"),
        ("decision_input_template", "document_type", "BAD", "decision-input-template document_type mismatch"),
        ("decision_input_template", "human_approval_completed", True, "decision-input-template human_approval_completed=true"),
        ("decision_input_template", "human_approved_for_draft_creation", True, "decision-input-template human_approved_for_draft_creation=true"),
        ("decision_input_template", "approval_label", "X", "decision-input-template approval_label mismatch"),
        ("decision_input_template", "execution_allowed", True, "decision-input-template execution_allowed=true"),
        ("decision_input_template", "ready_for_ls_new_15", True, "decision-input-template ready_for_ls_new_15=true"),
        ("initial_decision_record", "phase", "BAD", "initial-decision-record phase mismatch"),
        ("initial_decision_record", "document_type", "BAD", "initial-decision-record document_type mismatch"),
        ("initial_decision_record", "status", "BAD", "initial-decision-record status mismatch"),
        ("initial_decision_record", "human_approval_completed", True, "initial-decision-record human_approval_completed=true"),
        ("initial_decision_record", "human_approved_for_draft_creation", True, "initial-decision-record human_approved_for_draft_creation=true"),
        ("initial_decision_record", "approval_label", "X", "initial-decision-record approval_label mismatch"),
        ("initial_decision_record", "ready_for_ls_new_15", True, "initial-decision-record ready_for_ls_new_15=true"),
        ("initial_decision_record", "execution_allowed", True, "initial-decision-record execution_allowed=true"),
        ("approval_scope_summary", "phase", "BAD", "approval-scope-summary phase mismatch"),
        ("approval_scope_summary", "document_type", "BAD", "approval-scope-summary document_type mismatch"),
        ("approval_scope_summary", "status", "BAD", "approval-scope-summary status mismatch"),
        ("approval_scope_summary", "approval_scope", "BAD", "approval-scope-summary approval_scope mismatch"),
        ("approval_scope_summary", "allowed_future_execution_count_after_later_decision", 2, "approval-scope-summary allowed_future_execution_count_after_later_decision mismatch"),
        ("approval_scope_summary", "current_execution_count", 1, "approval-scope-summary current_execution_count mismatch"),
        ("approval_scope_summary", "publish_scope_allowed", True, "approval-scope-summary publish_scope_allowed=true"),
        ("approval_scope_summary", "update_existing_post_allowed", True, "approval-scope-summary update_existing_post_allowed=true"),
        ("approval_scope_summary", "target_post_id_allocation_allowed", True, "approval-scope-summary target_post_id_allocation_allowed=true"),
        ("approval_scope_summary", "post119_forbidden", False, "approval-scope-summary post119_forbidden mismatch"),
        ("approval_scope_summary", "post183_forbidden", False, "approval-scope-summary post183_forbidden mismatch"),
        ("approval_scope_summary", "rerun_allowed", True, "approval-scope-summary rerun_allowed=true"),
        ("approval_scope_summary", "publish_rerun_allowed", True, "approval-scope-summary publish_rerun_allowed=true"),
        ("approval_scope_summary", "execution_allowed", True, "approval-scope-summary execution_allowed=true"),
        ("approval_safety_summary", "phase", "BAD", "approval-safety-summary phase mismatch"),
        ("approval_safety_summary", "document_type", "BAD", "approval-safety-summary document_type mismatch"),
        ("approval_safety_summary", "status", "BAD", "approval-safety-summary status mismatch"),
        ("approval_safety_summary", "human_approval_required", False, "approval-safety-summary human_approval_required mismatch"),
        ("decision_handoff", "phase", "BAD", "decision-handoff phase mismatch"),
        ("decision_handoff", "document_type", "BAD", "decision-handoff document_type mismatch"),
        ("decision_handoff", "status", "BAD", "decision-handoff status mismatch"),
        ("decision_handoff", "next_phase", "BAD", "decision-handoff next_phase mismatch"),
        ("decision_handoff", "next_phase_name", "BAD", "decision-handoff next_phase_name mismatch"),
        ("decision_handoff", "handoff_ready", False, "decision-handoff handoff_ready mismatch"),
        ("decision_handoff", "ready_for_ls_new_14_decision", False, "decision-handoff ready_for_ls_new_14_decision mismatch"),
        ("decision_handoff", "ready_for_ls_new_15", True, "decision-handoff ready_for_ls_new_15=true"),
        ("decision_handoff", "required_approval_label", "BAD", "decision-handoff required_approval_label mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new13_validated", False, "result ls_new13_validated mismatch"),
        ("result", "ls_new13_command_prep_ready", False, "result ls_new13_command_prep_ready mismatch"),
        ("result", "human_approval_required", False, "result human_approval_required mismatch"),
        ("result", "required_approval_label", "BAD", "result required_approval_label mismatch"),
        ("result", "approval_label", "X", "result approval_label mismatch"),
        ("result", "approval_gate_manifest_created", False, "result approval_gate_manifest_created mismatch"),
        ("result", "approval_request_created", False, "result approval_request_created mismatch"),
        ("result", "approval_checklist_created", False, "result approval_checklist_created mismatch"),
        ("result", "approval_decision_input_template_created", False, "result approval_decision_input_template_created mismatch"),
        ("result", "initial_decision_record_created", False, "result initial_decision_record_created mismatch"),
        ("result", "approval_scope_summary_created", False, "result approval_scope_summary_created mismatch"),
        ("result", "approval_safety_summary_created", False, "result approval_safety_summary_created mismatch"),
        ("result", "decision_handoff_created", False, "result decision_handoff_created mismatch"),
        ("result", "approval_gate_summary_created", False, "result approval_gate_summary_created mismatch"),
        ("result", "one_shot_execution_count_target", 2, "result one_shot_execution_count_target mismatch"),
        ("result", "one_shot_execution_actual_count", 1, "result one_shot_execution_actual_count mismatch"),
        ("result", "ready_for_ls_new_14_decision", False, "result ready_for_ls_new_14_decision mismatch"),
        ("result", "recommended_next_action", "BAD", "result recommended_next_action mismatch"),
        ("result", "target_post_id", 1, "result target_post_id must be null"),
        ("lock", "phase", "BAD", "lock phase mismatch"),
        ("lock", "document_type", "BAD", "lock document_type mismatch"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
    ],
)
def test_structure_constraints(tmp_path: Path, target: str, key: str, value: Any, error: str) -> None:
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
        ("human_approved_for_draft_creation", "result human_approved_for_draft_creation=true"),
        ("approval_label_consumed", "result approval_label_consumed=true"),
        ("approval_label_autofill_executed", "result approval_label_autofill_executed=true"),
        ("auto_approval_executed", "result auto_approval_executed=true"),
        ("ai_self_approval_executed", "result ai_self_approval_executed=true"),
        ("execution_allowed", "result execution_allowed=true"),
        ("runner_execution_allowed", "result runner_execution_allowed=true"),
        ("final_execution_command_created", "result final_execution_command_created=true"),
        ("actual_executable_command_created", "result actual_executable_command_created=true"),
        ("shell_execution_performed", "result shell_execution_performed=true"),
        ("wordpress_api_call_executed", "result wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "result wordpress_write_executed=true"),
        ("wordpress_draft_created", "result wordpress_draft_created=true"),
        ("wordpress_publish_executed", "result wordpress_publish_executed=true"),
        ("wordpress_update_executed", "result wordpress_update_executed=true"),
        ("wordpress_delete_executed", "result wordpress_delete_executed=true"),
        ("x_api_call_executed", "result x_api_call_executed=true"),
        ("x_post_executed", "result x_post_executed=true"),
        ("external_fetch_executed", "result external_fetch_executed=true"),
        ("http_get_executed", "result http_get_executed=true"),
        ("web_scraping_executed", "result web_scraping_executed=true"),
        ("rss_fetch_executed", "result rss_fetch_executed=true"),
        ("amazon_api_call_executed", "result amazon_api_call_executed=true"),
        ("pa_api_call_executed", "result pa_api_call_executed=true"),
        ("creators_api_call_executed", "result creators_api_call_executed=true"),
        ("credential_env_read_executed", "result credential_env_read_executed=true"),
        ("credential_value_output", "result credential_value_output=true"),
        ("credential_secret_output", "result credential_secret_output=true"),
        ("credential_length_output", "result credential_length_output=true"),
        ("credential_hash_output", "result credential_hash_output=true"),
        ("authorization_header_output", "result authorization_header_output=true"),
        ("basic_auth_output", "result basic_auth_output=true"),
        ("base64_auth_output", "result base64_auth_output=true"),
        ("response_body_output", "result response_body_output=true"),
        ("user_identity_output", "result user_identity_output=true"),
        ("target_post_id_allocated", "result target_post_id_allocated=true"),
        ("post119_update_executed", "result post119_update_executed=true"),
        ("post183_update_executed", "result post183_update_executed=true"),
        ("candidate_selected", "result candidate_selected=true"),
        ("ls_next1_fill_updated", "result ls_next1_fill_updated=true"),
        ("rerun_allowed", "result rerun_allowed=true"),
        ("publish_rerun_allowed", "result publish_rerun_allowed=true"),
        ("ready_for_ls_new_15", "result ready_for_ls_new_15=true"),
    ],
)
def test_result_true_detections(tmp_path: Path, key: str, error: str) -> None:
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
        ("human_approval_completed", "lock human_approval_completed=true"),
        ("human_approved_for_draft_creation", "lock human_approved_for_draft_creation=true"),
        ("approval_label_consumed", "lock approval_label_consumed=true"),
        ("approval_label_autofill_executed", "lock approval_label_autofill_executed=true"),
        ("auto_approval_executed", "lock auto_approval_executed=true"),
        ("ai_self_approval_executed", "lock ai_self_approval_executed=true"),
        ("actual_executable_command_created", "lock actual_executable_command_created=true"),
        ("shell_execution_performed", "lock shell_execution_performed=true"),
        ("execution_allowed", "lock execution_allowed=true"),
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("wordpress_api_call_executed", "lock wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "lock wordpress_write_executed=true"),
        ("wordpress_draft_created", "lock wordpress_draft_created=true"),
        ("wordpress_publish_executed", "lock wordpress_publish_executed=true"),
        ("credential_env_read_executed", "lock credential_env_read_executed=true"),
        ("target_post_id_allocated", "lock target_post_id_allocated=true"),
        ("ready_for_ls_new_15", "lock ready_for_ls_new_15=true"),
        ("rerun_allowed", "lock rerun_allowed=true"),
        ("publish_rerun_allowed", "lock publish_rerun_allowed=true"),
    ],
)
def test_lock_true_detections(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["lock"])
    d[key] = True
    _write_json(p["lock"], d)
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


@pytest.mark.parametrize(
    "text,error",
    [
        ("", "summary header mismatch"),
        ("# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary\n", "summary human_approval_required mismatch"),
        ("# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary\n- Human approval required: true\n", "summary human_approval_completed mismatch"),
        ("# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary\n- Human approval required: true\n- Human approval completed: false\n", "summary human_approved_for_draft_creation mismatch"),
    ],
)
def test_summary_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["summary"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_no_forbidden_execution_or_http_patterns() -> None:
    src = Path("scripts/validate_start_ls_new14_draft_creation_execution_approval_gate.py").read_text(encoding="utf-8")
    forbidden = ["requests.", "urllib.request", "subprocess.run", "os.system", "Popen(", "http.client"]
    assert all(x not in src for x in forbidden)
    assert "Authorization:" not in src
    assert "base64" not in src
