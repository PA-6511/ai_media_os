from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-10"}


def _base_manifest() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_MANIFEST",
        "status": "LSNEW10_EXECUTION_PREP_READY_NO_DRAFT_CREATION",
        "execution_mode": "EXECUTION_PREP_ONLY_NO_DRAFT_CREATION",
        "production_status": "NO_EXECUTION_EXECUTION_PREP_ONLY",
        "ls_new9_decision_validated": True,
        "ls_new9_decision_approved": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_prep_manifest_created": True,
        "execution_input_map_created": True,
        "draft_creation_dry_boundary_created": True,
        "credential_preflight_handoff_request_created": True,
        "blocked_execution_command_template_created": True,
        "execution_prep_safety_summary_created": True,
        "execution_prep_summary_created": True,
        "execution_allowed": False,
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
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "ready_for_ls_new_11": True,
        "recommended_next_action": "BEGIN_LS_NEW_11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE",
        "recommended_next_phase_options": ["LS-NEW-11", "LS-MON-2"],
        "errors": [],
    }


def _base_input_map() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_INPUT_MAP",
        "status": "LSNEW10_EXECUTION_INPUT_MAP_READY_NO_DRAFT_CREATION",
        "credential_source": None,
        "credential_env_path_recorded": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_allowed": False,
    }


def _base_dry_boundary() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_DRAFT_CREATION_DRY_BOUNDARY",
        "status": "LSNEW10_DRAFT_CREATION_DRY_BOUNDARY_READY_NO_DRAFT_CREATION",
        "draft_creation_planned_for_later_phase": True,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_allowed": False,
    }


def _base_credential_handoff() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST",
        "status": "LSNEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST_READY_NO_CREDENTIAL_READ",
        "next_phase": "LS-NEW-11",
        "next_phase_name": "Credential and WordPress Connectivity Preflight",
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "execution_allowed": False,
        "handoff_ready": True,
    }


def _base_safety_summary() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_SAFETY_SUMMARY",
        "status": "LSNEW10_EXECUTION_PREP_SAFETY_SUMMARY_READY_NO_DRAFT_CREATION",
        "execution_allowed": False,
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
        "target_post_id": None,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "ready_for_ls_new_11": True,
    }


def _base_result() -> dict:
    d = _base_manifest().copy()
    d["document_type"] = "START_LS_NEW10_EXECUTION_PREP_RESULT"
    return d


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_LOCK",
        "status": "LSNEW10_EXECUTION_PREP_LOCKED_NO_DRAFT_CREATION",
        "locked": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "approval_label_consumed": False,
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


def _base_ls9_validation() -> dict:
    return {"validation_status": "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"}


def _blocked_template() -> str:
    return "\n".join(
        [
            "# LS-NEW-10 Blocked Execution Command Template",
            "",
            "This is not an executable command.",
            "- Execution allowed: false",
            "- WordPress draft creation allowed: false",
            "",
        ]
    )


