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


def _base_payload() -> dict:
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP",
        "status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "ls_new5_decision_validated": True,
        "ls_new5_decision_approved": True,
        "source_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "approval_label_consumed": False,
        "content_item_id": "new-comic-001",
        "title": "月曜日のたわわ",
        "volume": "第15巻",
        "author": "比村奇石",
        "publisher": "講談社",
        "release_date": "2026-07-06",
        "asin": "B0H6DQLPPB",
        "isbn": "978-4065442296",
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post_title": "t",
        "post_content_markdown": "m",
        "post_content_source": "LS-NEW-4 WP purchase navigation payload dry run",
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "affiliate_disclosure_included": True,
        "external_fetch_notice_included": True,
        "source_unverified_notice_included": True,
        "official_synopsis_copy_included": False,
        "store_description_copy_included": False,
        "review_copy_included": False,
        "long_work_explanation_included": False,
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
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": True,
        "recommended_next_action": "BEGIN_LS_NEW_7_WP_DRAFT_RUNNER_PREP_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-7", "LS-MON-2"],
        "errors": [],
    }


def _base_preview() -> str:
    return "\n".join(
        [
            "# LS-NEW-6 WordPress Draft Payload Prep Preview",
            "",
            "- Phase: LS-NEW-6",
            "- Status: READY_NO_EXECUTION",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Source approval: APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
            "- Approval label consumed: false",
            "",
            "## post_title",
            "t",
            "## post_content_markdown",
            "```markdown",
            "m",
            "```",
            "",
        ]
    )


def _base_safety() -> dict:
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_SAFETY_SUMMARY",
        "status": "LSNEW6_SAFETY_SUMMARY_READY_NO_EXECUTION",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": True,
    }


def _base_result() -> dict:
    payload = _base_payload()
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_RESULT",
        "status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "ls_new5_decision_validated": True,
        "ls_new5_decision_approved": True,
        "source_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "approval_label_consumed": False,
        "wp_draft_payload_created": True,
        "wp_draft_payload_preview_created": True,
        "safety_summary_created": True,
        "content_item_id": payload["content_item_id"],
        "title": payload["title"],
        "volume": payload["volume"],
        "author": payload["author"],
        "publisher": payload["publisher"],
        "release_date": payload["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "affiliate_disclosure_included": True,
        "external_fetch_notice_included": True,
        "source_unverified_notice_included": True,
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
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": True,
        "recommended_next_action": "BEGIN_LS_NEW_7_WP_DRAFT_RUNNER_PREP_NO_EXECUTION",
        "recommended_next_phase_options": ["LS-NEW-7", "LS-MON-2"],
        "errors": [],
    }


def _base_lock() -> dict:
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_LOCK",
        "status": "LSNEW6_WP_DRAFT_PAYLOAD_PREP_LOCKED_NO_EXECUTION",
        "locked": True,
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
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _base_ls5_validation() -> dict:
    return {"validation_status": "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"}


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "payload": tmp_path / "in/payload.json",
        "preview": tmp_path / "in/preview.md",
        "safety": tmp_path / "in/safety.json",
        "result": tmp_path / "in/result.json",
        "lock": tmp_path / "in/lock.json",
        "run_result": tmp_path / "in/run_result.json",
        "ls5_validation": tmp_path / "in/ls5_validation.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["payload"], _base_payload())
    p["preview"].parent.mkdir(parents=True, exist_ok=True)
    p["preview"].write_text(_base_preview(), encoding="utf-8")
    _write_json(p["safety"], _base_safety())
    _write_json(p["result"], _base_result())
    _write_json(p["run_result"], _base_result())
    _write_json(p["lock"], _base_lock())
    _write_json(p["ls5_validation"], _base_ls5_validation())
    return p


