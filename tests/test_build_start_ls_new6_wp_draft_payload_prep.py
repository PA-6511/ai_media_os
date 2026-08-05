from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-6"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-6"}


def _base_ls4_payload() -> dict:
    return {
        "document_type": "START_LS_NEW4_WP_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN",
        "wordpress_write_executed": False,
        "wordpress_api_call_executed": False,
        "post_status_target": "draft",
        "candidate_identity": {
            "content_item_id": "new-comic-001",
            "title": "月曜日のたわわ",
            "volume": "第15巻",
            "author": "比村奇石",
            "publisher": "講談社",
            "release_date": "2026-07-06",
            "asin": "B0H6DQLPPB",
            "isbn": "978-4065442296",
        },
        "post_title": "【2026-07-06発売】月曜日のたわわ 第15巻 電子書籍ストア候補",
        "body_markdown": "# heading\n外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。\n未取得\n",
        "affiliate_disclosure": "このページにはPR・アフィリエイトリンクを含む場合があります。",
        "external_fetch_notice": "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。",
    }


def _base_ls4_summary() -> dict:
    return {
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "external_fetch_executed": False,
        "wordpress_write_executed": False,
    }


def _base_ls5_result() -> dict:
    return {
        "status": "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION",
        "ready_for_ls_new_6": True,
        "execution_allowed": False,
        "approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_ls5_validation() -> dict:
    return {"validation_status": "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"}


def _base_ls5_record() -> dict:
    return {
        "status": "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION",
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls4_payload": tmp_path / "in/ls4_payload.json",
        "ls4_preview": tmp_path / "in/ls4_preview.md",
        "ls4_summary": tmp_path / "in/ls4_summary.json",
        "ls5_result": tmp_path / "in/ls5_result.json",
        "ls5_validation": tmp_path / "in/ls5_validation.json",
        "ls5_record": tmp_path / "in/ls5_record.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls4_payload"], _base_ls4_payload())
    p["ls4_preview"].parent.mkdir(parents=True, exist_ok=True)
    p["ls4_preview"].write_text("preview\n", encoding="utf-8")
    _write_json(p["ls4_summary"], _base_ls4_summary())
    _write_json(p["ls5_result"], _base_ls5_result())
    _write_json(p["ls5_validation"], _base_ls5_validation())
    _write_json(p["ls5_record"], _base_ls5_record())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "payload": tmp_path / "out/payload.json",
        "preview": tmp_path / "out/preview.md",
        "safety": tmp_path / "out/safety.json",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new6_wp_draft_payload_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new4-wp-payload",
        str(p["ls4_payload"]),
        "--ls-new4-wp-preview",
        str(p["ls4_preview"]),
        "--ls-new4-validation-summary",
        str(p["ls4_summary"]),
        "--ls-new5-decision-result",
        str(p["ls5_result"]),
        "--ls-new5-decision-validation-result",
        str(p["ls5_validation"]),
        "--ls-new5-decision-record",
        str(p["ls5_record"]),
        "--output-payload",
        str(out["payload"]),
        "--output-preview",
        str(out["preview"]),
        "--output-safety-summary",
        str(out["safety"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]
    req_flags = [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
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
    cmd.extend(req_flags if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_success_ready(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0, res.stderr
    payload = _load(tmp_path / "out/payload.json")
    result = _load(tmp_path / "out/result.json")
    safety = _load(tmp_path / "out/safety.json")
    assert payload["status"] == "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION"
    assert result["status"] == "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION"
    assert result["wp_draft_payload_created"] is True
    assert result["wp_draft_payload_preview_created"] is True
    assert result["safety_summary_created"] is True
    assert payload["ready_for_ls_new_7"] is True
    assert result["recommended_next_action"] == "BEGIN_LS_NEW_7_WP_DRAFT_RUNNER_PREP_NO_EXECUTION"
    assert safety["ready_for_ls_new_7"] is True


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("ls5_result", "status", "BAD", "ls-new5 decision status mismatch"),
        ("ls5_validation", "validation_status", "BAD", "ls-new5 decision validation mismatch"),
        ("ls5_record", "status", "BAD", "ls-new5 decision record status mismatch"),
        ("ls5_result", "ready_for_ls_new_6", False, "ls-new5 ready_for_ls_new_6 mismatch"),
        ("ls5_result", "execution_allowed", True, "ls-new5 execution_allowed mismatch"),
        ("ls5_result", "approval_label", "BAD", "ls-new5 approval_label mismatch"),
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls4_payload", "document_type", "BAD", "ls-new4 payload document_type mismatch"),
        ("ls4_payload", "wordpress_api_call_executed", True, "ls-new4 payload wordpress_api_call_executed=true"),
        ("ls4_payload", "wordpress_write_executed", True, "ls-new4 payload wordpress_write_executed=true"),
        ("ls4_payload", "post_status_target", "publish", "ls-new4 payload post_status_target mismatch"),
        ("ls4_summary", "purchase_navigation_media", False, "ls-new4 purchase_navigation_media mismatch"),
        ("ls4_summary", "work_explanation_media", True, "ls-new4 work_explanation_media mismatch"),
        ("ls4_summary", "external_fetch_executed", True, "ls-new4 external_fetch_executed=true"),
        ("ls4_summary", "wordpress_write_executed", True, "ls-new4 wordpress_write_executed=true"),
    ],
)
def test_required_inputs_and_gates(tmp_path: Path, target: str, key: str, value, error: str) -> None:
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
    ["content_item_id", "title", "volume", "author", "publisher", "release_date", "asin", "isbn"],
)
def test_missing_identity_field_fails(tmp_path: Path, field: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["ls4_payload"])
    d["candidate_identity"][field] = ""
    _write_json(p["ls4_payload"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert f"missing candidate field: {field}" in result["errors"]


@pytest.mark.parametrize("field", ["post_title", "body_markdown"])
def test_missing_post_fields_fail(tmp_path: Path, field: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["ls4_payload"])
    d[field] = ""
    _write_json(p["ls4_payload"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    expected = "missing post_title" if field == "post_title" else "missing body_markdown"
    assert expected in result["errors"]


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
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
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
        "--require-no-wordpress-publish",
        "--require-no-credential-read",
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
    flags = [x for x in all_flags if x != missing_flag]
    res = _run(tmp_path, p, flags=flags)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any(missing_flag in e for e in result["errors"])


@pytest.mark.parametrize(
    "key",
    [
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
        "approval_label_consumed",
    ],
)
def test_payload_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    payload = _load(tmp_path / "out/payload.json")
    assert payload[key] is False


@pytest.mark.parametrize(
    "key",
    [
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
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
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
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "target_post_id_allocated",
        "approval_label_consumed",
        "execution_allowed",
    ],
)
def test_safety_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    summary = _load(tmp_path / "out/safety.json")
    assert summary[key] is False


def test_preview_header_lines_exist(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    preview = (tmp_path / "out/preview.md").read_text(encoding="utf-8")
    assert "# LS-NEW-6 WordPress Draft Payload Prep Preview" in preview
    assert "- Status: READY_NO_EXECUTION" in preview
    assert "## post_title" in preview
    assert "## post_content_markdown" in preview


@pytest.mark.parametrize(
    "missing",
    ["policy", "schema", "ls4_payload", "ls4_preview", "ls4_summary", "ls5_result", "ls5_validation", "ls5_record"],
)
def test_missing_input_files_fail(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing" in e for e in result["errors"])


def test_invalid_json_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["ls4_payload"].write_text("{bad", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json ls-new4-wp-payload" in e for e in result["errors"])


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new6_wp_draft_payload_prep.py").read_text(encoding="utf-8")
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