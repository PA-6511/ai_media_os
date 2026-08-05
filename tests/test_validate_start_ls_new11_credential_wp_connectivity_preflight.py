from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-11"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-11"}


def _base_manifest() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_CREDENTIAL_PREFLIGHT_MANIFEST",
        "status": "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_READY_NO_WRITE",
        "execution_mode": "CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE",
        "production_status": "NO_WRITE_CONNECTIVITY_PREFLIGHT_ONLY",
        "ls_new10_validated": True,
        "ls_new10_ready": True,
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
        "required_url_key_present": True,
        "required_username_key_present": True,
        "required_app_password_key_present": True,
        "required_url_value_nonempty": True,
        "required_username_value_nonempty": True,
        "required_app_password_value_nonempty": True,
        "credential_presence_summary_created": True,
        "wp_connectivity_preflight_result_created": True,
        "no_write_safety_contract_created": True,
        "next_phase_handoff_created": True,
        "preflight_summary_created": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_rest_index_get_attempted": True,
        "wordpress_rest_index_get_succeeded": True,
        "wordpress_rest_index_status_class": "2xx",
        "wordpress_rest_response_body_saved": False,
        "wordpress_authenticated_get_executed": False,
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
        "credential_values_saved": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "ready_for_ls_new_12": True,
        "recommended_next_action": "BEGIN_LS_NEW_12_AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE",
        "recommended_next_phase_options": ["LS-NEW-12", "LS-MON-2"],
        "errors": [],
    }


def _base_credential_summary() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_CREDENTIAL_PRESENCE_SUMMARY",
        "status": "LSNEW11_CREDENTIAL_PRESENCE_SUMMARY_READY_NO_SECRET_OUTPUT",
        "credential_env_exists": True,
        "credential_existence_check_executed": True,
        "credential_env_read_executed": True,
        "required_url_key_present": True,
        "required_username_key_present": True,
        "required_app_password_key_present": True,
        "required_url_value_nonempty": True,
        "required_username_value_nonempty": True,
        "required_app_password_value_nonempty": True,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "credential_values_saved": False,
    }


def _base_wp_connectivity() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_WP_CONNECTIVITY_PREFLIGHT_RESULT",
        "status": "LSNEW11_WP_REST_CONNECTIVITY_READY_NO_WRITE",
        "wordpress_rest_index_get_attempted": True,
        "wordpress_rest_index_get_succeeded": True,
        "wordpress_rest_index_status_class": "2xx",
        "wordpress_rest_response_body_saved": False,
        "wordpress_authenticated_get_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "execution_allowed": False,
    }


def _base_contract() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_NO_WRITE_SAFETY_CONTRACT",
        "status": "LSNEW11_NO_WRITE_SAFETY_CONTRACT_READY",
        "no_write_required": True,
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


def _base_handoff() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_NEXT_PHASE_HANDOFF",
        "status": "LSNEW11_NEXT_PHASE_HANDOFF_READY",
        "next_phase": "LS-NEW-12",
        "next_phase_name": "Authenticated WP Read Preflight / No Write",
        "handoff_ready": True,
        "ready_for_ls_new_12": True,
        "notes": ["n1", "n2"],
    }


def _base_result() -> dict:
    d = _base_manifest().copy()
    d["document_type"] = "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_RESULT"
    return d


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_LOCK",
        "status": "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_LOCKED_NO_WRITE",
        "locked": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_authenticated_get_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls10_validation() -> dict:
    return {"validation_status": "LSNEW10_EXECUTION_PREP_VALIDATED_NO_DRAFT_CREATION"}


