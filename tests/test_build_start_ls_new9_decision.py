from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_policy() -> dict:
    return {"phase": "LS-NEW-9-DECISION"}


def _base_schema() -> dict:
    return {"phase": "LS-NEW-9-DECISION"}


def _base_ls9_result() -> dict:
    return {
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION",
        "ready_for_ls_new_9_decision": True,
        "ready_for_ls_new_10": False,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "target_post_id_allocated": False,
    }


def _base_ls9_validation() -> dict:
    return {"validation_status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"}


def _base_approval_request() -> dict:
    return {"phase": "LS-NEW-9"}


def _base_decision_template() -> dict:
    return {"phase": "LS-NEW-9", "instructions": "Human reviewer must fill this manually. AI must not auto-approve."}


def _base_decision_input() -> dict:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_INPUT",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "ready_for_ls_new_10": False,
    }


def _prepare(tmp_path: Path) -> dict[str, Path]:
    p = {
        "policy": tmp_path / "in/policy.json",
        "schema": tmp_path / "in/schema.json",
        "ls9_result": tmp_path / "in/ls9_result.json",
        "ls9_validation": tmp_path / "in/ls9_validation.json",
        "approval_request": tmp_path / "in/approval_request.json",
        "decision_template": tmp_path / "in/decision_template.json",
        "decision_input": tmp_path / "in/decision_input.json",
    }
    _write_json(p["policy"], _base_policy())
    _write_json(p["schema"], _base_schema())
    _write_json(p["ls9_result"], _base_ls9_result())
    _write_json(p["ls9_validation"], _base_ls9_validation())
    _write_json(p["approval_request"], _base_approval_request())
    _write_json(p["decision_template"], _base_decision_template())
    _write_json(p["decision_input"], _base_decision_input())
    return p


