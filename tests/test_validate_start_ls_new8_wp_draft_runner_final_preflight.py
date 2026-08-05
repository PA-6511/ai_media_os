from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-8"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-8"}


def _base_manifest() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_FINAL_PREFLIGHT_MANIFEST",
        "status": "LSNEW8_FINAL_PREFLIGHT_MANIFEST_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY",
        "ls_new7_validated": True,
        "source_manifest": "exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json",
        "source_safety_contract": "exchange/new_release/start_ls_new7_wp_draft_runner_safety_contract.json",
        "source_preflight_checklist": "exchange/new_release/start_ls_new7_wp_draft_runner_preflight_checklist.json",
        "source_blocked_execution_command_template": "exchange/new_release/start_ls_new7_blocked_execution_command_template.md",
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "final_preflight_manifest_created": True,
        "freeze_boundary_created": True,
        "rollback_boundary_created": True,
        "abort_conditions_created": True,
        "next_approval_gate_handoff_created": True,
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
        "execution_allowed": False,
        "ready_for_ls_new_9": True,
        "recommended_next_action": "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-9", "LS-MON-2"],
        "errors": [],
    }


def _base_freeze() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_FREEZE_BOUNDARY",
        "status": "LSNEW8_FREEZE_BOUNDARY_READY_NO_EXECUTION",
        "freeze_required_before_later_execution": True,
        "freeze_scope": [
            "LS-NEW-6 WP draft payload prep",
            "LS-NEW-7 runner prep manifest",
            "LS-NEW-7 safety contract",
            "LS-NEW-8 final preflight manifest",
        ],
        "frozen_in_current_phase": False,
        "freeze_execution_allowed": False,
        "execution_allowed": False,
    }


def _base_rollback() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_ROLLBACK_BOUNDARY",
        "status": "LSNEW8_ROLLBACK_BOUNDARY_READY_NO_EXECUTION",
        "rollback_required_before_later_execution": True,
        "rollback_scope": [
            "If a later draft creation succeeds, rollback means moving the created draft to trash or reverting to draft-hold according to later approved policy.",
            "No rollback action is executed in LS-NEW-8 because no WordPress draft exists yet.",
        ],
        "target_post_id": None,
        "rollback_executed": False,
        "execution_allowed": False,
    }


def _base_abort() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_ABORT_CONDITIONS",
        "status": "LSNEW8_ABORT_CONDITIONS_READY_NO_EXECUTION",
        "abort_if_any_true": [
            "LS-NEW-7 validation is not valid",
            "target_post_id is not null before draft creation",
            "target_post_id_allocated is true before draft creation",
            "execution_allowed is true in any pre-execution artifact",
            "runner_execution_allowed is true before explicit execution approval",
            "credential.env was read before later approved credential phase",
            "WordPress API was called before later approved execution phase",
            "post_id=119 update is attempted",
            "post_id=183 update is attempted",
            "approval label is consumed before execution gate",
            "external fetch is attempted",
        ],
        "abort_triggered": False,
        "execution_allowed": False,
    }


def _base_handoff() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_NEXT_APPROVAL_GATE_HANDOFF",
        "status": "LSNEW8_NEXT_APPROVAL_GATE_HANDOFF_READY_NO_EXECUTION",
        "next_phase": "LS-NEW-9",
        "next_phase_name": "Separate Execution Approval Gate",
        "required_future_approval_label": "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
        "handoff_ready": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_draft_create_allowed": False,
        "credential_env_read_allowed": False,
    }


def _base_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-8 WordPress Draft Runner Final Preflight Summary",
            "",
            "- Phase: LS-NEW-8",
            "- Status: READY_NO_EXECUTION",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Credential existence check executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Ready for LS-NEW-9: true",
            "",
        ]
    )


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_RESULT",
        "status": "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY",
        "ls_new7_validated": True,
        "final_preflight_manifest_created": True,
        "freeze_boundary_created": True,
        "rollback_boundary_created": True,
        "abort_conditions_created": True,
        "next_approval_gate_handoff_created": True,
        "final_preflight_summary_created": True,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
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
        "execution_allowed": False,
        "abort_triggered": False,
        "handoff_ready": True,
        "ready_for_ls_new_9": True,
        "recommended_next_action": "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-9", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCK",
        "status": "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCKED_NO_EXECUTION",
        "locked": True,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "execution_allowed": False,
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


