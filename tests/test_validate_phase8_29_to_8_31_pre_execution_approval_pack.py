import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate import (  # noqa: E402
    validate_phase8_29,
)
from validate_phase8_30_final_preflight_before_single_controlled_draft_creation import (  # noqa: E402
    validate_phase8_30,
)
from validate_phase8_31_human_execution_approval_validation_handoff import (  # noqa: E402
    validate_phase8_31,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_prereq_evidence(tmp_path: Path) -> None:
    for rel in [
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json",
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json",
        "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json",
        "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json",
        "exchange/logs/phase8_26_to_8_28_final_pre_execution_decision_pack_overall_report.json",
    ]:
        src = ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _tmp_case_phase29(
    tmp_path: Path,
    monkeypatch,
    env_values: dict[str, str] | None = None,
    policy_patch: dict | None = None,
    request_patch: dict | None = None,
):
    policy = _load(ROOT / "config/phase8_29_credential_readiness_recheck_no_secret_leak_gate_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_29_credential_readiness_recheck_no_secret_leak_gate_request.example.json")
    if policy_patch:
        policy.update(policy_patch)
    if request_patch:
        request.update(request_patch)

    p = tmp_path / "config/policy29.json"
    r = tmp_path / "exchange/examples/request29.json"
    out = tmp_path / "exchange/logs/result29.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    r.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(policy), encoding="utf-8")
    r.write_text(json.dumps(request), encoding="utf-8")

    (tmp_path / "config/phase8_16_credential_readiness_no_secret_leak_final_gate_policy.json").write_text(
        (ROOT / "config/phase8_16_credential_readiness_no_secret_leak_final_gate_policy.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    _copy_prereq_evidence(tmp_path)

    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)
    if env_values:
        for key, value in env_values.items():
            monkeypatch.setenv(key, value)

    return validate_phase8_29(policy_path=p, request_path=r, output_json_path=out)


def _tmp_case_phase30(
    tmp_path: Path,
    phase29_payload: dict,
    policy_patch: dict | None = None,
    request_patch: dict | None = None,
):
    policy = _load(ROOT / "config/phase8_30_final_preflight_before_single_controlled_draft_creation_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_30_final_preflight_before_single_controlled_draft_creation_request.example.json")
    if policy_patch:
        policy.update(policy_patch)
    if request_patch:
        request.update(request_patch)

    p = tmp_path / "config/policy30.json"
    r = tmp_path / "exchange/examples/request30.json"
    result29 = tmp_path / "exchange/logs/phase8_29_credential_readiness_recheck_no_secret_leak_gate_result.json"
    out = tmp_path / "exchange/logs/result30.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    r.parent.mkdir(parents=True, exist_ok=True)
    result29.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(policy), encoding="utf-8")
    r.write_text(json.dumps(request), encoding="utf-8")
    result29.write_text(json.dumps(phase29_payload), encoding="utf-8")

    _copy_prereq_evidence(tmp_path)

    return validate_phase8_30(policy_path=p, request_path=r, phase29_result_path=result29, output_json_path=out)


def _tmp_case_phase31(
    tmp_path: Path,
    phase30_payload: dict,
    human_patch: dict | None = None,
    policy_patch: dict | None = None,
    request_patch: dict | None = None,
):
    policy = _load(ROOT / "config/phase8_31_human_execution_approval_validation_handoff_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_31_human_execution_approval_validation_handoff_request.example.json")
    human = _load(ROOT / "exchange/examples/phase8_31_human_execution_approval.example.json")
    if policy_patch:
        policy.update(policy_patch)
    if request_patch:
        request.update(request_patch)
    if human_patch:
        human.update(human_patch)

    p = tmp_path / "config/policy31.json"
    r = tmp_path / "exchange/examples/request31.json"
    h = tmp_path / "exchange/examples/human31.json"
    result30 = tmp_path / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_result.json"
    out = tmp_path / "exchange/logs/result31.json"

    p.parent.mkdir(parents=True, exist_ok=True)
    r.parent.mkdir(parents=True, exist_ok=True)
    h.parent.mkdir(parents=True, exist_ok=True)
    result30.parent.mkdir(parents=True, exist_ok=True)

    p.write_text(json.dumps(policy), encoding="utf-8")
    r.write_text(json.dumps(request), encoding="utf-8")
    h.write_text(json.dumps(human), encoding="utf-8")
    result30.write_text(json.dumps(phase30_payload), encoding="utf-8")

    _copy_prereq_evidence(tmp_path)

    return validate_phase8_31(
        policy_path=p,
        request_path=r,
        human_approval_path=h,
        phase30_result_path=result30,
        output_json_path=out,
    )


def test_phase829_credentials_ready(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={
            "WORDPRESS_BASE_URL": "https://example.invalid",
            "WORDPRESS_USERNAME": "operator",
            "WORDPRESS_APP_PASSWORD": "dummy-secret-value",
        },
    )
    assert payload["final_status"] == "CREDENTIAL_RECHECK_READY_NO_SECRET_LEAK_NO_EXECUTION"
    assert payload["credentials_ready"] is True
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False
    assert payload["secret_values_output"] is False


def test_phase829_credentials_not_ready(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={
            "WORDPRESS_BASE_URL": "",
            "WORDPRESS_USERNAME": "",
        },
    )
    assert payload["final_status"] == "CREDENTIAL_RECHECK_NOT_READY_NO_SECRET_OUTPUT_NO_EXECUTION"
    assert payload["credentials_not_ready"] is True
    assert payload["execution_allowed"] is False
    dumped = json.dumps(payload, ensure_ascii=False)
    assert "dummy-secret-value" not in dumped


def test_phase830_preflight_ready(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={
            "WORDPRESS_BASE_URL": "https://example.invalid",
            "WORDPRESS_USERNAME": "operator",
            "WORDPRESS_APP_PASSWORD": "dummy-secret-value",
        },
    )
    payload = _tmp_case_phase30(tmp_path, phase29)
    assert payload["final_status"] == "FINAL_PREFLIGHT_READY_BUT_NO_EXECUTION"
    assert payload["actual_go_decision_issued"] is False
    assert payload["execution_allowed"] is False


def test_phase830_preflight_blocked(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": ""})
    payload = _tmp_case_phase30(tmp_path, phase29)
    assert payload["final_status"] == "FINAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["execution_allowed"] is False


def test_phase831_approval_valid_ready(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={
            "WORDPRESS_BASE_URL": "https://example.invalid",
            "WORDPRESS_USERNAME": "operator",
            "WORDPRESS_APP_PASSWORD": "dummy-secret-value",
        },
    )
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30)
    assert payload["final_status"] == "HUMAN_APPROVAL_VALID_FOR_NEXT_PHASE_READY_BUT_NOT_EXECUTED"
    assert payload["execution_allowed"] is False
    assert payload["approve_draft_create_only_currently_allowed"] is False


def test_phase831_blocked_not_ready(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": ""})
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30)
    assert payload["final_status"] == "HUMAN_APPROVAL_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert payload["execution_allowed"] is False


def test_phase831_request_fix(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"})
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30, human_patch={"decision": "REQUEST_FIX"})
    assert payload["final_status"] == "WARN_REQUEST_FIX_NO_EXECUTION"


def test_phase831_reject(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"})
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30, human_patch={"decision": "REJECT"})
    assert payload["final_status"] == "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION"


def test_phase831_abort(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"})
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30, human_patch={"decision": "ABORT"})
    assert payload["final_status"] == "ABORT_BY_HUMAN_NO_EXECUTION"


def test_phase831_unknown_decision(monkeypatch, tmp_path):
    phase29 = _tmp_case_phase29(tmp_path, monkeypatch, env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"})
    phase30 = _tmp_case_phase30(tmp_path, phase29)
    payload = _tmp_case_phase31(tmp_path, phase30, human_patch={"decision": "UNKNOWN"})
    assert payload["final_status"] == "ABORT_UNKNOWN_DECISION_NO_EXECUTION"


def test_required_false_flag_true(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"},
        policy_patch={"execution_allowed": True},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_target_item_count_invalid(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"},
        request_patch={"target_item_count": 2},
    )
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_secret_leak_suspected(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"},
        request_patch={"next_step_if_ready": "Authorization: Bearer dummy"},
    )
    assert payload["final_status"] == "ABORT_SECRET_LEAK_RISK"


def test_safe_key_allowlist(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"},
        request_patch={"next_step_if_ready": "no_secret_leak_passed"},
    )
    assert payload["final_status"] == "CREDENTIAL_RECHECK_READY_NO_SECRET_LEAK_NO_EXECUTION"


def test_env_dummy_secret_not_in_result(monkeypatch, tmp_path):
    secret = "VERY_SECRET_DUMMY_VALUE"
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={
            "WORDPRESS_BASE_URL": "https://example.invalid",
            "WORDPRESS_USERNAME": "operator",
            "WORDPRESS_APP_PASSWORD": secret,
        },
    )
    dumped = json.dumps(payload, ensure_ascii=False)
    assert secret not in dumped


def test_credential_checks_shape(monkeypatch, tmp_path):
    payload = _tmp_case_phase29(
        tmp_path,
        monkeypatch,
        env_values={"WORDPRESS_BASE_URL": "https://example.invalid", "WORDPRESS_USERNAME": "u", "WORDPRESS_APP_PASSWORD": "p"},
    )
    for item in payload["credential_checks"]:
        assert set(item.keys()) == {"credential_key", "present", "non_empty", "status"}
