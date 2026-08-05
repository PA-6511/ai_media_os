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


def _base_ls6_payload() -> dict:
    return {
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
    }


def _base_ls6_preview() -> str:
    return "# LS-NEW-6 WordPress Draft Payload Prep Preview\n"


def _base_ls6_safety() -> dict:
    return {
        "ready_for_ls_new_7": True,
    }


def _base_ls6_result() -> dict:
    return {
        "status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION",
        "ready_for_ls_new_7": True,
        "execution_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "target_post_id_allocated": False,
    }


def _base_ls6_validation() -> dict:
    return {"validation_status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls6_payload": tmp_path / "in/ls6_payload.json",
        "ls6_preview": tmp_path / "in/ls6_preview.md",
        "ls6_safety": tmp_path / "in/ls6_safety.json",
        "ls6_result": tmp_path / "in/ls6_result.json",
        "ls6_validation": tmp_path / "in/ls6_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls6_payload"], _base_ls6_payload())
    p["ls6_preview"].parent.mkdir(parents=True, exist_ok=True)
    p["ls6_preview"].write_text(_base_ls6_preview(), encoding="utf-8")
    _write_json(p["ls6_safety"], _base_ls6_safety())
    _write_json(p["ls6_result"], _base_ls6_result())
    _write_json(p["ls6_validation"], _base_ls6_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "safety_contract": tmp_path / "out/safety_contract.json",
        "preflight": tmp_path / "out/preflight.json",
        "command": tmp_path / "out/blocked.md",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new7_wp_draft_runner_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new6-payload",
        str(p["ls6_payload"]),
        "--ls-new6-preview",
        str(p["ls6_preview"]),
        "--ls-new6-safety-summary",
        str(p["ls6_safety"]),
        "--ls-new6-result",
        str(p["ls6_result"]),
        "--ls-new6-validation-result",
        str(p["ls6_validation"]),
        "--output-manifest",
        str(out["manifest"]),
        "--output-safety-contract",
        str(out["safety_contract"]),
        "--output-preflight-checklist",
        str(out["preflight"]),
        "--output-command-template",
        str(out["command"]),
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
    assert res.returncode == 0, res.stderr
    manifest = _load(tmp_path / "out/manifest.json")
    result = _load(tmp_path / "out/result.json")
    lock = _load(tmp_path / "out/lock.json")
    assert result["status"] == "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"
    assert result["ready_for_ls_new_8"] is True
    assert manifest["runner_prep_manifest_created"] is True
    assert manifest["runner_execution_allowed"] is False
    assert lock["runner_execution_allowed"] is False


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls6_result", "status", "BAD", "ls-new6 run status mismatch"),
        ("ls6_validation", "validation_status", "BAD", "ls-new6 validation status mismatch"),
        ("ls6_result", "ready_for_ls_new_7", False, "ls-new6 ready_for_ls_new_7 mismatch"),
        ("ls6_result", "execution_allowed", True, "ls-new6 execution_allowed mismatch"),
        ("ls6_result", "wordpress_api_call_executed", True, "ls-new6 wordpress_api_call_executed=true"),
        ("ls6_result", "wordpress_write_executed", True, "ls-new6 wordpress_write_executed=true"),
        ("ls6_result", "wordpress_draft_created", True, "ls-new6 wordpress_draft_created=true"),
        ("ls6_result", "target_post_id_allocated", True, "ls-new6 target_post_id_allocated=true"),
        ("ls6_safety", "ready_for_ls_new_7", False, "ls-new6 safety ready_for_ls_new_7 mismatch"),
    ],
)
def test_ls6_gate_failures(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "field",
    ["content_item_id", "title", "volume", "author", "publisher", "release_date"],
)
def test_missing_ls6_payload_fields_fail(tmp_path: Path, field: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["ls6_payload"])
    d[field] = ""
    _write_json(p["ls6_payload"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert f"missing ls-new6 payload field: {field}" in result["errors"]


@pytest.mark.parametrize(
    "missing",
    ["policy", "schema", "ls6_payload", "ls6_preview", "ls6_safety", "ls6_result", "ls6_validation"],
)
def test_missing_input_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing" in e for e in result["errors"])


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--require-no-runner-execution",
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
        "--require-no-runner-execution",
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
        "runner_execution_allowed",
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
        "approval_label_consumed",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
        "target_post_id_allocated",
    ],
)
def test_manifest_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    manifest = _load(tmp_path / "out/manifest.json")
    assert manifest[key] is False


@pytest.mark.parametrize(
    "key",
    [
        "runner_execution_allowed",
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
        "approval_label_consumed",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
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
        "runner_execution_allowed",
        "execution_allowed",
        "approval_label_consumed",
        "target_post_id_allocated",
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
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_lock_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    lock = _load(tmp_path / "out/lock.json")
    assert lock[key] is False


def test_command_template_and_summary_created(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    command = (tmp_path / "out/blocked.md").read_text(encoding="utf-8")
    summary = (tmp_path / "out/summary.md").read_text(encoding="utf-8")
    assert "This is not an executable command." in command
    assert "- Execution allowed: false" in command
    assert "# LS-NEW-7 WordPress Draft Runner Prep Summary" in summary
    assert "- Source payload: exchange/new_release/start_ls_new6_wp_draft_payload_prep.json" in summary


def test_invalid_json_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls6_payload"].write_text("{bad", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json ls-new6-payload" in e for e in result["errors"])


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new7_wp_draft_runner_prep.py").read_text(encoding="utf-8")
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