def _run(tmp_path: Path, p: dict[str, Path], flags: list[str] | None = None) -> subprocess.CompletedProcess:
    out = {
        "decision_record": tmp_path / "out/decision_record.json",
        "result": tmp_path / "out/result.json",
        "lock": tmp_path / "out/lock.json",
        "report": tmp_path / "out/report.md",
    }
    cmd = [
        "python3",
        "scripts/build_start_ls_new9_decision.py",
        "--policy",
        str(p["policy"]),
        "--schema",
        str(p["schema"]),
        "--ls-new9-result",
        str(p["ls9_result"]),
        "--ls-new9-validation-result",
        str(p["ls9_validation"]),
        "--ls-new9-approval-request",
        str(p["approval_request"]),
        "--ls-new9-decision-template",
        str(p["decision_template"]),
        "--decision-input",
        str(p["decision_input"]),
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


def test_valid_not_approved(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW9_DECISION_NOT_APPROVED_NO_EXECUTION"
    assert result["ready_for_ls_new_10"] is False
    assert result["recommended_next_action"] == "WAIT_OR_REVIEW_REWORK"


def test_valid_approved(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d["human_approval_completed"] = True
    d["human_approved_for_execution"] = True
    d["approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    d["reviewer_notes"] = "Separate execution approval reviewed. Approved for LS-NEW-10 execution-prep only."
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["status"] == "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"
    assert result["ready_for_ls_new_10"] is True
    assert result["recommended_next_action"] == "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY"


def test_approval_label_trimmed_match(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d["human_approval_completed"] = True
    d["human_approved_for_execution"] = True
    d["approval_label"] = "  APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY  "
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_10"] is True
    assert result["normalized_approval_label"] == "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"


@pytest.mark.parametrize("label", ["APPROVED_FOR_LS_NEW_9", "approved_for_ls_new_9_separate_execution_approval_gate_only"])
def test_approval_label_mismatch_cases(tmp_path: Path, label: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d["human_approval_completed"] = True
    d["human_approved_for_execution"] = True
    d["approval_label"] = label
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_10"] is False


@pytest.mark.parametrize(
    "target,key,value,error",
    [
        ("policy", "phase", "BAD", "policy phase mismatch"),
        ("schema", "phase", "BAD", "schema phase mismatch"),
        ("ls9_result", "status", "BAD", "ls-new9 run status mismatch"),
        ("ls9_validation", "validation_status", "BAD", "ls-new9 validation status mismatch"),
        ("ls9_result", "ready_for_ls_new_9_decision", False, "ls-new9 ready_for_ls_new_9_decision mismatch"),
        ("ls9_result", "ready_for_ls_new_10", True, "ls-new9 ready_for_ls_new_10 mismatch"),
        ("ls9_result", "human_approval_required", False, "ls-new9 human_approval_required mismatch"),
        ("ls9_result", "human_approval_completed", True, "ls-new9 human_approval_completed mismatch"),
        ("ls9_result", "human_approved_for_execution", True, "ls-new9 human_approved_for_execution mismatch"),
        ("ls9_result", "execution_allowed", True, "ls-new9 execution_allowed mismatch"),
        ("ls9_result", "runner_execution_allowed", True, "ls-new9 runner_execution_allowed mismatch"),
        ("ls9_result", "final_execution_command_created", True, "ls-new9 final_execution_command_created mismatch"),
        ("ls9_result", "wordpress_api_call_executed", True, "ls-new9 wordpress_api_call_executed=true"),
        ("ls9_result", "wordpress_draft_created", True, "ls-new9 wordpress_draft_created=true"),
        ("ls9_result", "credential_env_read_executed", True, "ls-new9 credential_env_read_executed=true"),
        ("ls9_result", "credential_existence_check_executed", True, "ls-new9 credential_existence_check_executed=true"),
        ("ls9_result", "target_post_id_allocated", True, "ls-new9 target_post_id_allocated=true"),
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


@pytest.mark.parametrize("missing", ["policy", "schema", "ls9_result", "ls9_validation", "approval_request", "decision_template", "decision_input"])
def test_missing_input_files(tmp_path: Path, missing: str) -> None:
    p = _prepare(tmp_path)
    p[missing].unlink()
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("missing" in e for e in result["errors"])


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
def test_missing_flags(tmp_path: Path, missing_flag: str) -> None:
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
    "key,warning",
    [
        ("execution_allowed", "input_execution_allowed_true_forced_false"),
        ("runner_execution_allowed", "input_runner_execution_allowed_true_forced_false"),
        ("final_execution_command_created", "input_final_execution_command_created_true_forced_false"),
    ],
)
def test_true_input_forbidden_flags_record_warnings(tmp_path: Path, key: str, warning: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d["human_approval_completed"] = True
    d["human_approved_for_execution"] = True
    d["approval_label"] = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
    d[key] = True
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_10"] is False
    assert warning in result["warnings"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("human_approval_completed", "true"),
        ("human_approved_for_execution", "true"),
        ("execution_allowed", "false"),
        ("runner_execution_allowed", "false"),
        ("final_execution_command_created", "false"),
    ],
)
def test_invalid_boolean_type(tmp_path: Path, key: str, value: str) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d[key] = value
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_10"] is False
    assert "invalid_boolean_type" in result["warnings"]


def test_ready_input_ignored(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    d = _load(p["decision_input"])
    d["ready_for_ls_new_10"] = True
    _write_json(p["decision_input"], d)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result["ready_for_ls_new_10"] is False


@pytest.mark.parametrize(
    "key",
    [
        "approval_label_consumed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "approval_label_autofill_executed",
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
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_result_fixed_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    result = _load(tmp_path / "out/result.json")
    assert result[key] is False


@pytest.mark.parametrize(
    "key",
    [
        "approval_label_consumed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "approval_label_autofill_executed",
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
        "target_post_id_allocated",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ],
)
def test_lock_fixed_false_flags(tmp_path: Path, key: str) -> None:
    p = _prepare(tmp_path)
    res = _run(tmp_path, p)
    assert res.returncode == 0
    lock = _load(tmp_path / "out/lock.json")
    assert lock[key] is False


def test_invalid_json_input_fails(tmp_path: Path) -> None:
    p = _prepare(tmp_path)
    p["decision_input"].write_text("{bad", encoding="utf-8")
    res = _run(tmp_path, p)
    assert res.returncode != 0
    result = _load(tmp_path / "out/result.json")
    assert any("invalid json decision-input" in e for e in result["errors"])


def test_source_code_forbidden_pattern_scan() -> None:
    src = Path("scripts/build_start_ls_new9_decision.py").read_text(encoding="utf-8")
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
