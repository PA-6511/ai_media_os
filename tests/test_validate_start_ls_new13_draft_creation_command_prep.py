from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict[str, Any]:
    return {"phase": "LS-NEW-13"}


def _base_schema() -> dict[str, Any]:
    return {"phase": "LS-NEW-13"}


def _base_manifest() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_MANIFEST",
        "status": "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION",
        "execution_mode": "DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION",
        "production_status": "NO_EXECUTION_DRAFT_CREATION_COMMAND_PREP_ONLY",
        "ls_new12_validated": True,
        "ls_new12_authenticated_read_ready": True,
        "draft_creation_command_prep_manifest_created": True,
        "draft_creation_payload_map_created": True,
        "blocked_draft_creation_command_template_created": True,
        "one_shot_draft_creation_boundary_created": True,
        "pre_execution_checklist_created": True,
        "no_execution_safety_contract_created": True,
        "next_phase_approval_handoff_created": True,
        "command_prep_summary_created": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
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
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ready_for_ls_new_14": True,
        "recommended_next_action": "BEGIN_LS_NEW_14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-14", "LS-MON-2"],
        "errors": [],
    }


def _base_payload_map() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_PAYLOAD_MAP",
        "status": "LSNEW13_DRAFT_CREATION_PAYLOAD_MAP_READY_NO_EXECUTION",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "payload_title_confirmed": True,
        "payload_body_present": True,
        "payload_status_draft_confirmed": True,
        "payload_source_not_modified": True,
        "execution_allowed": False,
    }


def _base_blocked_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-13 Blocked Draft Creation Command Template",
            "This is not an executable command.",
            "Do not run a WordPress POST from LS-NEW-13.",
            "Execution allowed: false",
            "",
        ]
    )


def _base_one_shot() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY",
        "status": "LSNEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY_READY_NO_EXECUTION",
        "one_shot_draft_creation_planned": True,
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_forbidden": True,
        "post183_update_forbidden": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "execution_allowed": False,
    }


def _base_checklist() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_PRE_EXECUTION_CHECKLIST",
        "status": "LSNEW13_PRE_EXECUTION_CHECKLIST_READY_NO_EXECUTION",
        "check_items": {
            "ls_new12_authenticated_read_validated": True,
            "payload_source_confirmed": True,
            "payload_status_is_draft": True,
            "target_post_id_is_null": True,
            "target_post_id_allocated": False,
            "execution_allowed": False,
        },
        "all_required_checks_passed": True,
    }


def _base_contract() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_NO_EXECUTION_SAFETY_CONTRACT",
        "status": "LSNEW13_NO_EXECUTION_SAFETY_CONTRACT_READY",
        "no_execution_required": True,
        "wordpress_api_call_allowed": False,
        "wordpress_post_allowed": False,
        "wordpress_put_allowed": False,
        "wordpress_patch_allowed": False,
        "wordpress_delete_allowed": False,
        "wordpress_draft_create_allowed": False,
        "wordpress_publish_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "shell_execution_allowed": False,
        "credential_env_read_allowed": False,
        "target_post_id_allocation_allowed": False,
        "execution_allowed": False,
    }


def _base_handoff() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_NEXT_PHASE_APPROVAL_HANDOFF",
        "status": "LSNEW13_NEXT_PHASE_APPROVAL_HANDOFF_READY",
        "next_phase": "LS-NEW-14",
        "next_phase_name": "Separate Draft Creation Execution Approval Gate",
        "handoff_ready": True,
        "ready_for_ls_new_14": True,
        "required_approval_label_next_phase": "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY",
    }


def _base_result() -> dict[str, Any]:
    d = _base_manifest().copy()
    d["document_type"] = "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_RESULT"
    return d


def _base_lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_LOCK",
        "status": "LSNEW13_DRAFT_CREATION_COMMAND_PREP_LOCKED_NO_EXECUTION",
        "locked": True,
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
        "approval_label_consumed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls12_validation() -> dict[str, Any]:
    return {"validation_status": "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"}


