from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-7"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-7"}


def _base_manifest() -> dict:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_MANIFEST",
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_MANIFEST_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_PREP_ONLY",
        "ls_new6_validated": True,
        "source_payload": "exchange/new_release/start_ls_new6_wp_draft_payload_prep.json",
        "source_preview": "exchange/new_release/start_ls_new6_wp_draft_payload_preview.md",
        "source_safety_summary": "exchange/new_release/start_ls_new6_wp_draft_payload_safety_summary.json",
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "runner_prep_manifest_created": True,
        "runner_safety_contract_created": True,
        "runner_preflight_checklist_created": True,
        "blocked_execution_command_template_created": True,
        "runner_execution_allowed": False,
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
        "ready_for_ls_new_8": True,
        "recommended_next_action": "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-8", "LS-MON-2"],
        "errors": [],
    }


def _base_safety_contract() -> dict:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT",
        "status": "LSNEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT_READY_NO_EXECUTION",
        "runner_execution_allowed": False,
        "blocked_until_explicit_approval": True,
        "separate_execution_command_required": True,
        "final_preflight_required": True,
        "human_approval_required_before_any_wp_call": True,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_draft_create_allowed": False,
        "credential_env_read_allowed": False,
        "target_post_id_allocation_allowed": False,
        "approval_label_consumption_allowed": False,
        "execution_allowed": False,
        "always_forbidden": [
            "post_id=119 update",
            "post_id=183 update",
            "secret output",
            "credential.env read in LS-NEW-7",
            "WordPress API call in LS-NEW-7",
            "WordPress draft creation in LS-NEW-7",
            "X post in LS-NEW-7",
            "external fetch in LS-NEW-7",
        ],
    }


def _base_preflight() -> dict:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREFLIGHT_CHECKLIST",
        "status": "LSNEW7_PREFLIGHT_CHECKLIST_READY_NO_EXECUTION",
        "required_before_later_execution": [
            "LS-NEW-6 payload validation remains valid",
            "human approval remains valid",
            "final preflight completed in later phase",
            "credential readiness checked only in later approved phase",
            "target post ID remains unallocated until actual draft creation phase",
            "separate execution command approved in later phase",
            "rollback/freeze boundary prepared in later phase",
        ],
        "current_phase_checks": {
            "runner_execution_allowed": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "credential_env_read_executed": False,
            "target_post_id_allocated": False,
            "execution_allowed": False,
        },
    }


def _base_command_template() -> str:
    return "\n".join(
        [
            "# LS-NEW-7 Blocked Execution Command Template",
            "",
            "This is not an executable command.",
            "This file documents that execution is blocked in LS-NEW-7.",
            "",
            "- Phase: LS-NEW-7",
            "- Runner execution allowed: false",
            "- WordPress API allowed: false",
            "- WordPress draft creation allowed: false",
            "- Credential read allowed: false",
            "- Target post ID allocation allowed: false",
            "- Execution allowed: false",
            "",
            "Actual execution must not be attempted in LS-NEW-7.",
            "A later phase must create a separate approved execution command after final preflight.",
            "",
        ]
    )


def _base_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-7 WordPress Draft Runner Prep Summary",
            "",
            "- Phase: LS-NEW-7",
            "- Status: READY_NO_EXECUTION",
            "- Runner execution allowed: false",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Source payload: exchange/new_release/start_ls_new6_wp_draft_payload_prep.json",
            "",
        ]
    )


def _base_result() -> dict:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_RESULT",
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_PREP_ONLY",
        "ls_new6_validated": True,
        "runner_prep_manifest_created": True,
        "runner_safety_contract_created": True,
        "runner_preflight_checklist_created": True,
        "blocked_execution_command_template_created": True,
        "runner_prep_summary_created": True,
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
        "ready_for_ls_new_8": True,
        "recommended_next_action": "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-8", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_LOCK",
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_LOCKED_NO_EXECUTION",
        "locked": True,
        "runner_execution_allowed": False,
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


