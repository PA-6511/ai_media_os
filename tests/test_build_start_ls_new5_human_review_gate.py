from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_GATE_POLICY",
    }


def _base_schema() -> dict:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_CHECKLIST_SCHEMA",
    }


def _base_ls4_result() -> dict:
    return {
        "phase": "LS-NEW-4",
        "status": "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION",
        "ready_for_ls_new_5_human_review": True,
        "execution_allowed": False,
        "content_item_id": "CID-001",
        "title": "テスト作品",
        "volume": "1",
        "author": "著者A",
        "publisher": "出版社A",
        "release_date": "2026-01-10",
        "asin": "B0TEST0001",
        "isbn": "9781234567890",
    }


def _base_ls4_validation() -> dict:
    return {
        "validation_status": "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION",
    }


def _base_wp_payload() -> dict:
    return {
        "post_title": "[PR] テスト作品 1巻",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
    }


def _base_x_payload() -> dict:
    text = "[PR] テスト作品 1巻 URL: https://example.invalid/item #PR #著者A"
    return {
        "post_text": text,
        "character_count": len(text),
        "under_280": True,
        "x_api_call_executed": False,
        "x_post_executed": False,
    }


def _base_summary() -> dict:
    return {
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "x_post_under_280": True,
    }


def _prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    inputs = {
        "policy": tmp_path / "config/policy.json",
        "schema": tmp_path / "config/schema.json",
        "ls4_result": tmp_path / "in/ls4_result.json",
        "ls4_validation": tmp_path / "in/ls4_validation.json",
        "wp_payload": tmp_path / "in/wp_payload.json",
        "wp_preview": tmp_path / "in/wp_preview.md",
        "x_payload": tmp_path / "in/x_payload.json",
        "summary": tmp_path / "in/summary.json",
    }
    _write_json(inputs["policy"], _base_policy())
    _write_json(inputs["schema"], _base_schema())
    _write_json(inputs["ls4_result"], _base_ls4_result())
    _write_json(inputs["ls4_validation"], _base_ls4_validation())
    _write_json(inputs["wp_payload"], _base_wp_payload())
    inputs["wp_preview"].parent.mkdir(parents=True, exist_ok=True)
    inputs["wp_preview"].write_text("WordPress write executed: false\n", encoding="utf-8")
    _write_json(inputs["x_payload"], _base_x_payload())
    _write_json(inputs["summary"], _base_summary())
    return inputs


