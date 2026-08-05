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


def _base_ls12_result() -> dict[str, Any]:
    return {
        "status": "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE",
        "ready_for_ls_new_13": True,
        "wordpress_authenticated_read_get_succeeded": True,
        "wordpress_authenticated_read_status_class": "2xx",
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
    }


def _base_ls12_validation() -> dict[str, Any]:
    return {"validation_status": "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"}


def _base_ls12_manifest() -> dict[str, Any]:
    return {"phase": "LS-NEW-12"}


def _base_ls12_read_result() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-12",
        "wordpress_authenticated_read_get_succeeded": True,
    }


def _base_ls12_hold() -> dict[str, Any]:
    return {"phase": "LS-NEW-12"}


def _base_ls12_handoff() -> dict[str, Any]:
    return {"phase": "LS-NEW-12", "ready_for_ls_new_13": True}


def _base_ls6_payload() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-6",
        "post_title": "【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補",
        "post_content_markdown": "body",
        "post_status_target": "draft",
    }


def _base_ls10_input_map() -> dict[str, Any]:
    return {"phase": "LS-NEW-10"}


def _base_ls10_dry() -> dict[str, Any]:
    return {"phase": "LS-NEW-10"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls12_result": tmp_path / "in/ls12_result.json",
        "ls12_validation": tmp_path / "in/ls12_validation.json",
        "ls12_manifest": tmp_path / "in/ls12_manifest.json",
        "ls12_read_result": tmp_path / "in/ls12_read_result.json",
        "ls12_hold": tmp_path / "in/ls12_hold.json",
        "ls12_handoff": tmp_path / "in/ls12_handoff.json",
        "ls6_payload": tmp_path / "in/ls6_payload.json",
        "ls10_input_map": tmp_path / "in/ls10_input_map.json",
        "ls10_dry": tmp_path / "in/ls10_dry.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls12_result"], _base_ls12_result())
    _write_json(p["ls12_validation"], _base_ls12_validation())
    _write_json(p["ls12_manifest"], _base_ls12_manifest())
    _write_json(p["ls12_read_result"], _base_ls12_read_result())
    _write_json(p["ls12_hold"], _base_ls12_hold())
    _write_json(p["ls12_handoff"], _base_ls12_handoff())
    _write_json(p["ls6_payload"], _base_ls6_payload())
    _write_json(p["ls10_input_map"], _base_ls10_input_map())
    _write_json(p["ls10_dry"], _base_ls10_dry())
    return p