def _base_ls7_validation() -> dict:
    return {"validation_status": "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "freeze": tmp_path / "in/freeze.json",
        "rollback": tmp_path / "in/rollback.json",
        "abort": tmp_path / "in/abort.json",
        "handoff": tmp_path / "in/handoff.json",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls7_validation": tmp_path / "in/ls7_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["freeze"], _base_freeze())
    _write_json(p["rollback"], _base_rollback())
    _write_json(p["abort"], _base_abort())
    _write_json(p["handoff"], _base_handoff())
    p["summary"].parent.mkdir(parents=True, exist_ok=True)
    p["summary"].write_text(_base_summary(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls7_validation"], _base_ls7_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new8_wp_draft_runner_final_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--freeze-boundary",
        str(p["freeze"]),
        "--rollback-boundary",
        str(p["rollback"]),
        "--abort-conditions",
        str(p["abort"]),
        "--handoff",
        str(p["handoff"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new7-validation-result",
        str(p["ls7_validation"]),
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
    assert out["validation_status"] == "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "path_key",
    [
        "policy",
        "schema",
        "manifest",
        "freeze",
        "rollback",
        "abort",
        "handoff",
        "summary",
        "result",
        "lock",
        "run_result",
        "ls7_validation",
    ],
)
def test_missing_files(path_key: str, tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p[path_key].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls7_validation", "validation_status", "BAD", "ls-new7 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new7_validated", False, "manifest ls_new7_validated mismatch"),
        ("manifest", "final_preflight_manifest_created", False, "manifest final_preflight_manifest_created mismatch"),
        ("manifest", "freeze_boundary_created", False, "manifest freeze_boundary_created mismatch"),
        ("manifest", "rollback_boundary_created", False, "manifest rollback_boundary_created mismatch"),
        ("manifest", "abort_conditions_created", False, "manifest abort_conditions_created mismatch"),
        ("manifest", "next_approval_gate_handoff_created", False, "manifest next_approval_gate_handoff_created mismatch"),
        ("manifest", "target_post_id", 1, "manifest target_post_id must be null"),
        ("manifest", "ready_for_ls_new_9", False, "manifest ready_for_ls_new_9=false"),
        ("manifest", "recommended_next_action", "BAD", "manifest recommended_next_action mismatch"),
        ("freeze", "phase", "BAD", "freeze phase mismatch"),
        ("freeze", "document_type", "BAD", "freeze document_type mismatch"),
        ("freeze", "status", "BAD", "freeze status mismatch"),
        ("freeze", "freeze_required_before_later_execution", False, "freeze_required_before_later_execution mismatch"),
        ("freeze", "frozen_in_current_phase", True, "frozen_in_current_phase=true"),
        ("freeze", "freeze_execution_allowed", True, "freeze_execution_allowed=true"),
        ("freeze", "execution_allowed", True, "freeze execution_allowed=true"),
        ("rollback", "phase", "BAD", "rollback phase mismatch"),
        ("rollback", "document_type", "BAD", "rollback document_type mismatch"),
        ("rollback", "status", "BAD", "rollback status mismatch"),
        ("rollback", "rollback_required_before_later_execution", False, "rollback_required_before_later_execution mismatch"),
        ("rollback", "target_post_id", 3, "rollback target_post_id must be null"),
        ("rollback", "rollback_executed", True, "rollback_executed=true"),
        ("rollback", "execution_allowed", True, "rollback execution_allowed=true"),
        ("abort", "phase", "BAD", "abort phase mismatch"),
        ("abort", "document_type", "BAD", "abort document_type mismatch"),
        ("abort", "status", "BAD", "abort status mismatch"),
        ("abort", "abort_triggered", True, "abort_triggered=true"),
        ("abort", "execution_allowed", True, "abort execution_allowed=true"),
        ("handoff", "phase", "BAD", "handoff phase mismatch"),
        ("handoff", "document_type", "BAD", "handoff document_type mismatch"),
        ("handoff", "status", "BAD", "handoff status mismatch"),
        ("handoff", "next_phase", "BAD", "handoff next_phase mismatch"),
        ("handoff", "required_future_approval_label", "BAD", "handoff approval label mismatch"),
        ("handoff", "handoff_ready", False, "handoff_ready=false"),
        ("handoff", "execution_allowed", True, "handoff execution_allowed=true"),
        ("handoff", "runner_execution_allowed", True, "handoff runner_execution_allowed=true"),
        ("handoff", "wordpress_api_call_allowed", True, "handoff wordpress_api_call_allowed=true"),
        ("handoff", "wordpress_draft_create_allowed", True, "handoff wordpress_draft_create_allowed=true"),
        ("handoff", "credential_env_read_allowed", True, "handoff credential_env_read_allowed=true"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new7_validated", False, "result ls_new7_validated mismatch"),
        ("result", "final_preflight_manifest_created", False, "result final_preflight_manifest_created mismatch"),
        ("result", "freeze_boundary_created", False, "result freeze_boundary_created mismatch"),
        ("result", "rollback_boundary_created", False, "result rollback_boundary_created mismatch"),
        ("result", "abort_conditions_created", False, "result abort_conditions_created mismatch"),
        ("result", "next_approval_gate_handoff_created", False, "result next_approval_gate_handoff_created mismatch"),
        ("result", "final_preflight_summary_created", False, "result final_preflight_summary_created mismatch"),
        ("result", "target_post_id", 1, "result target_post_id must be null"),
        ("result", "abort_triggered", True, "result abort_triggered=true"),
        ("result", "handoff_ready", False, "result handoff_ready=false"),
        ("result", "ready_for_ls_new_9", False, "result ready_for_ls_new_9=false"),
        ("result", "recommended_next_action", "BAD", "result recommended_next_action mismatch"),
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
        ("runner_execution_allowed", "runner_execution_allowed=true"),
        ("final_execution_command_created", "final_execution_command_created=true"),
        ("wordpress_api_call_executed", "wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "wordpress_write_executed=true"),
        ("wordpress_draft_created", "wordpress_draft_created=true"),
        ("wordpress_publish_executed", "wordpress_publish_executed=true"),
        ("x_post_executed", "x_post_executed=true"),
        ("external_fetch_executed", "external_fetch_executed=true"),
        ("http_get_executed", "http_get_executed=true"),
        ("credential_env_read_executed", "credential_env_read_executed=true"),
        ("credential_existence_check_executed", "credential_existence_check_executed=true"),
        ("credential_secret_output", "credential_secret_output=true"),
        ("target_post_id_allocated", "target_post_id_allocated=true"),
        ("approval_label_consumed", "approval_label_consumed=true"),
        ("post119_update_executed", "post119_update_executed=true"),
        ("post183_update_executed", "post183_update_executed=true"),
        ("candidate_selected", "candidate_selected=true"),
        ("ls_next1_fill_updated", "ls_next1_fill_updated=true"),
        ("execution_allowed", "execution_allowed=true"),
    ],
)
def test_manifest_forbidden_true_detection(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    m = _load(p["manifest"])
    m[key] = True
    _write_json(p["manifest"], m)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
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
        ("approval_label_consumed", "result approval_label_consumed=true"),
        ("post119_update_executed", "result post119_update_executed=true"),
        ("post183_update_executed", "result post183_update_executed=true"),
        ("candidate_selected", "result candidate_selected=true"),
        ("ls_next1_fill_updated", "result ls_next1_fill_updated=true"),
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
        ("runner_execution_allowed", "lock runner_execution_allowed=true"),
        ("final_execution_command_created", "lock final_execution_command_created=true"),
        ("execution_allowed", "lock execution_allowed=true"),
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
        ("bad", "summary header mismatch"),
        (
            "# LS-NEW-8 WordPress Draft Runner Final Preflight Summary\n",
            "summary missing line: - Phase: LS-NEW-8",
        ),
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
    "scope,error",
    [
        (["x"], "freeze scope missing ls-new8 manifest"),
        ([], "freeze scope missing ls-new8 manifest"),
    ],
)
def test_freeze_scope_checks(tmp_path: Path, scope: list[str], error: str) -> None:
    p = _prepare(tmp_path)
    f = _load(p["freeze"])
    f["freeze_scope"] = scope
    _write_json(p["freeze"], f)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "item,error",
    [
        ("post_id=119 update is attempted", "abort conditions missing item: post_id=119 update is attempted"),
        ("post_id=183 update is attempted", "abort conditions missing item: post_id=183 update is attempted"),
        ("external fetch is attempted", "abort conditions missing item: external fetch is attempted"),
    ],
)
def test_abort_required_items(tmp_path: Path, item: str, error: str) -> None:
    p = _prepare(tmp_path)
    a = _load(p["abort"])
    a["abort_if_any_true"] = [x for x in a["abort_if_any_true"] if x != item]
    _write_json(p["abort"], a)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new8_wp_draft_runner_final_preflight.py").read_text(encoding="utf-8")
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