def _base_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-13 Draft Creation Command Prep Summary",
            "- Execution allowed: false",
            "- Actual executable command created: false",
            "- Shell execution performed: false",
            "- Ready for LS-NEW-14: true",
            "",
        ]
    )


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "payload_map": tmp_path / "in/payload_map.json",
        "blocked": tmp_path / "in/blocked.md",
        "one_shot": tmp_path / "in/one_shot.json",
        "checklist": tmp_path / "in/checklist.json",
        "contract": tmp_path / "in/contract.json",
        "handoff": tmp_path / "in/handoff.json",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "run_result": tmp_path / "in/run_result.json",
        "lock": tmp_path / "in/lock.json",
        "ls12_validation": tmp_path / "in/ls12_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["payload_map"], _base_payload_map())
    p["blocked"].write_text(_base_blocked_text(), encoding="utf-8")
    _write_json(p["one_shot"], _base_one_shot())
    _write_json(p["checklist"], _base_checklist())
    _write_json(p["contract"], _base_contract())
    _write_json(p["handoff"], _base_handoff())
    p["summary"].write_text(_base_summary(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls12_validation"], _base_ls12_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new13_draft_creation_command_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--payload-map",
        str(p["payload_map"]),
        "--blocked-command-template",
        str(p["blocked"]),
        "--one-shot-boundary",
        str(p["one_shot"]),
        "--pre-execution-checklist",
        str(p["checklist"]),
        "--no-execution-safety-contract",
        str(p["contract"]),
        "--next-phase-approval-handoff",
        str(p["handoff"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new12-validation-result",
        str(p["ls12_validation"]),
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
    assert out["validation_status"] == "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "manifest",
        "payload_map",
        "blocked",
        "one_shot",
        "checklist",
        "contract",
        "handoff",
        "summary",
        "result",
        "run_result",
        "lock",
        "ls12_validation",
    ],
)
def test_missing_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW13_DRAFT_CREATION_COMMAND_PREP_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls12_validation", "validation_status", "BAD", "ls-new12 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new12_validated", False, "manifest ls_new12_validated mismatch"),
        ("manifest", "ls_new12_authenticated_read_ready", False, "manifest ls_new12_authenticated_read_ready mismatch"),
        ("manifest", "draft_creation_command_prep_manifest_created", False, "manifest draft_creation_command_prep_manifest_created mismatch"),
        ("manifest", "draft_creation_payload_map_created", False, "manifest draft_creation_payload_map_created mismatch"),
        ("manifest", "blocked_draft_creation_command_template_created", False, "manifest blocked_draft_creation_command_template_created mismatch"),
        ("manifest", "one_shot_draft_creation_boundary_created", False, "manifest one_shot_draft_creation_boundary_created mismatch"),
        ("manifest", "pre_execution_checklist_created", False, "manifest pre_execution_checklist_created mismatch"),
        ("manifest", "no_execution_safety_contract_created", False, "manifest no_execution_safety_contract_created mismatch"),
        ("manifest", "next_phase_approval_handoff_created", False, "manifest next_phase_approval_handoff_created mismatch"),
        ("manifest", "command_prep_summary_created", False, "manifest command_prep_summary_created mismatch"),
        ("manifest", "one_shot_execution_count_target", 2, "manifest one_shot_execution_count_target mismatch"),
        ("manifest", "one_shot_execution_actual_count", 1, "manifest one_shot_execution_actual_count mismatch"),
        ("manifest", "ready_for_ls_new_14", False, "manifest ready_for_ls_new_14 mismatch"),
        ("manifest", "recommended_next_action", "BAD", "manifest recommended_next_action mismatch"),
        ("payload_map", "phase", "BAD", "payload-map phase mismatch"),
        ("payload_map", "document_type", "BAD", "payload-map document_type mismatch"),
        ("payload_map", "status", "BAD", "payload-map status mismatch"),
        ("payload_map", "post_status_target", "publish", "payload-map post_status_target mismatch"),
        ("payload_map", "target_post_id", 1, "payload-map target_post_id must be null"),
        ("payload_map", "target_post_id_allocated", True, "payload-map target_post_id_allocated mismatch"),
        ("payload_map", "payload_title_confirmed", False, "payload-map payload_title_confirmed mismatch"),
        ("payload_map", "payload_body_present", False, "payload-map payload_body_present mismatch"),
        ("payload_map", "payload_status_draft_confirmed", False, "payload-map payload_status_draft_confirmed mismatch"),
        ("payload_map", "payload_source_not_modified", False, "payload-map payload_source_not_modified mismatch"),
        ("payload_map", "execution_allowed", True, "payload-map execution_allowed=true"),
        ("one_shot", "phase", "BAD", "one-shot-boundary phase mismatch"),
        ("one_shot", "document_type", "BAD", "one-shot-boundary document_type mismatch"),
        ("one_shot", "status", "BAD", "one-shot-boundary status mismatch"),
        ("one_shot", "one_shot_draft_creation_planned", False, "one-shot-boundary one_shot_draft_creation_planned mismatch"),
        ("one_shot", "one_shot_execution_count_target", 2, "one-shot-boundary one_shot_execution_count_target mismatch"),
        ("one_shot", "one_shot_execution_actual_count", 1, "one-shot-boundary one_shot_execution_actual_count mismatch"),
        ("one_shot", "draft_creation_executed_in_current_phase", True, "one-shot-boundary draft_creation_executed_in_current_phase=true"),
        ("one_shot", "wordpress_draft_created", True, "one-shot-boundary wordpress_draft_created=true"),
        ("one_shot", "target_post_id", 1, "one-shot-boundary target_post_id must be null"),
        ("one_shot", "target_post_id_allocated", True, "one-shot-boundary target_post_id_allocated=true"),
        ("one_shot", "rerun_allowed", True, "one-shot-boundary rerun_allowed=true"),
        ("one_shot", "publish_rerun_allowed", True, "one-shot-boundary publish_rerun_allowed=true"),
        ("one_shot", "execution_allowed", True, "one-shot-boundary execution_allowed=true"),
        ("checklist", "phase", "BAD", "pre-execution-checklist phase mismatch"),
        ("checklist", "document_type", "BAD", "pre-execution-checklist document_type mismatch"),
        ("checklist", "status", "BAD", "pre-execution-checklist status mismatch"),
        ("checklist", "all_required_checks_passed", False, "pre-execution-checklist all_required_checks_passed mismatch"),
        ("contract", "phase", "BAD", "no-execution-safety-contract phase mismatch"),
        ("contract", "document_type", "BAD", "no-execution-safety-contract document_type mismatch"),
        ("contract", "status", "BAD", "no-execution-safety-contract status mismatch"),
        ("contract", "no_execution_required", False, "no-execution-safety-contract no_execution_required mismatch"),
        ("handoff", "phase", "BAD", "handoff phase mismatch"),
        ("handoff", "document_type", "BAD", "handoff document_type mismatch"),
        ("handoff", "status", "BAD", "handoff status mismatch"),
        ("handoff", "next_phase", "BAD", "handoff next_phase mismatch"),
        ("handoff", "next_phase_name", "BAD", "handoff next_phase_name mismatch"),
        ("handoff", "handoff_ready", False, "handoff handoff_ready mismatch"),
        ("handoff", "ready_for_ls_new_14", False, "handoff ready_for_ls_new_14 mismatch"),
        ("handoff", "required_approval_label_next_phase", "BAD", "handoff required_approval_label_next_phase mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new12_validated", False, "result ls_new12_validated mismatch"),
        ("result", "ls_new12_authenticated_read_ready", False, "result ls_new12_authenticated_read_ready mismatch"),
        ("result", "draft_creation_command_prep_manifest_created", False, "result draft_creation_command_prep_manifest_created mismatch"),
        ("result", "draft_creation_payload_map_created", False, "result draft_creation_payload_map_created mismatch"),
        ("result", "blocked_draft_creation_command_template_created", False, "result blocked_draft_creation_command_template_created mismatch"),
        ("result", "one_shot_draft_creation_boundary_created", False, "result one_shot_draft_creation_boundary_created mismatch"),
        ("result", "pre_execution_checklist_created", False, "result pre_execution_checklist_created mismatch"),
        ("result", "no_execution_safety_contract_created", False, "result no_execution_safety_contract_created mismatch"),
        ("result", "next_phase_approval_handoff_created", False, "result next_phase_approval_handoff_created mismatch"),
        ("result", "command_prep_summary_created", False, "result command_prep_summary_created mismatch"),
        ("result", "one_shot_execution_count_target", 2, "result one_shot_execution_count_target mismatch"),
        ("result", "one_shot_execution_actual_count", 1, "result one_shot_execution_actual_count mismatch"),
        ("result", "ready_for_ls_new_14", False, "result ready_for_ls_new_14 mismatch"),
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
        ("actual_executable_command_created", "result actual_executable_command_created=true"),
        ("shell_execution_performed", "result shell_execution_performed=true"),
        ("execution_allowed", "result execution_allowed=true"),
        ("runner_execution_allowed", "result runner_execution_allowed=true"),
        ("final_execution_command_created", "result final_execution_command_created=true"),
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
        ("approval_label_consumed", "result approval_label_consumed=true"),
        ("post119_update_executed", "result post119_update_executed=true"),
        ("post183_update_executed", "result post183_update_executed=true"),
        ("candidate_selected", "result candidate_selected=true"),
        ("ls_next1_fill_updated", "result ls_next1_fill_updated=true"),
        ("rerun_allowed", "result rerun_allowed=true"),
        ("publish_rerun_allowed", "result publish_rerun_allowed=true"),
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
        ("approval_label_consumed", "lock approval_label_consumed=true"),
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


@pytest.mark.parametrize(
    "text,error",
    [
        ("", "summary header mismatch"),
        ("# LS-NEW-13 Draft Creation Command Prep Summary\n", "summary execution allowed mismatch"),
        ("# LS-NEW-13 Draft Creation Command Prep Summary\n- Execution allowed: false\n", "summary actual executable command mismatch"),
    ],
)
def test_summary_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["summary"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "text,error",
    [
        ("", "blocked-template header mismatch"),
        ("# LS-NEW-13 Blocked Draft Creation Command Template\n", "blocked-template executable warning missing"),
        ("# LS-NEW-13 Blocked Draft Creation Command Template\nThis is not an executable command.\n", "blocked-template do-not-run warning missing"),
    ],
)
def test_blocked_template_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["blocked"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_no_forbidden_execution_or_http_patterns() -> None:
    src = Path("scripts/validate_start_ls_new13_draft_creation_command_prep.py").read_text(encoding="utf-8")
    forbidden = ["requests.", "urllib.request", "subprocess.run", "os.system", "Popen("]
    assert all(x not in src for x in forbidden)