def _all_flags() -> list[str]:
    return [
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
        "--require-no-approval-label-consumption",
        "--require-no-target-post-id-allocation",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--require-no-rerun",
        "--require-no-publish-rerun",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "payload_map": tmp_path / "out/payload_map.json",
        "blocked": tmp_path / "out/blocked.md",
        "one_shot": tmp_path / "out/one_shot.json",
        "checklist": tmp_path / "out/checklist.json",
        "contract": tmp_path / "out/contract.json",
        "handoff": tmp_path / "out/handoff.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new13_draft_creation_command_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new12-result",
        str(p["ls12_result"]),
        "--ls-new12-validation-result",
        str(p["ls12_validation"]),
        "--ls-new12-manifest",
        str(p["ls12_manifest"]),
        "--ls-new12-authenticated-read-result",
        str(p["ls12_read_result"]),
        "--ls-new12-draft-creation-hold-boundary",
        str(p["ls12_hold"]),
        "--ls-new12-next-phase-handoff",
        str(p["ls12_handoff"]),
        "--ls-new6-payload",
        str(p["ls6_payload"]),
        "--ls-new10-execution-input-map",
        str(p["ls10_input_map"]),
        "--ls-new10-dry-boundary",
        str(p["ls10_dry"]),
        "--output-manifest",
        str(out["manifest"]),
        "--output-payload-map",
        str(out["payload_map"]),
        "--output-blocked-command-template",
        str(out["blocked"]),
        "--output-one-shot-boundary",
        str(out["one_shot"]),
        "--output-pre-execution-checklist",
        str(out["checklist"]),
        "--output-no-execution-safety-contract",
        str(out["contract"]),
        "--output-next-phase-approval-handoff",
        str(out["handoff"]),
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
    assert out["status"] == "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION"
    assert out["one_shot_execution_count_target"] == 1
    assert out["one_shot_execution_actual_count"] == 0
    assert out["ready_for_ls_new_14"] is True


@pytest.mark.parametrize(
    "missing",
    [
        "ls12_validation",
        "ls12_result",
        "ls12_manifest",
        "ls12_read_result",
        "ls12_hold",
        "ls12_handoff",
        "ls6_payload",
        "ls10_input_map",
        "ls10_dry",
    ],
)
def test_missing_previous_inputs_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/result.json")
    assert out["status"] == "LSNEW13_DRAFT_CREATION_COMMAND_PREP_FAILED_NO_EXECUTION"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls12_validation", "validation_status", "BAD", "ls-new12 validation status mismatch"),
        ("ls12_result", "status", "BAD", "ls-new12 run status mismatch"),
        ("ls12_result", "ready_for_ls_new_13", False, "ls-new12 ready_for_ls_new_13 mismatch"),
        ("ls12_result", "wordpress_authenticated_read_get_succeeded", False, "ls-new12 authenticated read succeeded mismatch"),
        ("ls12_result", "wordpress_authenticated_read_status_class", "4xx", "ls-new12 authenticated read status class mismatch"),
        ("ls12_result", "wordpress_authenticated_read_response_body_saved", True, "ls-new12 response body saved mismatch"),
        ("ls12_result", "wordpress_authenticated_user_identity_saved", True, "ls-new12 user identity saved mismatch"),
        ("ls12_result", "credential_value_output", True, "ls-new12 credential_value_output mismatch"),
        ("ls12_result", "authorization_header_output", True, "ls-new12 authorization_header_output mismatch"),
        ("ls12_result", "basic_auth_output", True, "ls-new12 basic_auth_output mismatch"),
        ("ls12_result", "base64_auth_output", True, "ls-new12 base64_auth_output mismatch"),
        ("ls12_result", "execution_allowed", True, "ls-new12 execution_allowed mismatch"),
        ("ls12_result", "runner_execution_allowed", True, "ls-new12 runner_execution_allowed mismatch"),
        ("ls12_result", "final_execution_command_created", True, "ls-new12 final_execution_command_created mismatch"),
        ("ls12_result", "wordpress_draft_created", True, "ls-new12 wordpress_draft_created mismatch"),
        ("ls12_result", "wordpress_publish_executed", True, "ls-new12 wordpress_publish_executed mismatch"),
        ("ls12_result", "target_post_id_allocated", True, "ls-new12 target_post_id_allocated mismatch"),
        ("ls12_result", "target_post_id", 9, "ls-new12 target_post_id must be null"),
        ("ls12_result", "approval_label_consumed", True, "ls-new12 approval_label_consumed mismatch"),
        ("ls6_payload", "post_title", "", "payload title missing"),
        ("ls6_payload", "post_content_markdown", "", "payload body missing"),
        ("ls6_payload", "post_status_target", "publish", "payload status not draft"),
        ("ls12_manifest", "phase", "BAD", "ls-new12 manifest phase mismatch"),
        ("ls12_read_result", "phase", "BAD", "ls-new12 authenticated-read-result phase mismatch"),
        ("ls12_read_result", "wordpress_authenticated_read_get_succeeded", False, "ls-new12 authenticated-read-result succeeded mismatch"),
        ("ls12_hold", "phase", "BAD", "ls-new12 hold boundary phase mismatch"),
        ("ls12_handoff", "phase", "BAD", "ls-new12 handoff phase mismatch"),
        ("ls12_handoff", "ready_for_ls_new_13", False, "ls-new12 handoff ready_for_ls_new_13 mismatch"),
        ("ls10_input_map", "phase", "BAD", "ls-new10 input map phase mismatch"),
        ("ls10_dry", "phase", "BAD", "ls-new10 dry boundary phase mismatch"),
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
        ("manifest", "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_MANIFEST"),
        ("payload_map", "START_LS_NEW13_DRAFT_CREATION_PAYLOAD_MAP"),
        ("one_shot", "START_LS_NEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY"),
        ("checklist", "START_LS_NEW13_PRE_EXECUTION_CHECKLIST"),
        ("contract", "START_LS_NEW13_NO_EXECUTION_SAFETY_CONTRACT"),
        ("handoff", "START_LS_NEW13_NEXT_PHASE_APPROVAL_HANDOFF"),
        ("result", "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_RESULT"),
        ("lock", "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_LOCK"),
    ],
)
def test_generated_document_types(tmp_path: Path, path_key: str, doc_type: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    suffix = "md" if path_key == "blocked" else "json"
    if path_key != "blocked":
        obj = _load(tmp_path / f"out/{path_key}.{suffix}")
        assert obj["document_type"] == doc_type


def test_payload_map_fields(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    m = _load(tmp_path / "out/payload_map.json")
    assert m["payload_title_confirmed"] is True
    assert m["payload_body_present"] is True
    assert m["payload_status_draft_confirmed"] is True
    assert m["payload_source_not_modified"] is True
    assert m["target_post_id"] is None


def test_blocked_template_markers(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    text = (tmp_path / "out/blocked.md").read_text(encoding="utf-8")
    assert "not an executable command" in text
    assert "Do not run" in text
    assert "WordPress POST" in text
    assert "python3 " not in text
    assert "curl " not in text


@pytest.mark.parametrize(
    "key",
    [
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
        "approval_label_consumed",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_result_forbidden_flags_false(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    _run(tmp_path, p)
    out = _load(tmp_path / "out/result.json")
    assert out[key] is False


def test_source_no_forbidden_execution_or_http_patterns() -> None:
    src = Path("scripts/build_start_ls_new13_draft_creation_command_prep.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.",
        "urllib.request",
        "subprocess.run",
        "os.system",
        "Popen(",
        "/etc/ai-media-os/credential.env",
    ]
    assert all(x not in src for x in forbidden)