def _base_ls6_validation() -> dict:
    return {"validation_status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "manifest": tmp_path / "in/manifest.json",
        "safety_contract": tmp_path / "in/safety_contract.json",
        "preflight": tmp_path / "in/preflight.json",
        "command": tmp_path / "in/command.md",
        "summary": tmp_path / "in/summary.md",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls6_validation": tmp_path / "in/ls6_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["manifest"], _base_manifest())
    _write_json(p["safety_contract"], _base_safety_contract())
    _write_json(p["preflight"], _base_preflight())
    p["command"].parent.mkdir(parents=True, exist_ok=True)
    p["command"].write_text(_base_command_template(), encoding="utf-8")
    p["summary"].parent.mkdir(parents=True, exist_ok=True)
    p["summary"].write_text(_base_summary(), encoding="utf-8")
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls6_validation"], _base_ls6_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new7_wp_draft_runner_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--manifest",
        str(p["manifest"]),
        "--safety-contract",
        str(p["safety_contract"]),
        "--preflight-checklist",
        str(p["preflight"]),
        "--command-template",
        str(p["command"]),
        "--summary",
        str(p["summary"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new6-validation-result",
        str(p["ls6_validation"]),
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
    assert out["validation_status"] == "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "path_key",
    ["policy", "schema", "manifest", "safety_contract", "preflight", "command", "summary", "result", "lock", "run_result", "ls6_validation"],
)
def test_missing_files(path_key: str, tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p[path_key].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW7_WP_DRAFT_RUNNER_PREP_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls6_validation", "validation_status", "BAD", "ls-new6 validation status mismatch"),
        ("manifest", "phase", "BAD", "manifest phase mismatch"),
        ("manifest", "document_type", "BAD", "manifest document_type mismatch"),
        ("manifest", "status", "BAD", "manifest status mismatch"),
        ("manifest", "execution_mode", "BAD", "manifest execution_mode mismatch"),
        ("manifest", "production_status", "BAD", "manifest production_status mismatch"),
        ("manifest", "ls_new6_validated", False, "manifest ls_new6_validated mismatch"),
        ("manifest", "runner_prep_manifest_created", False, "manifest created flag mismatch"),
        ("manifest", "runner_safety_contract_created", False, "manifest safety flag mismatch"),
        ("manifest", "runner_preflight_checklist_created", False, "manifest checklist flag mismatch"),
        ("manifest", "blocked_execution_command_template_created", False, "manifest command template flag mismatch"),
        ("manifest", "target_post_id", 10, "manifest target_post_id must be null"),
        ("manifest", "ready_for_ls_new_8", False, "manifest ready_for_ls_new_8=false"),
        ("manifest", "recommended_next_action", "BAD", "manifest recommended_next_action mismatch"),
        ("safety_contract", "phase", "BAD", "safety contract phase mismatch"),
        ("safety_contract", "document_type", "BAD", "safety contract document_type mismatch"),
        ("safety_contract", "status", "BAD", "safety contract status mismatch"),
        ("safety_contract", "runner_execution_allowed", True, "runner_execution_allowed=true"),
        ("safety_contract", "separate_execution_command_required", False, "separate_execution_command_required mismatch"),
        ("safety_contract", "final_preflight_required", False, "final_preflight_required mismatch"),
        ("safety_contract", "wordpress_api_call_allowed", True, "wordpress_api_call_allowed=true"),
        ("safety_contract", "execution_allowed", True, "safety contract execution_allowed=true"),
        ("preflight", "phase", "BAD", "preflight phase mismatch"),
        ("preflight", "document_type", "BAD", "preflight document_type mismatch"),
        ("preflight", "status", "BAD", "preflight status mismatch"),
        ("result", "phase", "BAD", "result phase mismatch"),
        ("result", "document_type", "BAD", "result document_type mismatch"),
        ("result", "status", "BAD", "result status mismatch"),
        ("result", "execution_mode", "BAD", "result execution_mode mismatch"),
        ("result", "production_status", "BAD", "result production_status mismatch"),
        ("result", "ls_new6_validated", False, "result ls_new6_validated mismatch"),
        ("result", "runner_prep_manifest_created", False, "result runner_prep_manifest_created mismatch"),
        ("result", "runner_safety_contract_created", False, "result runner_safety_contract_created mismatch"),
        ("result", "runner_preflight_checklist_created", False, "result runner_preflight_checklist_created mismatch"),
        ("result", "blocked_execution_command_template_created", False, "result blocked_execution_command_template_created mismatch"),
        ("result", "runner_prep_summary_created", False, "result runner_prep_summary_created mismatch"),
        ("result", "target_post_id", 1, "result target_post_id must be null"),
        ("result", "ready_for_ls_new_8", False, "ready_for_ls_new_8=false"),
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
        ("bad", "command template header mismatch"),
        (
            "# LS-NEW-7 Blocked Execution Command Template\n",
            "command template missing line: This is not an executable command.",
        ),
    ],
)
def test_command_template_checks(tmp_path: Path, text: str, error: str) -> None:
    p = _prepare(tmp_path)
    p["command"].write_text(text, encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "text,error",
    [
        ("bad", "summary header mismatch"),
        (
            "# LS-NEW-7 WordPress Draft Runner Prep Summary\n",
            "summary missing line: - Phase: LS-NEW-7",
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


def test_preflight_missing_required_line(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    pr = _load(p["preflight"])
    pr["required_before_later_execution"] = ["x"]
    _write_json(p["preflight"], pr)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "preflight missing final preflight item" in out["errors"]


@pytest.mark.parametrize(
    "key",
    [
        "runner_execution_allowed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "credential_env_read_executed",
        "target_post_id_allocated",
        "execution_allowed",
    ],
)
def test_preflight_current_checks_false(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    pr = _load(p["preflight"])
    pr["current_phase_checks"][key] = True
    _write_json(p["preflight"], pr)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert f"preflight current_phase_checks {key}=true" in out["errors"]


@pytest.mark.parametrize(
    "item,error",
    [
        ("post_id=119 update", "safety contract missing forbidden item: post_id=119 update"),
        ("post_id=183 update", "safety contract missing forbidden item: post_id=183 update"),
        ("WordPress API call in LS-NEW-7", "safety contract missing forbidden item: WordPress API call in LS-NEW-7"),
        (
            "WordPress draft creation in LS-NEW-7",
            "safety contract missing forbidden item: WordPress draft creation in LS-NEW-7",
        ),
        ("external fetch in LS-NEW-7", "safety contract missing forbidden item: external fetch in LS-NEW-7"),
    ],
)
def test_safety_contract_forbidden_list(tmp_path: Path, item: str, error: str) -> None:
    p = _prepare(tmp_path)
    sc = _load(p["safety_contract"])
    sc["always_forbidden"] = [x for x in sc["always_forbidden"] if x != item]
    _write_json(p["safety_contract"], sc)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new7_wp_draft_runner_prep.py").read_text(encoding="utf-8")
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