def _run(tmp_path: Path, p: dict[str, Path]) -> subprocess.CompletedProcess:
    cmd = [
        "python3",
        "scripts/validate_start_ls_new6_wp_draft_payload_prep.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--payload",
        str(p["payload"]),
        "--preview",
        str(p["preview"]),
        "--safety-summary",
        str(p["safety"]),
        "--result",
        str(p["result"]),
        "--lock",
        str(p["lock"]),
        "--run-result",
        str(p["run_result"]),
        "--ls-new5-decision-validation-result",
        str(p["ls5_validation"]),
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
    assert res.returncode == 0, res.stderr
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"


@pytest.mark.parametrize(
    "path_key",
    ["policy", "schema", "payload", "preview", "safety", "result", "lock", "run_result", "ls5_validation"],
)
def test_missing_inputs(path_key: str, tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p[path_key].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert out["validation_status"] == "LSNEW6_WP_DRAFT_PAYLOAD_PREP_NOT_VALIDATED"


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls5_validation", "validation_status", "BAD", "ls-new5 decision validation mismatch"),
        ("payload", "document_type", "BAD", "payload document_type mismatch"),
        ("payload", "phase", "BAD", "payload phase mismatch"),
        ("payload", "status", "BAD", "payload status mismatch"),
        ("payload", "execution_mode", "BAD", "payload execution_mode mismatch"),
        ("payload", "production_status", "BAD", "payload production_status mismatch"),
        ("payload", "source_approval_label", "BAD", "payload source_approval_label mismatch"),
        ("payload", "post_status_target", "publish", "post_status_target mismatch"),
        ("payload", "target_post_id", 123, "target_post_id must be null"),
        ("payload", "target_post_id_allocated", True, "target_post_id_allocated=true"),
        ("payload", "purchase_navigation_media", False, "purchase_navigation_media mismatch"),
        ("payload", "work_explanation_media", True, "work_explanation_media=true"),
        ("payload", "affiliate_disclosure_included", False, "missing affiliate disclosure"),
        ("payload", "external_fetch_notice_included", False, "missing external fetch notice"),
        ("payload", "source_unverified_notice_included", False, "source_unverified_notice_included mismatch"),
        ("payload", "official_synopsis_copy_included", True, "official_synopsis_copy_included=true"),
        ("payload", "store_description_copy_included", True, "store_description_copy_included=true"),
        ("payload", "review_copy_included", True, "review_copy_included=true"),
        ("payload", "long_work_explanation_included", True, "long_work_explanation_included=true"),
        ("payload", "execution_allowed", True, "execution_allowed=true"),
        ("payload", "ready_for_ls_new_7", False, "ready_for_ls_new_7=false"),
        ("payload", "recommended_next_action", "BAD", "recommended_next_action mismatch"),
    ],
)
def test_payload_constraints(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p[target])
    d[key] = value
    _write_json(p[target], d)
    if target == "payload":
        res = _load(p["result"])
        if key in res:
            res[key] = value
            _write_json(p["result"], res)
            _write_json(p["run_result"], res)
    r = _run(tmp_path, p)
    assert r.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
        ("wordpress_api_call_executed", "wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "wordpress_write_executed=true"),
        ("wordpress_draft_created", "wordpress_draft_created=true"),
        ("wordpress_publish_executed", "wordpress_publish_executed=true"),
        ("x_post_executed", "x_post_executed=true"),
        ("external_fetch_executed", "external_fetch_executed=true"),
        ("http_get_executed", "http_get_executed=true"),
        ("credential_env_read_executed", "credential_env_read_executed=true"),
        ("credential_secret_output", "credential_secret_output=true"),
        ("post119_update_executed", "post119_update_executed=true"),
        ("post183_update_executed", "post183_update_executed=true"),
        ("candidate_selected", "candidate_selected=true"),
        ("ls_next1_fill_updated", "ls_next1_fill_updated=true"),
    ],
)
def test_detects_forbidden_true_payload_flags(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["payload"])
    d[key] = True
    _write_json(p["payload"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,error",
    [
        ("wordpress_api_call_executed", "safety wordpress_api_call_executed=true"),
        ("wordpress_write_executed", "safety wordpress_write_executed=true"),
        ("wordpress_draft_created", "safety wordpress_draft_created=true"),
        ("wordpress_publish_executed", "safety wordpress_publish_executed=true"),
        ("x_api_call_executed", "safety x_api_call_executed=true"),
        ("x_post_executed", "safety x_post_executed=true"),
        ("external_fetch_executed", "safety external_fetch_executed=true"),
        ("http_get_executed", "safety http_get_executed=true"),
        ("credential_env_read_executed", "safety credential_env_read_executed=true"),
        ("target_post_id_allocated", "safety target_post_id_allocated=true"),
        ("approval_label_consumed", "safety approval_label_consumed=true"),
        ("execution_allowed", "safety execution_allowed=true"),
    ],
)
def test_detects_forbidden_true_safety_flags(tmp_path: Path, key: str, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["safety"])
    d[key] = True
    _write_json(p["safety"], d)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("status", "BAD", "result status mismatch"),
        ("execution_mode", "BAD", "result execution_mode mismatch"),
        ("production_status", "BAD", "result production_status mismatch"),
        ("wp_draft_payload_created", False, "wp_draft_payload_created mismatch"),
        ("wp_draft_payload_preview_created", False, "wp_draft_payload_preview_created mismatch"),
        ("safety_summary_created", False, "safety_summary_created mismatch"),
        ("execution_allowed", True, "result execution_allowed=true"),
    ],
)
def test_result_constraints(tmp_path: Path, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["result"])
    d[key] = value
    _write_json(p["result"], d)
    _write_json(p["run_result"], d)
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
    "key,value,error",
    [
        ("phase", "BAD", "lock phase mismatch"),
        ("document_type", "BAD", "lock document_type mismatch"),
        ("status", "BAD", "lock status mismatch"),
        ("locked", False, "lock mismatch"),
        ("execution_allowed", True, "lock execution_allowed=true"),
        ("approval_label_consumed", True, "lock approval_label_consumed=true"),
        ("target_post_id_allocated", True, "lock target_post_id_allocated=true"),
    ],
)
def test_lock_constraints(tmp_path: Path, key: str, value, error: str) -> None:
    p = _prepare(tmp_path)
    lock = _load(p["lock"])
    lock[key] = value
    _write_json(p["lock"], lock)
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


@pytest.mark.parametrize(
    "line,error",
    [
        ("- Phase: LS-NEW-6", "preview missing line: - Phase: LS-NEW-6"),
        (
            "- Source approval: APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
            "preview missing line: - Source approval: APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
        ),
    ],
)
def test_preview_required_lines(tmp_path: Path, line: str, error: str) -> None:
    p = _prepare(tmp_path)
    text = p["preview"].read_text(encoding="utf-8")
    p["preview"].write_text(text.replace(line, ""), encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert error in out["errors"]


def test_preview_header_mismatch(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["preview"].write_text("bad\n", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    out = _load(tmp_path / "out/validation.json")
    assert "preview header mismatch" in out["errors"]


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/validate_start_ls_new6_wp_draft_payload_prep.py").read_text(encoding="utf-8")
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