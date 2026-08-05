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


def _base_ls7_manifest() -> dict:
    return {
        "phase": "LS-NEW-7",
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_MANIFEST_READY_NO_EXECUTION",
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "post_status_target": "draft",
        "target_post_id": None,
    }


def _base_ls7_safety() -> dict:
    return {"status": "LSNEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT_READY_NO_EXECUTION"}


def _base_ls7_preflight() -> dict:
    return {"status": "LSNEW7_PREFLIGHT_CHECKLIST_READY_NO_EXECUTION"}


def _base_ls7_command() -> str:
    return "# LS-NEW-7 Blocked Execution Command Template\n"


def _base_ls7_summary() -> str:
    return "# LS-NEW-7 WordPress Draft Runner Prep Summary\n"


def _base_ls7_result() -> dict:
    return {
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "ready_for_ls_new_8": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "target_post_id_allocated": False,
    }


def _base_ls7_validation() -> dict:
    return {"validation_status": "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls7_manifest": tmp_path / "in/ls7_manifest.json",
        "ls7_safety": tmp_path / "in/ls7_safety.json",
        "ls7_preflight": tmp_path / "in/ls7_preflight.json",
        "ls7_command": tmp_path / "in/ls7_command.md",
        "ls7_summary": tmp_path / "in/ls7_summary.md",
        "ls7_result": tmp_path / "in/ls7_result.json",
        "ls7_validation": tmp_path / "in/ls7_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls7_manifest"], _base_ls7_manifest())
    _write_json(p["ls7_safety"], _base_ls7_safety())
    _write_json(p["ls7_preflight"], _base_ls7_preflight())
    p["ls7_command"].parent.mkdir(parents=True, exist_ok=True)
    p["ls7_command"].write_text(_base_ls7_command(), encoding="utf-8")
    p["ls7_summary"].parent.mkdir(parents=True, exist_ok=True)
    p["ls7_summary"].write_text(_base_ls7_summary(), encoding="utf-8")
    _write_json(p["ls7_result"], _base_ls7_result())
    _write_json(p["ls7_validation"], _base_ls7_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "manifest": tmp_path / "out/manifest.json",
        "freeze": tmp_path / "out/freeze.json",
        "rollback": tmp_path / "out/rollback.json",
        "abort": tmp_path / "out/abort.json",
        "handoff": tmp_path / "out/handoff.json",
        "summary": tmp_path / "out/summary.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }

    cmd = [
        "python3",
        "scripts/build_start_ls_new8_wp_draft_runner_final_preflight.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new7-manifest",
        str(p["ls7_manifest"]),
        "--ls-new7-safety-contract",
        str(p["ls7_safety"]),
        "--ls-new7-preflight-checklist",
        str(p["ls7_preflight"]),
        "--ls-new7-command-template",
        str(p["ls7_command"]),
        "--ls-new7-summary",
        str(p["ls7_summary"]),
        "--ls-new7-result",
        str(p["ls7_result"]),
        "--ls-new7-validation-result",
        str(p["ls7_validation"]),
        "--output-manifest",
        str(out["manifest"]),
        "--output-freeze-boundary",
        str(out["freeze"]),
        "--output-rollback-boundary",
        str(out["rollback"]),
        "--output-abort-conditions",
        str(out["abort"]),
        "--output-handoff",
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


def test_success_build_ready(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0, res.stderr

    manifest = _load(tmp_path / "out/manifest.json")
    freeze = _load(tmp_path / "out/freeze.json")
    rollback = _load(tmp_path / "out/rollback.json")
    abort = _load(tmp_path / "out/abort.json")
    handoff = _load(tmp_path / "out/handoff.json")
    result = _load(tmp_path / "out/result.json")
    lock = _load(tmp_path / "out/lock.json")

    assert result["status"] == "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION"
    assert result["production_status"] == "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY"
    assert result["ls_new7_validated"] is True
    assert result["ready_for_ls_new_9"] is True
    assert result["recommended_next_action"] == "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION"
    assert result["recommended_next_phase_options"] == ["LS-NEW-9", "LS-MON-2"]
    assert manifest["final_preflight_manifest_created"] is True
    assert freeze["freeze_required_before_later_execution"] is True
    assert rollback["rollback_required_before_later_execution"] is True
    assert abort["abort_triggered"] is False
    assert handoff["handoff_ready"] is True
    assert lock["final_execution_command_created"] is False


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls7_result", "status", "BAD", "ls-new7 run status mismatch"),
        ("ls7_validation", "validation_status", "BAD", "ls-new7 validation status mismatch"),
        ("ls7_result", "ready_for_ls_new_8", False, "ls-new7 ready_for_ls_new_8 mismatch"),
        ("ls7_result", "execution_allowed", True, "ls-new7 execution_allowed mismatch"),
        ("ls7_result", "runner_execution_allowed", True, "ls-new7 runner_execution_allowed mismatch"),
        ("ls7_result", "wordpress_api_call_executed", True, "ls-new7 wordpress_api_call_executed=true"),
        ("ls7_result", "wordpress_write_executed", True, "ls-new7 wordpress_write_executed=true"),
        ("ls7_result", "wordpress_draft_created", True, "ls-new7 wordpress_draft_created=true"),
        ("ls7_result", "credential_env_read_executed", True, "ls-new7 credential_env_read_executed=true"),
        ("ls7_result", "credential_existence_check_executed", True, "ls-new7 credential_existence_check_executed=true"),
        ("ls7_result", "target_post_id_allocated", True, "ls-new7 target_post_id_allocated=true"),
        ("ls7_manifest", "status", "BAD", "ls-new7 manifest status mismatch"),
        ("ls7_safety", "status", "BAD", "ls-new7 safety status mismatch"),
        ("ls7_preflight", "status", "BAD", "ls-new7 preflight status mismatch"),
    ],
)
def test_ls7_gate_failures(tmp_path: Path, target: str, key: str, value, error: str) -> None:
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
        "ls7_manifest",
        "ls7_safety",
        "ls7_preflight",
        "ls7_command",
        "ls7_summary",
        "ls7_result",
        "ls7_validation",
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
def test_missing_ls7_manifest_fields_fail(tmp_path: Path, field: str) -> None:
    p = _prepare(tmp_path)
    m = _load(p["ls7_manifest"])
    m[field] = ""
    _write_json(p["ls7_manifest"], m)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert f"missing ls-new7 manifest field: {field}" in result["errors"]


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
def test_missing_required_flags(tmp_path: Path, missing_flag: str) -> None:
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
    "key",
    [
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
        "approval_label_consumed",
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
        "runner_execution_allowed",
        "final_execution_command_created",
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


def test_boundaries_and_handoff_content(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0

    freeze = _load(tmp_path / "out/freeze.json")
    rollback = _load(tmp_path / "out/rollback.json")
    abort = _load(tmp_path / "out/abort.json")
    handoff = _load(tmp_path / "out/handoff.json")

    assert freeze["freeze_scope"] == [
        "LS-NEW-6 WP draft payload prep",
        "LS-NEW-7 runner prep manifest",
        "LS-NEW-7 safety contract",
        "LS-NEW-8 final preflight manifest",
    ]
    assert rollback["target_post_id"] is None
    assert "post_id=119 update is attempted" in abort["abort_if_any_true"]
    assert "post_id=183 update is attempted" in abort["abort_if_any_true"]
    assert handoff["next_phase"] == "LS-NEW-9"
    assert handoff["required_future_approval_label"] == "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"


def test_summary_created(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    summary = (tmp_path / "out/summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# LS-NEW-8 WordPress Draft Runner Final Preflight Summary")
    assert "- Ready for LS-NEW-9: true" in summary


def test_invalid_json_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls7_manifest"].write_text("{bad", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json ls-new7-manifest" in e for e in result["errors"])


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new8_wp_draft_runner_final_preflight.py").read_text(encoding="utf-8")
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
