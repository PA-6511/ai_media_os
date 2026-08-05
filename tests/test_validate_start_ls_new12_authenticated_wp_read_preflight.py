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
    return {"phase": "LS-NEW-12"}


def _base_schema() -> dict[str, Any]:
    return {"phase": "LS-NEW-12"}


def _base_manifest() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_MANIFEST",
        "status": "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE",
        "execution_mode": "AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE",
        "production_status": "NO_WRITE_AUTHENTICATED_READ_PREFLIGHT_ONLY",
        "ls_new11_validated": True,
        "ls_new11_ready": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "credential_env_exists": True,
        "credential_existence_check_executed": True,
        "credential_env_read_executed": True,
        "wordpress_authenticated_read_get_attempted": True,
        "wordpress_authenticated_read_get_succeeded": True,
        "wordpress_authenticated_read_status_class": "2xx",
        "wordpress_authenticated_read_endpoint_kind": "users_me",
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "authenticated_wp_read_result_created": True,
        "secret_non_output_summary_created": True,
        "no_write_safety_contract_created": True,
        "draft_creation_hold_boundary_created": True,
        "next_phase_handoff_created": True,
        "preflight_summary_created": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "generic_external_fetch_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "ready_for_ls_new_13": True,
        "recommended_next_action": "BEGIN_LS_NEW_13_DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-13", "LS-MON-2"],
        "errors": [],
    }


def _base_authenticated_read_result() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_RESULT",
        "status": "LSNEW12_AUTHENTICATED_WP_READ_READY_NO_WRITE",
        "wordpress_authenticated_read_get_attempted": True,
        "wordpress_authenticated_read_get_succeeded": True,
        "wordpress_authenticated_read_status_class": "2xx",
        "wordpress_authenticated_read_endpoint_kind": "users_me",
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "execution_allowed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "response_body_output": False,
        "user_identity_output": False,
    }


def _base_secret_non_output_summary() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_SECRET_NON_OUTPUT_SUMMARY",
        "status": "LSNEW12_SECRET_NON_OUTPUT_CONFIRMED",
        "credential_env_read_executed": True,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
    }


def _base_contract() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_NO_WRITE_SAFETY_CONTRACT",
        "status": "LSNEW12_NO_WRITE_SAFETY_CONTRACT_READY",
        "no_write_required": True,
        "wordpress_get_only": True,
        "wordpress_post_allowed": False,
        "wordpress_put_allowed": False,
        "wordpress_patch_allowed": False,
        "wordpress_delete_allowed": False,
        "wordpress_draft_create_allowed": False,
        "wordpress_publish_allowed": False,
        "wordpress_update_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "target_post_id_allocation_allowed": False,
        "execution_allowed": False,
    }


def _base_draft_hold() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_DRAFT_CREATION_HOLD_BOUNDARY",
        "status": "LSNEW12_DRAFT_CREATION_HOLD_BOUNDARY_READY_NO_DRAFT_CREATION",
        "draft_creation_still_blocked": True,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "required_before_later_draft_creation": ["x"],
        "execution_allowed": False,
    }


def _base_handoff() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_NEXT_PHASE_HANDOFF",
        "status": "LSNEW12_NEXT_PHASE_HANDOFF_READY",
        "next_phase": "LS-NEW-13",
        "next_phase_name": "Draft Creation Command Prep / No Execution",
        "handoff_ready": True,
        "ready_for_ls_new_13": True,
        "notes": ["n1", "n2"],
    }


def _base_result() -> dict[str, Any]:
    d = _base_manifest().copy()
    d["document_type"] = "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_RESULT"
    return d


def _base_lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCK",
        "status": "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCKED_NO_WRITE",
        "locked": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls11_validation() -> dict[str, Any]:
    return {"validation_status": "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"}