def _run_build(tmp_path: Path, inputs: dict[str, Path], extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "review_request": tmp_path / "out/review_request.json",
        "checklist": tmp_path / "out/checklist.template.json",
        "decision_template": tmp_path / "out/decision.template.json",
        "decision_record": tmp_path / "out/decision.json",
        "wp_snapshot": tmp_path / "out/wp_snapshot.md",
        "x_snapshot": tmp_path / "out/x_snapshot.md",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new5_human_review_gate.py",
        "--policy",
        str(inputs["policy"]),
        "--schema",
        str(inputs["schema"]),
        "--ls-new4-result",
        str(inputs["ls4_result"]),
        "--ls-new4-validation-result",
        str(inputs["ls4_validation"]),
        "--wp-payload",
        str(inputs["wp_payload"]),
        "--wp-preview",
        str(inputs["wp_preview"]),
        "--x-payload",
        str(inputs["x_payload"]),
        "--payload-validation-summary",
        str(inputs["summary"]),
        "--output-review-request",
        str(out["review_request"]),
        "--output-checklist-template",
        str(out["checklist"]),
        "--output-decision-template",
        str(out["decision_template"]),
        "--output-decision-record",
        str(out["decision_record"]),
        "--output-wp-review-snapshot",
        str(out["wp_snapshot"]),
        "--output-x-review-snapshot",
        str(out["x_snapshot"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-credential-read",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-auto-approval",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_success_creates_outputs(tmp_path: Path) -> None:
    inputs = _prepare_inputs(tmp_path)
    res = _run_build(tmp_path, inputs)
    assert res.returncode == 0, res.stderr

    result = _load(tmp_path / "out/result.json")
    lock = _load(tmp_path / "out/lock.json")
    review_request = _load(tmp_path / "out/review_request.json")
    decision = _load(tmp_path / "out/decision.json")

    assert result["status"] == "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION"
    assert result["production_status"] == "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION"
    assert result["human_review_completed"] is False
    assert result["human_approved"] is False
    assert result["approval_label"] == ""
    assert result["ready_for_ls_new_6"] is False
    assert result["execution_allowed"] is False
    assert result["errors"] == []

    assert review_request["review_required"] is True
    assert review_request["review_completed"] is False
    assert review_request["human_approved"] is False

    assert decision["human_review_completed"] is False
    assert decision["human_approved"] is False
    assert decision["approval_label"] == ""

    assert lock["locked"] is True
    assert lock["execution_allowed"] is False


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-credential-read",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-auto-approval",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ],
)
def test_missing_required_flag_fails(tmp_path: Path, missing_flag: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    # Build command manually without one mandatory flag.
    base = _run_build(tmp_path, inputs)
    assert base.returncode == 0

    cmd = [
        "python3",
        "scripts/build_start_ls_new5_human_review_gate.py",
        "--policy",
        str(inputs["policy"]),
        "--schema",
        str(inputs["schema"]),
        "--ls-new4-result",
        str(inputs["ls4_result"]),
        "--ls-new4-validation-result",
        str(inputs["ls4_validation"]),
        "--wp-payload",
        str(inputs["wp_payload"]),
        "--wp-preview",
        str(inputs["wp_preview"]),
        "--x-payload",
        str(inputs["x_payload"]),
        "--payload-validation-summary",
        str(inputs["summary"]),
        "--output-review-request",
        str(tmp_path / "out2/review_request.json"),
        "--output-checklist-template",
        str(tmp_path / "out2/checklist.template.json"),
        "--output-decision-template",
        str(tmp_path / "out2/decision.template.json"),
        "--output-decision-record",
        str(tmp_path / "out2/decision.json"),
        "--output-wp-review-snapshot",
        str(tmp_path / "out2/wp_snapshot.md"),
        "--output-x-review-snapshot",
        str(tmp_path / "out2/x_snapshot.md"),
        "--output",
        str(tmp_path / "out2/result.json"),
        "--lock-output",
        str(tmp_path / "out2/lock.json"),
        "--report",
        str(tmp_path / "out2/report.md"),
    ]
    all_flags = [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-credential-read",
        "--require-no-amazon-api",
        "--require-no-x-api",
        "--require-no-x-post",
        "--require-no-auto-approval",
        "--require-no-candidate-selection",
        "--require-no-ls-next1-fill-update",
        "--forbid-post119-update",
        "--forbid-post183-update",
    ]
    cmd.extend([f for f in all_flags if f != missing_flag])

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    result = _load(tmp_path / "out2/result.json")
    assert result["status"] == "LSNEW5_HUMAN_REVIEW_GATE_FAILED_NO_EXECUTION"
    assert any(missing_flag in e for e in result["errors"])


@pytest.mark.parametrize(
    "mutator, expected_error",
    [
        (lambda d: d.update({"phase": "LS-NEW-X"}), "policy phase mismatch"),
        (lambda d: d.update({"phase": "LS-NEW-X"}), "schema phase mismatch"),
    ],
)
def test_policy_schema_phase_mismatch(tmp_path: Path, mutator, expected_error: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    if "policy" in expected_error:
        data = _load(inputs["policy"])
        mutator(data)
        _write_json(inputs["policy"], data)
    else:
        data = _load(inputs["schema"])
        mutator(data)
        _write_json(inputs["schema"], data)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert expected_error in result["errors"]


@pytest.mark.parametrize(
    "mutator, expected",
    [
        (lambda d: d.update({"status": "BAD"}), "ls-new4 status mismatch"),
        (lambda d: d.update({"ready_for_ls_new_5_human_review": False}), "ready_for_ls_new_5_human_review mismatch"),
        (lambda d: d.update({"execution_allowed": True}), "execution_allowed mismatch"),
    ],
)
def test_ls4_result_gate_checks(tmp_path: Path, mutator, expected: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs["ls4_result"])
    mutator(d)
    _write_json(inputs["ls4_result"], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert expected in result["errors"]


@pytest.mark.parametrize("field", ["content_item_id", "title", "volume", "author", "publisher", "release_date", "asin", "isbn"])
def test_missing_candidate_field_fails(tmp_path: Path, field: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs["ls4_result"])
    d[field] = ""
    _write_json(inputs["ls4_result"], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert f"missing required candidate field: {field}" in result["errors"]


@pytest.mark.parametrize(
    "key,value,error",
    [
        ("purchase_navigation_media", False, "payload summary purchase_navigation_media mismatch"),
        ("work_explanation_media", True, "payload summary work_explanation_media mismatch"),
        ("x_post_under_280", False, "payload summary x_post_under_280 mismatch"),
    ],
)
def test_payload_summary_checks(tmp_path: Path, key: str, value, error: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs["summary"])
    d[key] = value
    _write_json(inputs["summary"], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "target,key,error",
    [
        ("wp_payload", "wordpress_api_call_executed", "wp payload wordpress_api_call_executed=true"),
        ("wp_payload", "wordpress_write_executed", "wp payload wordpress_write_executed=true"),
        ("x_payload", "x_api_call_executed", "x payload x_api_call_executed=true"),
        ("x_payload", "x_post_executed", "x payload x_post_executed=true"),
    ],
)
def test_payload_execution_flags_must_be_false(tmp_path: Path, target: str, key: str, error: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs[target])
    d[key] = True
    _write_json(inputs[target], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "missing_key",
    [
        "policy",
        "schema",
        "ls4_result",
        "ls4_validation",
        "wp_payload",
        "wp_preview",
        "x_payload",
        "summary",
    ],
)
def test_missing_input_file_fails(tmp_path: Path, missing_key: str) -> None:
    inputs = _prepare_inputs(tmp_path)
    inputs[missing_key].unlink()

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing" in e for e in result["errors"])


def test_invalid_json_input_fails(tmp_path: Path) -> None:
    inputs = _prepare_inputs(tmp_path)
    inputs["x_payload"].write_text("{bad json", encoding="utf-8")

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json x-payload" in e for e in result["errors"])


def test_generated_files_content_sanity(tmp_path: Path) -> None:
    inputs = _prepare_inputs(tmp_path)
    res = _run_build(tmp_path, inputs)
    assert res.returncode == 0

    review = _load(tmp_path / "out/review_request.json")
    checklist = _load(tmp_path / "out/checklist.template.json")
    decision_template = _load(tmp_path / "out/decision.template.json")
    decision = _load(tmp_path / "out/decision.json")

    assert review["approval_label_required_for_next"] == "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    assert checklist["human_decision"]["approval_label"] == ""
    assert decision_template["allowed_approval_label"] == "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    assert decision["status"] == "LSNEW5_HUMAN_REVIEW_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION"

    wp_snapshot = (tmp_path / "out/wp_snapshot.md").read_text(encoding="utf-8")
    x_snapshot = (tmp_path / "out/x_snapshot.md").read_text(encoding="utf-8")
    assert "WordPress write executed: false" in wp_snapshot
    assert "X post executed: false" in x_snapshot


def test_report_is_written_on_failure(tmp_path: Path) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs["ls4_result"])
    d["status"] = "BAD"
    _write_json(inputs["ls4_result"], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    report = (tmp_path / "out/report.md").read_text(encoding="utf-8")
    assert "LS-NEW-5 Human Review Gate Report" in report
    assert "ls-new4 status mismatch" in report


def test_no_optional_outputs_created_when_failed(tmp_path: Path) -> None:
    inputs = _prepare_inputs(tmp_path)
    d = _load(inputs["summary"])
    d["x_post_under_280"] = False
    _write_json(inputs["summary"], d)

    res = _run_build(tmp_path, inputs)
    assert res.returncode != 0
    assert not (tmp_path / "out/review_request.json").exists()
    assert (tmp_path / "out/result.json").exists()


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new5_human_review_gate.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.get(",
        "httpx.get(",
        "boto3",
        "tweepy",
        "wp-json/wp/v2",
    ]
    assert all(p not in src for p in forbidden)