def _summary_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-10 Execution Prep Summary",
            "",
            "- Ready for LS-NEW-11: true",
            "LS-NEW-10 は実行系準備のみであり、WordPress下書き作成・credential読込・WordPress API呼び出しは実行しない。",
            "",
        ]
    )


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "input_map": tmp_path / "in/input_map.json",
        "dry": tmp_path / "in/dry.json",
        "handoff": tmp_path / "in/handoff.json",
        "safety": tmp_path / "in/safety.json",
        "summary": tmp_path / "in/summary.md",
        "blocked": tmp_path / "in/blocked.md",
        "result": tmp_path / "in/result.json",
        "run_result": tmp_path / "in/run_result.json",
        "lock": tmp_path / "in/lock.json",
        "ls9_validation": tmp_path / "in/ls9_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["input_map"], _base_input_map())
    _write_json(p["dry"], _base_dry_boundary())
    _write_json(p["handoff"], _base_credential_handoff())
    _write_json(p["safety"], _base_safety_summary())
    p["summary"].write_text(_summary_text(), encoding="utf-8")
    p["blocked"].write_text(_blocked_template(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls9_validation"], _base_ls9_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new10_execution_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--input-map",
        str(p["input_map"]),
        "--dry-boundary",
        str(p["dry"]),
        "--credential-handoff",
        str(p["handoff"]),
        "--blocked-command-template",
        str(p["blocked"]),
        "--safety-summary",
        str(p["safety"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new9-decision-validation-result",
        str(p["ls9_validation"]),
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
    assert out["validation_status"] == "LSNEW10_EXECUTION_PREP_VALIDATED_NO_DRAFT_CREATION"


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "manifest",
        "input_map",
        "dry",
        "handoff",
        "safety",
        "summary",
        "blocked",
        "result",
        "run_result",
        "lock",
        "ls9_validation",
    ],
)
def test_missing_inputs_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW10_EXECUTION_PREP_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls9_validation", "validation_status", "BAD", "ls-new9 decision validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new9_decision_validated", False, "manifest ls_new9_decision_validated mismatch"),
        ("manifest", "ls_new9_decision_approved", False, "manifest ls_new9_decision_approved mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new9_decision_validated", False, "result ls_new9_decision_validated mismatch"),
        ("result", "ls_new9_decision_approved", False, "result ls_new9_decision_approved mismatch"),
        ("result", "ready_for_ls_new_11", False, "result ready_for_ls_new_11 mismatch"),
        ("result", "recommended_next_action", "BAD", "result recommended_next_action mismatch"),
        ("result", "content_item_id", "bad", "result content_item_id mismatch"),
        ("result", "title", "bad", "result title mismatch"),
        ("result", "volume", "bad", "result volume mismatch"),
        ("result", "author", "bad", "result author mismatch"),
        ("result", "publisher", "bad", "result publisher mismatch"),
        ("result", "release_date", "bad", "result release_date mismatch"),
        ("result", "post_status_target", "publish", "result post_status_target mismatch"),
        ("result", "target_post_id", 10, "result target_post_id must be null"),
        ("input_map", "phase", "BAD", "input-map phase mismatch"),
        ("input_map", "document_type", "BAD", "input-map document_type mismatch"),
        ("input_map", "status", "BAD", "input-map status mismatch"),
        ("input_map", "credential_source", "x", "input-map credential_source must be null"),
        ("dry", "phase", "BAD", "dry-boundary phase mismatch"),
        ("dry", "document_type", "BAD", "dry-boundary document_type mismatch"),
        ("dry", "status", "BAD", "dry-boundary status mismatch"),
        ("handoff", "phase", "BAD", "credential-handoff phase mismatch"),
        ("handoff", "document_type", "BAD", "credential-handoff document_type mismatch"),
        ("handoff", "status", "BAD", "credential-handoff status mismatch"),
        ("handoff", "next_phase", "BAD", "credential-handoff next_phase mismatch"),
        ("handoff", "next_phase_name", "BAD", "credential-handoff next_phase_name mismatch"),
        ("safety", "phase", "BAD", "safety-summary phase mismatch"),
        ("safety", "document_type", "BAD", "safety-summary document_type mismatch"),
        ("safety", "status", "BAD", "safety-summary status mismatch"),
        ("safety", "ready_for_ls_new_11", False, "safety-summary ready_for_ls_new_11 mismatch"),
        ("lock", "phase", "BAD", "lock phase mismatch"),
        ("lock", "document_type", "BAD", "lock document_type mismatch"),
        ("lock", "status", "BAD", "lock status mismatch"),
        ("lock", "locked", False, "lock mismatch"),
    ],
)
def test_structure_constraints(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    if target in ("summary", "blocked"):
        pytest.skip("text files handled separately")
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
        ("execution_allowed", "result execution_allowed=true"),
        ("runner_execution_allowed", "result runner_execution_allowed=true"),
        ("final_execution_command_created", "result final_execution_command_created=true"),
        ("wordpress_api_call_executed", "result wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "result wordpress_write_executed=true"),
        ("wordpress_draft_created", "result wordpress_draft_created=true"),
        ("wordpress_publish_executed", "result wordpress_publish_executed=true"),
        ("x_api_call_executed", "result x_api_call_executed=true"),
        ("x_post_executed", "result x_post_executed=true"),
        ("external_fetch_executed", "result external_fetch_executed=true"),
        ("http_get_executed", "result http_get_executed=true"),
        ("credential_env_read_executed", "result credential_env_read_executed=true"),
        ("credential_existence_check_executed", "result credential_existence_check_executed=true"),
        ("credential_value_output", "result credential_value_output=true"),
        ("credential_secret_output", "result credential_secret_output=true"),
        ("secret_length_output", "result secret_length_output=true"),
        ("secret_hash_output", "result secret_hash_output=true"),
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
        ("execution_allowed", "lock execution_allowed=true"),
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("approval_label_consumed", "lock approval_label_consumed=true"),
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
    "which,new_text,error",
    [
        ("blocked", "", "blocked command template missing non-executable statement"),
        ("blocked", "This is not an executable command.\n", "blocked command template missing execution allowed false"),
        ("summary", "", "summary header mismatch"),
        ("summary", "# LS-NEW-10 Execution Prep Summary\n", "summary ready_for_ls_new_11 mismatch"),
    ],
)
def test_text_file_constraints(tmp_path: Path, which: str, new_text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p[which].write_text(new_text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new10_execution_prep.py").read_text(encoding="utf-8")
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