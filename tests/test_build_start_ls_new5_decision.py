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
        "phase": "LS-NEW-5-DECISION",
        "allowed_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_schema() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "allowed_approval_label": "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
    }


def _base_ls_new5_result() -> dict:
    return {
        "status": "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION",
        "execution_allowed": False,
        "human_review_required": True,
        "human_review_completed": False,
        "human_approved": False,
        "ready_for_ls_new_6": False,
    }


def _base_ls_new5_validation() -> dict:
    return {
        "validation_status": "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION",
    }


def _base_input() -> dict:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_INPUT",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
        "ready_for_ls_new_6": False,
    }


def _prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls_new5_result": tmp_path / "in/ls_new5_result.json",
        "ls_new5_validation": tmp_path / "in/ls_new5_validation.json",
        "decision_input": tmp_path / "in/decision_input.json",
    }
    _write_json(paths["policy"], _base_policy())
    _write_json(paths["schema"], _base_schema())
    _write_json(paths["ls_new5_result"], _base_ls_new5_result())
    _write_json(paths["ls_new5_validation"], _base_ls_new5_validation())
    _write_json(paths["decision_input"], _base_input())
    return paths


def _run_build(tmp_path: Path, paths: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "decision_record": tmp_path / "out/decision_record.json",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new5_decision.py",
        "--policy",
        str(paths["policy"]),
        "--schema",
        str(paths["schema"]),
        "--ls-new5-result",
        str(paths["ls_new5_result"]),
        "--ls-new5-validation-result",
        str(paths["ls_new5_validation"]),
        "--decision-input",
        str(paths["decision_input"]),
        "--output-decision-record",
        str(out["decision_record"]),
        "--output",
        str(out["result"]),
        "--lock-output",
        str(out["lock"]),
        "--report",
        str(out["report"]),
    ]

    required_flags = [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
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
    cmd.extend(required_flags if flags is None else flags)
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_default_not_approved(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0, res.stderr
    result = _load(tmp_path / "out/result.json")
    record = _load(tmp_path / "out/decision_record.json")
    assert result["status"] == "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION"
    assert result["ready_for_ls_new_6"] is False
    assert result["recommended_next_action"] == "WAIT_OR_REVIEW_REWORK"
    assert result["execution_allowed"] is False
    assert result["approval_label_consumed"] is False
    assert result["warnings"] == []
    assert record["status"] == result["status"]


def test_build_approved_exact_label(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision["human_review_completed"] = True
    decision["human_approved"] = True
    decision["approval_label"] = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    decision["reviewer_notes"] = "ok"
    _write_json(paths["decision_input"], decision)

    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION"
    assert result["ready_for_ls_new_6"] is True
    assert result["recommended_next_action"] == "PROCEED_TO_LS_NEW_6_PREP_ONLY"


def test_build_approved_trimmed_label(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision["human_review_completed"] = True
    decision["human_approved"] = True
    decision["approval_label"] = "  APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY  "
    _write_json(paths["decision_input"], decision)

    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_6"] is True
    assert result["normalized_approval_label"] == "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def test_execution_allowed_true_forced_false(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision["human_review_completed"] = True
    decision["human_approved"] = True
    decision["approval_label"] = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"
    decision["execution_allowed"] = True
    _write_json(paths["decision_input"], decision)

    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["execution_allowed"] is False
    assert result["ready_for_ls_new_6"] is False
    assert "input_execution_allowed_true_forced_false" in result["warnings"]


def test_ready_input_is_ignored(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision["ready_for_ls_new_6"] = True
    _write_json(paths["decision_input"], decision)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_6"] is False


@pytest.mark.parametrize(
    "bad_field,bad_value",
    [
        ("human_review_completed", "true"),
        ("human_approved", "true"),
        ("execution_allowed", "false"),
    ],
)
def test_invalid_boolean_type_warning(tmp_path: Path, bad_field: str, bad_value) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision[bad_field] = bad_value
    _write_json(paths["decision_input"], decision)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_6"] is False
    assert "invalid_boolean_type" in result["warnings"]


@pytest.mark.parametrize(
    "label",
    [
        "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP",
        "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY_X",
        "approved_for_ls_new_6_wp_draft_payload_prep_only",
        "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ ONLY",
        " APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLYX",
    ],
)
def test_label_mismatch_cases(tmp_path: Path, label: str) -> None:
    paths = _prepare_inputs(tmp_path)
    decision = _load(paths["decision_input"])
    decision["human_review_completed"] = True
    decision["human_approved"] = True
    decision["approval_label"] = label
    _write_json(paths["decision_input"], decision)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION"


@pytest.mark.parametrize(
    "mutator,error",
    [
        (lambda d: d.update({"phase": "LS-NEW-X"}), "policy phase mismatch"),
        (lambda d: d.update({"phase": "LS-NEW-X"}), "schema phase mismatch"),
    ],
)
def test_policy_schema_mismatch(tmp_path: Path, mutator, error: str) -> None:
    paths = _prepare_inputs(tmp_path)
    if "policy" in error:
        d = _load(paths["policy"])
        mutator(d)
        _write_json(paths["policy"], d)
    else:
        d = _load(paths["schema"])
        mutator(d)
        _write_json(paths["schema"], d)

    res = _run_build(tmp_path, paths)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("ls_new5_result", "status", "BAD", "ls-new5 status mismatch"),
        ("ls_new5_validation", "validation_status", "BAD", "ls-new5 validation mismatch"),
        ("ls_new5_result", "execution_allowed", True, "ls-new5 execution_allowed mismatch"),
        ("ls_new5_result", "human_review_required", False, "ls-new5 human_review_required mismatch"),
        ("ls_new5_result", "human_review_completed", True, "ls-new5 human_review_completed mismatch"),
        ("ls_new5_result", "human_approved", True, "ls-new5 human_approved mismatch"),
        ("ls_new5_result", "ready_for_ls_new_6", True, "ls-new5 ready_for_ls_new_6 mismatch"),
        ("policy", "allowed_approval_label", "BAD", "policy allowed approval label mismatch"),
        ("schema", "allowed_approval_label", "BAD", "schema allowed approval label mismatch"),
    ],
)
def test_previous_phase_and_label_constraints(tmp_path: Path, target: str, key: str, value, error: str) -> None:
    paths = _prepare_inputs(tmp_path)
    d = _load(paths[target])
    d[key] = value
    _write_json(paths[target], d)

    res = _run_build(tmp_path, paths)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert error in result["errors"]


@pytest.mark.parametrize(
    "missing_flag",
    [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
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
    paths = _prepare_inputs(tmp_path)
    all_flags = [
        "--require-no-external-fetch",
        "--require-no-http-get",
        "--require-no-wordpress-api",
        "--require-no-wordpress-write",
        "--require-no-wordpress-draft",
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
    flags = [f for f in all_flags if f != missing_flag]
    res = _run_build(tmp_path, paths, flags=flags)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any(missing_flag in e for e in result["errors"])


@pytest.mark.parametrize(
    "key",
    [
        "auto_approval_executed",
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_result_safety_flags_are_false(tmp_path: Path, key: str) -> None:
    paths = _prepare_inputs(tmp_path)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result[key] is False


def test_missing_input_file_fails(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    paths["decision_input"].unlink()
    res = _run_build(tmp_path, paths)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing decision-input" in e for e in result["errors"])


def test_invalid_json_fails(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    paths["decision_input"].write_text("{bad", encoding="utf-8")
    res = _run_build(tmp_path, paths)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json decision-input" in e for e in result["errors"])


def test_lock_payload_defaults(tmp_path: Path) -> None:
    paths = _prepare_inputs(tmp_path)
    res = _run_build(tmp_path, paths)
    assert res.returncode == 0
    lock = _load(tmp_path / "out/lock.json")
    assert lock["status"] == "LSNEW5_DECISION_LOCKED_NO_EXECUTION"
    assert lock["locked"] is True
    assert lock["execution_allowed"] is False


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new5_decision.py").read_text(encoding="utf-8")
    forbidden = [
        "requests.",
        "urllib.request",
        "wp-json",
        "/wp/v2/posts",
        "/etc/ai-media-os/credential.env",
        "http.client",
        "Authorization:",
    ]
    assert all(x not in src for x in forbidden)