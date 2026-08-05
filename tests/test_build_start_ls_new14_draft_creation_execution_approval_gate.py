from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

REQ_RUN = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION"
REQ_VALID = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict[str, Any]:
    return {"phase": "LS-NEW-14"}


def _base_schema() -> dict[str, Any]:
    return {"phase": "LS-NEW-14"}


def _base_ls13_result() -> dict[str, Any]:
    return {
        "status": REQ_RUN,
        "ready_for_ls_new_14": True,
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
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
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
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "approval_label_consumed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
    }


def _base_ls13_validation() -> dict[str, Any]:
    return {"validation_status": REQ_VALID}


def _base_ls13_manifest() -> dict[str, Any]:
    return {"phase": "LS-NEW-13"}


def _base_ls13_payload_map() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
    }


def _base_ls13_blocked() -> str:
    return "\n".join(
        [
            "# LS-NEW-13 Blocked Draft Creation Command Template",
            "This is not an executable command.",
            "Do not run a WordPress POST from LS-NEW-13.",
            "",
        ]
    )


def _base_ls13_one_shot() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
    }


def _base_ls13_checklist() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "all_required_checks_passed": True,
    }


def _base_ls13_contract() -> dict[str, Any]:
    return {"phase": "LS-NEW-13"}


def _base_ls13_handoff() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-13",
        "required_approval_label_next_phase": REQ_LABEL,
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls13_result": tmp_path / "in/ls13_result.json",
        "ls13_validation": tmp_path / "in/ls13_validation.json",
        "ls13_manifest": tmp_path / "in/ls13_manifest.json",
        "ls13_payload_map": tmp_path / "in/ls13_payload_map.json",
        "ls13_blocked": tmp_path / "in/ls13_blocked.md",
        "ls13_one_shot": tmp_path / "in/ls13_one_shot.json",
        "ls13_checklist": tmp_path / "in/ls13_checklist.json",
        "ls13_contract": tmp_path / "in/ls13_contract.json",
        "ls13_handoff": tmp_path / "in/ls13_handoff.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls13_result"], _base_ls13_result())
    _write_json(p["ls13_validation"], _base_ls13_validation())
    _write_json(p["ls13_manifest"], _base_ls13_manifest())
    _write_json(p["ls13_payload_map"], _base_ls13_payload_map())
    p["ls13_blocked"].write_text(_base_ls13_blocked(), encoding="utf-8")
    _write_json(p["ls13_one_shot"], _base_ls13_one_shot())
    _write_json(p["ls13_checklist"], _base_ls13_checklist())
    _write_json(p["ls13_contract"], _base_ls13_contract())
    _write_json(p["ls13_handoff"], _base_ls13_handoff())
    return p


