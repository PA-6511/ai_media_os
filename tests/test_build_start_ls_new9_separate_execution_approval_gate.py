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


def _base_ls8_manifest() -> dict:
    return {
        "status": "LSNEW8_FINAL_PREFLIGHT_MANIFEST_READY_NO_EXECUTION",
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
    }


def _base_ls8_freeze() -> dict:
    return {"status": "LSNEW8_FREEZE_BOUNDARY_READY_NO_EXECUTION"}


def _base_ls8_rollback() -> dict:
    return {"status": "LSNEW8_ROLLBACK_BOUNDARY_READY_NO_EXECUTION"}


def _base_ls8_abort() -> dict:
    return {"status": "LSNEW8_ABORT_CONDITIONS_READY_NO_EXECUTION"}


def _base_ls8_handoff() -> dict:
    return {"status": "LSNEW8_NEXT_APPROVAL_GATE_HANDOFF_READY_NO_EXECUTION"}


def _base_ls8_summary() -> str:
    return "# LS-NEW-8 WordPress Draft Runner Final Preflight Summary\n"


def _base_ls8_result() -> dict:
    return {
        "status": "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION",
        "ready_for_ls_new_9": True,
        "handoff_ready": True,
        "abort_triggered": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "target_post_id_allocated": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_draft_created": False,
    }


