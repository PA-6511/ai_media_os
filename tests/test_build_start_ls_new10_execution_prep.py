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


def _base_ls9_result() -> dict:
    return {
        "status": "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION",
        "ready_for_ls_new_10": True,
        "recommended_next_action": "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY",
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "approval_label_consumed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "wordpress_api_call_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
    }


def _base_ls9_validation() -> dict:
    return {"validation_status": "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"}


def _base_ls9_record() -> dict:
    return {"status": "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"}


def _base_ls6_payload() -> dict:
    return {
        "phase": "LS-NEW-6",
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
    }


def _base_ls7_manifest() -> dict:
    return {"phase": "LS-NEW-7"}


def _base_ls8_manifest() -> dict:
    return {"phase": "LS-NEW-8"}


def _base_boundary() -> dict:
    return {"phase": "LS-NEW-8"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls9_result": tmp_path / "in/ls9_result.json",
        "ls9_validation": tmp_path / "in/ls9_validation.json",
        "ls9_record": tmp_path / "in/ls9_record.json",
        "ls6_payload": tmp_path / "in/ls6_payload.json",
        "ls7_manifest": tmp_path / "in/ls7_manifest.json",
        "ls8_manifest": tmp_path / "in/ls8_manifest.json",
        "freeze": tmp_path / "in/freeze.json",
        "rollback": tmp_path / "in/rollback.json",
        "abort": tmp_path / "in/abort.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls9_result"], _base_ls9_result())
    _write_json(p["ls9_validation"], _base_ls9_validation())
    _write_json(p["ls9_record"], _base_ls9_record())
    _write_json(p["ls6_payload"], _base_ls6_payload())
    _write_json(p["ls7_manifest"], _base_ls7_manifest())
    _write_json(p["ls8_manifest"], _base_ls8_manifest())
    _write_json(p["freeze"], _base_boundary())
    _write_json(p["rollback"], _base_boundary())
    _write_json(p["abort"], _base_boundary())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "input_map": tmp_path / "out/input_map.json",
        "dry": tmp_path / "out/dry.json",
        "handoff": tmp_path / "out/handoff.json",
        "blocked": tmp_path / "out/blocked.md",
        "safety": tmp_path / "out/safety.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new10_execution_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new9-decision-result",
        str(p["ls9_result"]),
        "--ls-new9-decision-validation-result",
        str(p["ls9_validation"]),
        "--ls-new9-decision-record",
        str(p["ls9_record"]),
        "--ls-new6-payload",
        str(p["ls6_payload"]),
        "--ls-new7-runner-prep-manifest",
        str(p["ls7_manifest"]),
        "--ls-new8-final-preflight-manifest",
        str(p["ls8_manifest"]),
        "--ls-new8-freeze-boundary",
        str(p["freeze"]),
        "--ls-new8-rollback-boundary",
        str(p["rollback"]),
        "--ls-new8-abort-conditions",
        str(p["abort"]),
        "--output-manifest",
        str(out["manifest"]),
        "--output-input-map",
        str(out["input_map"]),
        "--output-dry-boundary",
        str(out["dry"]),
        "--output-credential-handoff",
        str(out["handoff"]),
        "--output-blocked-command-template",
        str(out["blocked"]),
        "--output-safety-summary",
        str(out["safety"]),
        "--output-summary",
        str(out["summary"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]
    required_flags = [
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


def test_valid_build_success(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW10_EXECUTION_PREP_READY_NO_DRAFT_CREATION"
    assert result["ready_for_ls_new_11"] is True
    assert result["recommended_next_action"] == "BEGIN_LS_NEW_11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE"


@pytest.mark.parametrize(
    "key",
    [
        "execution_prep_manifest_created",
        "execution_input_map_created",
        "draft_creation_dry_boundary_created",
        "credential_preflight_handoff_request_created",
        "blocked_execution_command_template_created",
        "execution_prep_safety_summary_created",
        "execution_prep_summary_created",
    ],
)
def test_created_flags_true(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result[key] is True


@pytest.mark.parametrize(
    "key",
    [
        "execution_allowed",
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
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ],
)
def test_result_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    result = _load(tmp_path / "out/result.json")
    assert result[key] is False


def test_result_content_fields(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    result = _load(tmp_path / "out/result.json")
    assert result["content_item_id"] == "new-comic-001"
    assert result["title"] == "月曜日のたわわ"
    assert result["volume"] == "第15巻"
    assert result["author"] == "比村奇石"
    assert result["publisher"] == "講談社"
    assert result["release_date"] == "2026-07-06"
    assert result["post_status_target"] == "draft"
    assert result["target_post_id"] is None
    assert result["target_post_id_allocated"] is False


@pytest.mark.parametrize(
    "missing",
    [
        "policy",
        "schema",
        "ls9_result",
        "ls9_validation",
        "ls9_record",
        "ls6_payload",
        "ls7_manifest",
        "ls8_manifest",
        "freeze",
        "rollback",
        "abort",
    ],
)
def test_missing_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW10_EXECUTION_PREP_FAILED_NO_DRAFT_CREATION"


@pytest.mark.parametrize(
    "missing_flag",
    [
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
def test_missing_required_flags_fail(tmp_path: Path, missing_flag: str) -> None:
    p = _prepare(tmp_path)
    all_flags = [
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
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls9_result", "status", "BAD", "ls-new9 decision status mismatch"),
        ("ls9_validation", "validation_status", "BAD", "ls-new9 decision validation status mismatch"),
        ("ls9_record", "status", "BAD", "ls-new9 decision record status mismatch"),
        ("ls9_result", "ready_for_ls_new_10", False, "ls-new9 ready_for_ls_new_10 mismatch"),
        ("ls9_result", "recommended_next_action", "BAD", "ls-new9 recommended_next_action mismatch"),
        ("ls9_result", "execution_allowed", True, "ls-new9 execution_allowed mismatch"),
        ("ls9_result", "runner_execution_allowed", True, "ls-new9 runner_execution_allowed mismatch"),
        ("ls9_result", "final_execution_command_created", True, "ls-new9 final_execution_command_created mismatch"),
        ("ls9_result", "approval_label_consumed", True, "ls-new9 approval_label_consumed mismatch"),
        ("ls9_result", "target_post_id", 7, "ls-new9 target_post_id must be null"),
        ("ls9_result", "target_post_id_allocated", True, "ls-new9 target_post_id_allocated mismatch"),
        ("ls9_result", "wordpress_api_call_executed", True, "ls-new9 wordpress_api_call_executed=true"),
        ("ls9_result", "wordpress_draft_created", True, "ls-new9 wordpress_draft_created=true"),
        ("ls9_result", "credential_env_read_executed", True, "ls-new9 credential_env_read_executed=true"),
        ("ls9_result", "credential_existence_check_executed", True, "ls-new9 credential_existence_check_executed=true"),
        ("ls6_payload", "phase", "BAD", "ls-new6 payload phase mismatch"),
        ("ls7_manifest", "phase", "BAD", "ls-new7 runner phase mismatch"),
        ("ls8_manifest", "phase", "BAD", "ls-new8 final preflight phase mismatch"),
    ],
)
def test_previous_phase_gate_failures(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "path_key,document_key,expected",
    [
        ("manifest", "document_type", "START_LS_NEW10_EXECUTION_PREP_MANIFEST"),
        ("input_map", "document_type", "START_LS_NEW10_EXECUTION_INPUT_MAP"),
        ("dry", "document_type", "START_LS_NEW10_DRAFT_CREATION_DRY_BOUNDARY"),
        ("handoff", "document_type", "START_LS_NEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST"),
        ("safety", "document_type", "START_LS_NEW10_EXECUTION_PREP_SAFETY_SUMMARY"),
        ("result", "document_type", "START_LS_NEW10_EXECUTION_PREP_RESULT"),
        ("lock", "document_type", "START_LS_NEW10_EXECUTION_PREP_LOCK"),
    ],
)
def test_generated_document_types(tmp_path: Path, path_key: str, document_key: str, expected: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    target = _load(tmp_path / f"out/{path_key}.json")
    assert target[document_key] == expected


def test_blocked_template_content(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    text = (tmp_path / "out/blocked.md").read_text(encoding="utf-8")
    assert "This is not an executable command." in text
    assert "Execution allowed: false" in text
    assert "WordPress draft creation allowed: false" in text


def test_summary_content(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    text = (tmp_path / "out/summary.md").read_text(encoding="utf-8")
    assert "# LS-NEW-10 Execution Prep Summary" in text
    assert "- Ready for LS-NEW-11: true" in text
    assert "WordPress下書き作成" in text


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new10_execution_prep.py").read_text(encoding="utf-8")
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