def _all_flags() -> list[str]:
    return [
        "--require-no-auto-approval",
        "--require-no-ai-self-approval",
        "--require-no-approval-label-autofill",
        "--require-no-approval-label-consumption",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-wordpress-update",
        "--require-no-wordpress-delete",
        "--require-no-runner-execution",
        "--require-no-final-execution-command",
        "--require-no-actual-executable-command",
        "--require-no-shell-execution",
        "--require-no-credential-read",
        "--require-no-credential-value-output",
        "--require-no-credential-secret-output",
        "--require-no-credential-length-output",
        "--require-no-credential-hash-output",
        "--require-no-authorization-output",
        "--require-no-basic-auth-output",
        "--require-no-base64-auth-output",
        "--require-no-response-body-output",
        "--require-no-user-identity-output",
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-web-scraping",
        "--require-no-rss-fetch",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--require-no-rerun",
        "--require-no-publish-rerun",
        "--require-not-ready-for-ls-new15",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "approval_request": tmp_path / "out/approval_request.json",
        "approval_checklist": tmp_path / "out/approval_checklist.json",
        "decision_input_template": tmp_path / "out/decision_input_template.json",
        "initial_decision_record": tmp_path / "out/initial_decision_record.json",
        "approval_scope_summary": tmp_path / "out/approval_scope_summary.json",
        "approval_safety_summary": tmp_path / "out/approval_safety_summary.json",
        "decision_handoff": tmp_path / "out/decision_handoff.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new14_draft_creation_execution_approval_gate.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new13-result",
        str(p["ls13_result"]),
        "--ls-new13-validation-result",
        str(p["ls13_validation"]),
        "--ls-new13-manifest",
        str(p["ls13_manifest"]),
        "--ls-new13-payload-map",
        str(p["ls13_payload_map"]),
        "--ls-new13-blocked-command-template",
        str(p["ls13_blocked"]),
        "--ls-new13-one-shot-boundary",
        str(p["ls13_one_shot"]),
        "--ls-new13-pre-execution-checklist",
        str(p["ls13_checklist"]),
        "--ls-new13-no-execution-safety-contract",
        str(p["ls13_contract"]),
        "--ls-new13-next-phase-approval-handoff",
        str(p["ls13_handoff"]),
        "--output-manifest",
        str(out["manifest"]),
        "--output-approval-request",
        str(out["approval_request"]),
        "--output-approval-checklist",
        str(out["approval_checklist"]),
        "--output-decision-input-template",
        str(out["decision_input_template"]),
        "--output-initial-decision-record",
        str(out["initial_decision_record"]),
        "--output-approval-scope-summary",
        str(out["approval_scope_summary"]),
        "--output-approval-safety-summary",
        str(out["approval_safety_summary"]),
        "--output-decision-handoff",
        str(out["decision_handoff"]),
        "--output-summary",
        str(out["summary"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]
    cmd.extend(_all_flags() if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_build_success(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
    assert out["production_status"] == "WAITING_FOR_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_NO_EXECUTION"
    assert out["human_approval_required"] is True
    assert out["human_approval_completed"] is False
    assert out["human_approved_for_draft_creation"] is False


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "ls13_result",
        "ls13_validation",
        "ls13_manifest",
        "ls13_payload_map",
        "ls13_blocked",
        "ls13_one_shot",
        "ls13_checklist",
        "ls13_contract",
        "ls13_handoff",
    ],
)
def test_missing_inputs_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_FAILED_NO_EXECUTION"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls13_validation", "validation_status", "BAD", "ls-new13 validation status mismatch"),
        ("ls13_result", "status", "BAD", "ls-new13 run status mismatch"),
        ("ls13_result", "ready_for_ls_new_14", False, "ls-new13 ready_for_ls_new_14 mismatch"),
        ("ls13_result", "ls_new12_validated", False, "ls-new13 ls_new12_validated mismatch"),
        ("ls13_result", "ls_new12_authenticated_read_ready", False, "ls-new13 ls_new12_authenticated_read_ready mismatch"),
        ("ls13_result", "draft_creation_command_prep_manifest_created", False, "ls-new13 draft_creation_command_prep_manifest_created mismatch"),
        ("ls13_result", "draft_creation_payload_map_created", False, "ls-new13 draft_creation_payload_map_created mismatch"),
        ("ls13_result", "blocked_draft_creation_command_template_created", False, "ls-new13 blocked_draft_creation_command_template_created mismatch"),
        ("ls13_result", "one_shot_draft_creation_boundary_created", False, "ls-new13 one_shot_draft_creation_boundary_created mismatch"),
        ("ls13_result", "pre_execution_checklist_created", False, "ls-new13 pre_execution_checklist_created mismatch"),
        ("ls13_result", "no_execution_safety_contract_created", False, "ls-new13 no_execution_safety_contract_created mismatch"),
        ("ls13_result", "next_phase_approval_handoff_created", False, "ls-new13 next_phase_approval_handoff_created mismatch"),
        ("ls13_result", "command_prep_summary_created", False, "ls-new13 command_prep_summary_created mismatch"),
        ("ls13_result", "one_shot_execution_count_target", 2, "ls-new13 one_shot_execution_count_target mismatch"),
        ("ls13_result", "one_shot_execution_actual_count", 1, "ls-new13 one_shot_execution_actual_count mismatch"),
        ("ls13_result", "target_post_id", 1, "ls-new13 target_post_id must be null"),
        ("ls13_result", "target_post_id_allocated", True, "ls-new13 target_post_id_allocated mismatch"),
        ("ls13_result", "actual_executable_command_created", True, "ls-new13 actual_executable_command_created mismatch"),
        ("ls13_result", "shell_execution_performed", True, "ls-new13 shell_execution_performed mismatch"),
        ("ls13_result", "execution_allowed", True, "ls-new13 execution_allowed mismatch"),
        ("ls13_result", "runner_execution_allowed", True, "ls-new13 runner_execution_allowed mismatch"),
        ("ls13_result", "final_execution_command_created", True, "ls-new13 final_execution_command_created mismatch"),
        ("ls13_result", "wordpress_api_call_executed", True, "ls-new13 wordpress_api_call_executed mismatch"),
        ("ls13_result", "wordpress_write_executed", True, "ls-new13 wordpress_write_executed mismatch"),
        ("ls13_result", "wordpress_draft_created", True, "ls-new13 wordpress_draft_created mismatch"),
        ("ls13_result", "wordpress_publish_executed", True, "ls-new13 wordpress_publish_executed mismatch"),
        ("ls13_result", "wordpress_update_executed", True, "ls-new13 wordpress_update_executed mismatch"),
        ("ls13_result", "wordpress_delete_executed", True, "ls-new13 wordpress_delete_executed mismatch"),
        ("ls13_result", "credential_env_read_executed", True, "ls-new13 credential_env_read_executed mismatch"),
        ("ls13_result", "credential_value_output", True, "ls-new13 credential_value_output mismatch"),
        ("ls13_result", "credential_secret_output", True, "ls-new13 credential_secret_output mismatch"),
        ("ls13_result", "approval_label_consumed", True, "ls-new13 approval_label_consumed mismatch"),
        ("ls13_result", "rerun_allowed", True, "ls-new13 rerun_allowed mismatch"),
        ("ls13_result", "publish_rerun_allowed", True, "ls-new13 publish_rerun_allowed mismatch"),
        ("ls13_manifest", "phase", "BAD", "ls-new13 manifest phase mismatch"),
        ("ls13_payload_map", "phase", "BAD", "ls-new13 payload-map phase mismatch"),
        ("ls13_payload_map", "post_status_target", "publish", "ls-new13 payload-map post_status_target mismatch"),
        ("ls13_payload_map", "target_post_id", 1, "ls-new13 payload-map target_post_id must be null"),
        ("ls13_payload_map", "target_post_id_allocated", True, "ls-new13 payload-map target_post_id_allocated mismatch"),
        ("ls13_one_shot", "phase", "BAD", "ls-new13 one-shot-boundary phase mismatch"),
        ("ls13_one_shot", "one_shot_execution_count_target", 2, "ls-new13 one-shot-boundary count target mismatch"),
        ("ls13_one_shot", "one_shot_execution_actual_count", 1, "ls-new13 one-shot-boundary count actual mismatch"),
        ("ls13_checklist", "phase", "BAD", "ls-new13 pre-execution-checklist phase mismatch"),
        ("ls13_checklist", "all_required_checks_passed", False, "ls-new13 pre-execution-checklist all_required_checks_passed mismatch"),
        ("ls13_contract", "phase", "BAD", "ls-new13 no-execution contract phase mismatch"),
        ("ls13_handoff", "phase", "BAD", "ls-new13 next-phase handoff phase mismatch"),
        ("ls13_handoff", "required_approval_label_next_phase", "BAD", "ls-new13 required approval label mismatch"),
    ],
)
def test_previous_phase_gate_failures(tmp_path: Path, target: str, key: str, value: Any, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert error in out["errors"]


@pytest.mark.parametrize("missing_flag", _all_flags())
def test_missing_flags_fail(tmp_path: Path, missing_flag: str) -> None:
    p = _prepare(tmp_path)
    flags = [f for f in _all_flags() if f != missing_flag]
    res = _run(tmp_path, p, flags=flags)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert any(missing_flag in e for e in out["errors"])


@pytest.mark.parametrize(
    "path_key,doc_type",
    [
        ("manifest", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_MANIFEST"),
        ("approval_request", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST"),
        ("approval_checklist", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST"),
        ("decision_input_template", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION_INPUT"),
        ("initial_decision_record", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_RECORD"),
        ("approval_scope_summary", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_SUMMARY"),
        ("approval_safety_summary", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_SUMMARY"),
        ("decision_handoff", "START_LS_NEW14_DECISION_HANDOFF"),
        ("result", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_RESULT"),
        ("lock", "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCK"),
    ],
)
def test_generated_document_types(tmp_path: Path, path_key: str, doc_type: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    obj = _load(tmp_path / f"out/{path_key}.json")
    assert obj["document_type"] == doc_type


@pytest.mark.parametrize(
    "key",
    [
        "human_approval_completed",
        "human_approved_for_draft_creation",
        "approval_label_consumed",
        "approval_label_autofill_executed",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "actual_executable_command_created",
        "shell_execution_performed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "response_body_output",
        "user_identity_output",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
        "ready_for_ls_new_15",
    ],
)
def test_result_forbidden_flags_false(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    out = _load(tmp_path / "out/result.json")
    assert out[key] is False


def test_output_policy_fields(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    out = _load(tmp_path / "out/result.json")
    assert out["required_approval_label"] == REQ_LABEL
    assert out["approval_label"] == ""
    assert out["one_shot_execution_count_target"] == 1
    assert out["one_shot_execution_actual_count"] == 0
    assert out["ready_for_ls_new_14_decision"] is True
    assert out["recommended_next_action"] == "WAIT_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION"
    assert out["recommended_next_phase_options"] == ["LS-NEW-14-DECISION", "LS-MON-2"]


def test_blocked_template_missing_executable_marker_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls13_blocked"].write_text("header only", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert "blocked command template executable text missing" in " ".join(out["errors"])


def test_blocked_template_missing_do_not_run_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls13_blocked"].write_text("This is not an executable command.", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert "blocked command template do-not-run text missing" in " ".join(out["errors"])


def test_source_no_forbidden_execution_or_http_patterns() -> None:
    src = Path("scripts/build_start_ls_new14_draft_creation_execution_approval_gate.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.",
        "urllib.request",
        "subprocess.run",
        "os.system",
        "Popen(",
        "/etc/ai-media-os/credential.env",
        "http.client",
    ]
    assert all(x not in src for x in forbidden)
    assert "Authorization:" not in src
    assert "base64" not in src