def _base_ls8_validation() -> dict:
    return {"validation_status": "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls8_manifest": tmp_path / "in/ls8_manifest.json",
        "ls8_freeze": tmp_path / "in/ls8_freeze.json",
        "ls8_rollback": tmp_path / "in/ls8_rollback.json",
        "ls8_abort": tmp_path / "in/ls8_abort.json",
        "ls8_handoff": tmp_path / "in/ls8_handoff.json",
        "ls8_summary": tmp_path / "in/ls8_summary.md",
        "ls8_result": tmp_path / "in/ls8_result.json",
        "ls8_validation": tmp_path / "in/ls8_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls8_manifest"], _base_ls8_manifest())
    _write_json(p["ls8_freeze"], _base_ls8_freeze())
    _write_json(p["ls8_rollback"], _base_ls8_rollback())
    _write_json(p["ls8_abort"], _base_ls8_abort())
    _write_json(p["ls8_handoff"], _base_ls8_handoff())
    p["ls8_summary"].parent.mkdir(parents=True, exist_ok=True)
    p["ls8_summary"].write_text(_base_ls8_summary(), encoding="utf-8")
    _write_json(p["ls8_result"], _base_ls8_result())
    _write_json(p["ls8_validation"], _base_ls8_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "request": tmp_path / "out/request.json",
        "checklist": tmp_path / "out/checklist.template.json",
        "decision_template": tmp_path / "out/decision.template.json",
        "decision_record": tmp_path / "out/decision.json",
        "scope": tmp_path / "out/scope.md",
        "safety": tmp_path / "out/safety.json",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }

    cmd = [
        "python3",
        "scripts/build_start_ls_new9_separate_execution_approval_gate.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new8-manifest",
        str(p["ls8_manifest"]),
        "--ls-new8-freeze-boundary",
        str(p["ls8_freeze"]),
        "--ls-new8-rollback-boundary",
        str(p["ls8_rollback"]),
        "--ls-new8-abort-conditions",
        str(p["ls8_abort"]),
        "--ls-new8-handoff",
        str(p["ls8_handoff"]),
        "--ls-new8-summary",
        str(p["ls8_summary"]),
        "--ls-new8-result",
        str(p["ls8_result"]),
        "--ls-new8-validation-result",
        str(p["ls8_validation"]),
        "--output-request",
        str(out["request"]),
        "--output-checklist-template",
        str(out["checklist"]),
        "--output-decision-template",
        str(out["decision_template"]),
        "--output-decision-record",
        str(out["decision_record"]),
        "--output-scope-summary",
        str(out["scope"]),
        "--output-safety-summary",
        str(out["safety"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]

    required_flags = [
        "--require-no-auto-approval",
        "--require-no-runner-execution",
        "--require-no-final-execution-command",
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
        "--require-no-credential-check",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    cmd.extend(required_flags if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_success_build_ready(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    request = _load(tmp_path / "out/request.json")
    safety = _load(tmp_path / "out/safety.json")
    assert result["status"] == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
    assert result["production_status"] == "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION"
    assert result["ls_new8_validated"] is True
    assert result["approval_request_created"] is True
    assert result["approval_checklist_template_created"] is True
    assert result["approval_decision_template_created"] is True
    assert result["approval_decision_record_created"] is True
    assert result["approval_scope_summary_created"] is True
    assert result["approval_gate_safety_summary_created"] is True
    assert request["approval_label"] == ""
    assert safety["auto_approval_executed"] is False


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls8_result", "status", "BAD", "ls-new8 run status mismatch"),
        ("ls8_validation", "validation_status", "BAD", "ls-new8 validation status mismatch"),
        ("ls8_result", "ready_for_ls_new_9", False, "ls-new8 ready_for_ls_new_9 mismatch"),
        ("ls8_result", "handoff_ready", False, "ls-new8 handoff_ready mismatch"),
        ("ls8_result", "abort_triggered", True, "ls-new8 abort_triggered mismatch"),
        ("ls8_result", "execution_allowed", True, "ls-new8 execution_allowed mismatch"),
        ("ls8_result", "runner_execution_allowed", True, "ls-new8 runner_execution_allowed mismatch"),
        ("ls8_result", "final_execution_command_created", True, "ls-new8 final_execution_command_created mismatch"),
        ("ls8_result", "wordpress_draft_created", True, "ls-new8 wordpress_draft_created=true"),
        ("ls8_result", "credential_env_read_executed", True, "ls-new8 credential_env_read_executed=true"),
        ("ls8_result", "credential_existence_check_executed", True, "ls-new8 credential_existence_check_executed=true"),
        ("ls8_result", "target_post_id_allocated", True, "ls-new8 target_post_id_allocated=true"),
        ("ls8_manifest", "status", "BAD", "ls-new8 manifest status mismatch"),
        ("ls8_freeze", "status", "BAD", "ls-new8 freeze status mismatch"),
        ("ls8_rollback", "status", "BAD", "ls-new8 rollback status mismatch"),
        ("ls8_abort", "status", "BAD", "ls-new8 abort status mismatch"),
        ("ls8_handoff", "status", "BAD", "ls-new8 handoff status mismatch"),
    ],
)
def test_ls8_gate_failures(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "ls8_manifest",
        "ls8_freeze",
        "ls8_rollback",
        "ls8_abort",
        "ls8_handoff",
        "ls8_summary",
        "ls8_result",
        "ls8_validation",
    ],
)
def test_missing_input_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing" in e for e in result["errors"])


@pytest.mark.parametrize(
    "field",
    ["content_item_id", "title", "volume", "author", "publisher", "release_date"],
)
def test_missing_ls8_manifest_fields_fail(tmp_path: Path, field: str) -> None:
    p = _prepare(tmp_path)
    m = _load(p["ls8_manifest"])
    m[field] = ""
    _write_json(p["ls8_manifest"], m)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert f"missing ls-new8 manifest field: {field}" in result["errors"]


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--require-no-auto-approval",
        "--require-no-runner-execution",
        "--require-no-final-execution-command",
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
        "--require-no-credential-check",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ],
)
def test_missing_required_flags(tmp_path: Path, missing_flag: str) -> None:
    p = _prepare(tmp_path)
    all_flags = [
        "--require-no-auto-approval",
        "--require-no-runner-execution",
        "--require-no-final-execution-command",
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
        "--require-no-credential-check",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    flags = [f for f in all_flags if f != missing_flag]
    res = _run(tmp_path, p, flags=flags)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any(missing_flag in e for e in result["errors"])


@pytest.mark.parametrize(
    "key",
    [
        "human_approval_completed",
        "human_approved_for_execution",
        "approval_label_consumed",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "approval_label_autofill_executed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
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
        "credential_existence_check_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
        "target_post_id_allocated",
    ],
)
def test_result_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result[key] is False


@pytest.mark.parametrize(
    "key",
    [
        "auto_approval_executed",
        "ai_self_approval_executed",
        "approval_label_autofill_executed",
        "approval_label_consumed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "credential_env_read_executed",
        "credential_existence_check_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
    ],
)
def test_safety_summary_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    safety = _load(tmp_path / "out/safety.json")
    assert safety[key] is False


def test_templates_and_scope_content(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    checklist = _load(tmp_path / "out/checklist.template.json")
    decision_template = _load(tmp_path / "out/decision.template.json")
    decision_record = _load(tmp_path / "out/decision.json")
    scope = (tmp_path / "out/scope.md").read_text(encoding="utf-8")
    assert checklist["human_decision"]["approval_label"] == ""
    assert "AI must not auto-approve" in decision_template["instructions"]
    assert decision_record["status"] == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION"
    assert "LS-NEW-9 自体では WordPress API / credential.env / draft creation を許可しない。" in scope


def test_invalid_json_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls8_manifest"].write_text("{bad", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json ls-new8-manifest" in e for e in result["errors"])


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new9_separate_execution_approval_gate.py").read_text(encoding="utf-8")
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