def _base_summary_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-12 Authenticated WP Read Preflight Summary",
            "- Authenticated WP read GET succeeded: true",
            "- Response body saved: false",
            "- Authenticated user identity saved: false",
            "- Authorization header output: false",
            "- Ready for LS-NEW-13: true",
            "",
        ]
    )


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "authenticated_read_result": tmp_path / "in/authenticated_read_result.json",
        "secret_non_output_summary": tmp_path / "in/secret_non_output_summary.json",
        "contract": tmp_path / "in/contract.json",
        "draft_hold": tmp_path / "in/draft_hold.json",
        "handoff": tmp_path / "in/handoff.json",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "run_result": tmp_path / "in/run_result.json",
        "lock": tmp_path / "in/lock.json",
        "ls11_validation": tmp_path / "in/ls11_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["authenticated_read_result"], _base_authenticated_read_result())
    _write_json(p["secret_non_output_summary"], _base_secret_non_output_summary())
    _write_json(p["contract"], _base_contract())
    _write_json(p["draft_hold"], _base_draft_hold())
    _write_json(p["handoff"], _base_handoff())
    p["summary"].write_text(_base_summary_text(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls11_validation"], _base_ls11_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new12_authenticated_wp_read_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--authenticated-read-result",
        str(p["authenticated_read_result"]),
        "--secret-non-output-summary",
        str(p["secret_non_output_summary"]),
        "--no-write-safety-contract",
        str(p["contract"]),
        "--draft-creation-hold-boundary",
        str(p["draft_hold"]),
        "--next-phase-handoff",
        str(p["handoff"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new11-validation-result",
        str(p["ls11_validation"]),
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
    assert out["validation_status"] == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "manifest",
        "authenticated_read_result",
        "secret_non_output_summary",
        "contract",
        "draft_hold",
        "handoff",
        "summary",
        "result",
        "run_result",
        "lock",
        "ls11_validation",
    ],
)
def test_missing_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls11_validation", "validation_status", "BAD", "ls-new11 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new11_validated", False, "manifest ls_new11_validated mismatch"),
        ("manifest", "ls_new11_ready", False, "manifest ls_new11_ready mismatch"),
        ("manifest", "credential_env_exists", False, "manifest credential_env_exists mismatch"),
        ("manifest", "credential_existence_check_executed", False, "manifest credential_existence_check_executed mismatch"),
        ("manifest", "credential_env_read_executed", False, "manifest credential_env_read_executed mismatch"),
        ("manifest", "wordpress_authenticated_read_get_attempted", False, "manifest wordpress_authenticated_read_get_attempted mismatch"),
        ("manifest", "wordpress_authenticated_read_get_succeeded", False, "manifest wordpress_authenticated_read_get_succeeded mismatch"),
        ("manifest", "wordpress_authenticated_read_status_class", "4xx", "manifest wordpress_authenticated_read_status_class mismatch"),
        ("manifest", "wordpress_authenticated_read_endpoint_kind", "other", "manifest wordpress_authenticated_read_endpoint_kind mismatch"),
        ("manifest", "ready_for_ls_new_13", False, "manifest ready_for_ls_new_13 mismatch"),
        ("manifest", "recommended_next_action", "BAD", "manifest recommended_next_action mismatch"),
        ("authenticated_read_result", "phase", "BAD", "authenticated-read-result phase mismatch"),
        ("authenticated_read_result", "document_type", "BAD", "authenticated-read-result document_type mismatch"),
        ("authenticated_read_result", "status", "BAD", "authenticated-read-result status mismatch"),
        ("authenticated_read_result", "wordpress_authenticated_read_get_attempted", False, "authenticated-read-result wordpress_authenticated_read_get_attempted mismatch"),
        ("authenticated_read_result", "wordpress_authenticated_read_get_succeeded", False, "authenticated-read-result wordpress_authenticated_read_get_succeeded mismatch"),
        ("authenticated_read_result", "wordpress_authenticated_read_status_class", "4xx", "authenticated-read-result wordpress_authenticated_read_status_class mismatch"),
        ("authenticated_read_result", "wordpress_authenticated_read_endpoint_kind", "other", "authenticated-read-result wordpress_authenticated_read_endpoint_kind mismatch"),
        ("secret_non_output_summary", "phase", "BAD", "secret-non-output-summary phase mismatch"),
        ("secret_non_output_summary", "document_type", "BAD", "secret-non-output-summary document_type mismatch"),
        ("secret_non_output_summary", "status", "BAD", "secret-non-output-summary status mismatch"),
        ("secret_non_output_summary", "credential_env_read_executed", False, "secret-non-output-summary credential_env_read_executed mismatch"),
        ("contract", "phase", "BAD", "no-write-contract phase mismatch"),
        ("contract", "document_type", "BAD", "no-write-contract document_type mismatch"),
        ("contract", "status", "BAD", "no-write-contract status mismatch"),
        ("contract", "no_write_required", False, "no-write-contract no_write_required mismatch"),
        ("contract", "wordpress_get_only", False, "no-write-contract wordpress_get_only mismatch"),
        ("draft_hold", "phase", "BAD", "draft-hold-boundary phase mismatch"),
        ("draft_hold", "document_type", "BAD", "draft-hold-boundary document_type mismatch"),
        ("draft_hold", "status", "BAD", "draft-hold-boundary status mismatch"),
        ("draft_hold", "draft_creation_still_blocked", False, "draft-hold-boundary draft_creation_still_blocked mismatch"),
        ("draft_hold", "draft_creation_executed_in_current_phase", True, "draft-hold-boundary draft_creation_executed_in_current_phase=true"),
        ("draft_hold", "wordpress_draft_created", True, "draft-hold-boundary wordpress_draft_created=true"),
        ("draft_hold", "target_post_id", 1, "draft-hold-boundary target_post_id must be null"),
        ("draft_hold", "target_post_id_allocated", True, "draft-hold-boundary target_post_id_allocated=true"),
        ("handoff", "phase", "BAD", "handoff phase mismatch"),
        ("handoff", "document_type", "BAD", "handoff document_type mismatch"),
        ("handoff", "status", "BAD", "handoff status mismatch"),
        ("handoff", "next_phase", "BAD", "handoff next_phase mismatch"),
        ("handoff", "next_phase_name", "BAD", "handoff next_phase_name mismatch"),
        ("handoff", "handoff_ready", False, "handoff handoff_ready mismatch"),
        ("handoff", "ready_for_ls_new_13", False, "handoff ready_for_ls_new_13 mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new11_validated", False, "result ls_new11_validated mismatch"),
        ("result", "ls_new11_ready", False, "result ls_new11_ready mismatch"),
        ("result", "credential_env_exists", False, "result credential_env_exists mismatch"),
        ("result", "credential_existence_check_executed", False, "result credential_existence_check_executed mismatch"),
        ("result", "credential_env_read_executed", False, "result credential_env_read_executed mismatch"),
        ("result", "wordpress_authenticated_read_get_attempted", False, "result wordpress_authenticated_read_get_attempted mismatch"),
        ("result", "wordpress_authenticated_read_get_succeeded", False, "result wordpress_authenticated_read_get_succeeded mismatch"),
        ("result", "wordpress_authenticated_read_status_class", "4xx", "result wordpress_authenticated_read_status_class mismatch"),
        ("result", "wordpress_authenticated_read_endpoint_kind", "other", "result wordpress_authenticated_read_endpoint_kind mismatch"),
        ("result", "ready_for_ls_new_13", False, "result ready_for_ls_new_13 mismatch"),
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
        ("credential_value_output", "result credential_value_output=true"),
        ("credential_secret_output", "result credential_secret_output=true"),
        ("credential_length_output", "result credential_length_output=true"),
        ("credential_hash_output", "result credential_hash_output=true"),
        ("authorization_header_output", "result authorization_header_output=true"),
        ("basic_auth_output", "result basic_auth_output=true"),
        ("base64_auth_output", "result base64_auth_output=true"),
        ("response_body_output", "result response_body_output=true"),
        ("user_identity_output", "result user_identity_output=true"),
        ("wordpress_authenticated_read_response_body_saved", "result wordpress_authenticated_read_response_body_saved=true"),
        ("wordpress_authenticated_user_identity_saved", "result wordpress_authenticated_user_identity_saved=true"),
        ("wordpress_write_executed", "result wordpress_write_executed=true"),
        ("wordpress_draft_created", "result wordpress_draft_created=true"),
        ("wordpress_publish_executed", "result wordpress_publish_executed=true"),
        ("wordpress_update_executed", "result wordpress_update_executed=true"),
        ("wordpress_delete_executed", "result wordpress_delete_executed=true"),
        ("execution_allowed", "result execution_allowed=true"),
        ("runner_execution_allowed", "result runner_execution_allowed=true"),
        ("final_execution_command_created", "result final_execution_command_created=true"),
        ("target_post_id_allocated", "result target_post_id_allocated=true"),
        ("approval_label_consumed", "result approval_label_consumed=true"),
        ("post119_update_executed", "result post119_update_executed=true"),
        ("post183_update_executed", "result post183_update_executed=true"),
        ("candidate_selected", "result candidate_selected=true"),
        ("ls_next1_fill_updated", "result ls_next1_fill_updated=true"),
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
        ("credential_value_output", "secret-non-output-summary credential_value_output=true"),
        ("credential_secret_output", "secret-non-output-summary credential_secret_output=true"),
        ("credential_length_output", "secret-non-output-summary credential_length_output=true"),
        ("credential_hash_output", "secret-non-output-summary credential_hash_output=true"),
        ("authorization_header_output", "secret-non-output-summary authorization_header_output=true"),
        ("basic_auth_output", "secret-non-output-summary basic_auth_output=true"),
        ("base64_auth_output", "secret-non-output-summary base64_auth_output=true"),
        ("response_body_output", "secret-non-output-summary response_body_output=true"),
        ("user_identity_output", "secret-non-output-summary user_identity_output=true"),
        ("wordpress_authenticated_read_response_body_saved", "secret-non-output-summary wordpress_authenticated_read_response_body_saved=true"),
        ("wordpress_authenticated_user_identity_saved", "secret-non-output-summary wordpress_authenticated_user_identity_saved=true"),
    ],
)
def test_secret_summary_true_detections(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["secret_non_output_summary"])
    d[key] = True
    _write_json(p["secret_non_output_summary"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
        ("execution_allowed", "lock execution_allowed=true"),
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("wordpress_write_executed", "lock wordpress_write_executed=true"),
        ("wordpress_draft_created", "lock wordpress_draft_created=true"),
        ("wordpress_publish_executed", "lock wordpress_publish_executed=true"),
        ("wordpress_update_executed", "lock wordpress_update_executed=true"),
        ("wordpress_delete_executed", "lock wordpress_delete_executed=true"),
        ("credential_value_output", "lock credential_value_output=true"),
        ("credential_secret_output", "lock credential_secret_output=true"),
        ("credential_length_output", "lock credential_length_output=true"),
        ("credential_hash_output", "lock credential_hash_output=true"),
        ("authorization_header_output", "lock authorization_header_output=true"),
        ("basic_auth_output", "lock basic_auth_output=true"),
        ("base64_auth_output", "lock base64_auth_output=true"),
        ("response_body_output", "lock response_body_output=true"),
        ("user_identity_output", "lock user_identity_output=true"),
        ("wordpress_authenticated_read_response_body_saved", "lock wordpress_authenticated_read_response_body_saved=true"),
        ("wordpress_authenticated_user_identity_saved", "lock wordpress_authenticated_user_identity_saved=true"),
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
        ("# LS-NEW-12 Authenticated WP Read Preflight Summary\n", "summary authenticated read succeeded mismatch"),
        ("# LS-NEW-12 Authenticated WP Read Preflight Summary\n- Authenticated WP read GET succeeded: true\n", "summary response body saved mismatch"),
        ("# LS-NEW-12 Authenticated WP Read Preflight Summary\n- Authenticated WP read GET succeeded: true\n- Response body saved: false\n", "summary authenticated user identity saved mismatch"),
        ("# LS-NEW-12 Authenticated WP Read Preflight Summary\n- Authenticated WP read GET succeeded: true\n- Response body saved: false\n- Authenticated user identity saved: false\n", "summary authorization header output mismatch"),
    ],
)
def test_summary_text_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["summary"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_code_no_forbidden_output_patterns() -> None:
    src = Path("scripts/validate_start_ls_new12_authenticated_wp_read_preflight.py").read_text(encoding="utf-8")
    forbidden = [
        "print(credential",
        "print(password",
        "print(secret",
        "print(Authorization",
        "print(Basic",
        "logger.credential",
        "logger.password",
        "logger.secret",
        "response.read().write",
    ]
    assert all(x not in src for x in forbidden)