def _base_summary_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-11 Credential and WP Connectivity Preflight Summary",
            "- Credential values output: false",
            "- Authorization header output: false",
            "- WordPress REST index GET succeeded: true",
            "- Ready for LS-NEW-12: true",
            "",
        ]
    )


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "credential_summary": tmp_path / "in/credential_summary.json",
        "wp_connectivity": tmp_path / "in/wp_connectivity.json",
        "contract": tmp_path / "in/contract.json",
        "handoff": tmp_path / "in/handoff.json",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "run_result": tmp_path / "in/run_result.json",
        "lock": tmp_path / "in/lock.json",
        "ls10_validation": tmp_path / "in/ls10_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["credential_summary"], _base_credential_summary())
    _write_json(p["wp_connectivity"], _base_wp_connectivity())
    _write_json(p["contract"], _base_contract())
    _write_json(p["handoff"], _base_handoff())
    p["summary"].write_text(_base_summary_text(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls10_validation"], _base_ls10_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new11_credential_wp_connectivity_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--credential-summary",
        str(p["credential_summary"]),
        "--wp-connectivity-result",
        str(p["wp_connectivity"]),
        "--no-write-safety-contract",
        str(p["contract"]),
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
        "--ls-new10-validation-result",
        str(p["ls10_validation"]),
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
    assert out["validation_status"] == "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "manifest",
        "credential_summary",
        "wp_connectivity",
        "contract",
        "handoff",
        "summary",
        "result",
        "run_result",
        "lock",
        "ls10_validation",
    ],
)
def test_missing_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls10_validation", "validation_status", "BAD", "ls-new10 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new10_validated", False, "manifest ls_new10_validated mismatch"),
        ("manifest", "ls_new10_ready", False, "manifest ls_new10_ready mismatch"),
        ("manifest", "credential_env_exists", False, "manifest credential_env_exists mismatch"),
        ("manifest", "credential_existence_check_executed", False, "manifest credential_existence_check_executed mismatch"),
        ("manifest", "credential_env_read_executed", False, "manifest credential_env_read_executed mismatch"),
        ("manifest", "required_url_key_present", False, "manifest required_url_key_present mismatch"),
        ("manifest", "required_username_key_present", False, "manifest required_username_key_present mismatch"),
        ("manifest", "required_app_password_key_present", False, "manifest required_app_password_key_present mismatch"),
        ("manifest", "required_url_value_nonempty", False, "manifest required_url_value_nonempty mismatch"),
        ("manifest", "required_username_value_nonempty", False, "manifest required_username_value_nonempty mismatch"),
        ("manifest", "required_app_password_value_nonempty", False, "manifest required_app_password_value_nonempty mismatch"),
        ("manifest", "wordpress_rest_index_get_attempted", False, "manifest wordpress_rest_index_get_attempted mismatch"),
        ("manifest", "wordpress_rest_index_get_succeeded", False, "manifest wordpress_rest_index_get_succeeded mismatch"),
        ("manifest", "wordpress_rest_index_status_class", "4xx", "manifest wordpress_rest_index_status_class mismatch"),
        ("manifest", "wordpress_rest_response_body_saved", True, "manifest wordpress_rest_response_body_saved=true"),
        ("credential_summary", "phase", "BAD", "credential-summary phase mismatch"),
        ("credential_summary", "document_type", "BAD", "credential-summary document_type mismatch"),
        ("credential_summary", "status", "BAD", "credential-summary status mismatch"),
        ("wp_connectivity", "phase", "BAD", "wp-connectivity phase mismatch"),
        ("wp_connectivity", "document_type", "BAD", "wp-connectivity document_type mismatch"),
        ("wp_connectivity", "status", "BAD", "wp-connectivity status mismatch"),
        ("wp_connectivity", "wordpress_rest_index_get_attempted", False, "wp-connectivity wordpress_rest_index_get_attempted mismatch"),
        ("wp_connectivity", "wordpress_rest_index_get_succeeded", False, "wp-connectivity wordpress_rest_index_get_succeeded mismatch"),
        ("wp_connectivity", "wordpress_rest_index_status_class", "NETWORK_ERROR", "wp-connectivity wordpress_rest_index_status_class mismatch"),
        ("wp_connectivity", "wordpress_rest_response_body_saved", True, "wp-connectivity wordpress_rest_response_body_saved=true"),
        ("contract", "phase", "BAD", "no-write-contract phase mismatch"),
        ("contract", "document_type", "BAD", "no-write-contract document_type mismatch"),
        ("contract", "status", "BAD", "no-write-contract status mismatch"),
        ("contract", "no_write_required", False, "no-write-contract no_write_required mismatch"),
        ("handoff", "phase", "BAD", "handoff phase mismatch"),
        ("handoff", "document_type", "BAD", "handoff document_type mismatch"),
        ("handoff", "status", "BAD", "handoff status mismatch"),
        ("handoff", "next_phase", "BAD", "handoff next_phase mismatch"),
        ("handoff", "next_phase_name", "BAD", "handoff next_phase_name mismatch"),
        ("handoff", "handoff_ready", False, "handoff handoff_ready mismatch"),
        ("handoff", "ready_for_ls_new_12", False, "handoff ready_for_ls_new_12 mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new10_validated", False, "result ls_new10_validated mismatch"),
        ("result", "ls_new10_ready", False, "result ls_new10_ready mismatch"),
        ("result", "credential_env_exists", False, "result credential_env_exists mismatch"),
        ("result", "credential_existence_check_executed", False, "result credential_existence_check_executed mismatch"),
        ("result", "credential_env_read_executed", False, "result credential_env_read_executed mismatch"),
        ("result", "required_url_key_present", False, "result required_url_key_present mismatch"),
        ("result", "required_username_key_present", False, "result required_username_key_present mismatch"),
        ("result", "required_app_password_key_present", False, "result required_app_password_key_present mismatch"),
        ("result", "required_url_value_nonempty", False, "result required_url_value_nonempty mismatch"),
        ("result", "required_username_value_nonempty", False, "result required_username_value_nonempty mismatch"),
        ("result", "required_app_password_value_nonempty", False, "result required_app_password_value_nonempty mismatch"),
        ("result", "wordpress_rest_index_get_attempted", False, "result wordpress_rest_index_get_attempted mismatch"),
        ("result", "wordpress_rest_index_get_succeeded", False, "result wordpress_rest_index_get_succeeded mismatch"),
        ("result", "wordpress_rest_index_status_class", "4xx", "result wordpress_rest_index_status_class mismatch"),
        ("result", "wordpress_rest_response_body_saved", True, "result wordpress_rest_response_body_saved=true"),
        ("result", "ready_for_ls_new_12", False, "result ready_for_ls_new_12 mismatch"),
        ("result", "recommended_next_action", "BAD", "result recommended_next_action mismatch"),
        ("result", "target_post_id", 1, "result target_post_id must be null"),
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
        ("wordpress_write_executed", "result wordpress_write_executed=true"),
        ("wordpress_draft_created", "result wordpress_draft_created=true"),
        ("wordpress_publish_executed", "result wordpress_publish_executed=true"),
        ("wordpress_update_executed", "result wordpress_update_executed=true"),
        ("wordpress_delete_executed", "result wordpress_delete_executed=true"),
        ("wordpress_authenticated_get_executed", "result wordpress_authenticated_get_executed=true"),
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
        ("credential_value_output", "credential-summary credential_value_output=true"),
        ("credential_secret_output", "credential-summary credential_secret_output=true"),
        ("credential_length_output", "credential-summary credential_length_output=true"),
        ("credential_hash_output", "credential-summary credential_hash_output=true"),
        ("authorization_header_output", "credential-summary authorization_header_output=true"),
        ("basic_auth_output", "credential-summary basic_auth_output=true"),
        ("base64_auth_output", "credential-summary base64_auth_output=true"),
        ("credential_values_saved", "credential-summary credential_values_saved=true"),
    ],
)
def test_credential_summary_secret_true_detections(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["credential_summary"])
    d[key] = True
    _write_json(p["credential_summary"], d)
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
        ("wordpress_authenticated_get_executed", "lock wordpress_authenticated_get_executed=true"),
        ("credential_value_output", "lock credential_value_output=true"),
        ("credential_secret_output", "lock credential_secret_output=true"),
        ("credential_length_output", "lock credential_length_output=true"),
        ("credential_hash_output", "lock credential_hash_output=true"),
        ("authorization_header_output", "lock authorization_header_output=true"),
        ("basic_auth_output", "lock basic_auth_output=true"),
        ("base64_auth_output", "lock base64_auth_output=true"),
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
        ("# LS-NEW-11 Credential and WP Connectivity Preflight Summary\n", "summary credential values output mismatch"),
        ("# LS-NEW-11 Credential and WP Connectivity Preflight Summary\n- Credential values output: false\n", "summary authorization header output mismatch"),
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
    src = Path("scripts/validate_start_ls_new11_credential_wp_connectivity_preflight.py").read_text(encoding="utf-8")
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