import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_32_final_execution_gate_decision_design_only import validate_phase8_32  # noqa: E402
from validate_phase8_33_one_shot_lock_enforcement_abort_condition_design_only import validate_phase8_33  # noqa: E402
from validate_phase8_34_post_run_evidence_contract_rollback_trigger_design_only import validate_phase8_34  # noqa: E402
from generate_phase8_32_final_execution_gate_decision_design_only_report import main as report32_main  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_prereq(tmp_path: Path) -> None:
    for rel in [
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json",
        "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json",
        "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json",
        "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json",
        "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json",
        "exchange/logs/phase8_26_to_8_28_final_pre_execution_decision_pack_overall_report.json",
        "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json",
    ]:
        src = ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _tmp_case(tmp_path: Path, phase: str, policy_patch: dict | None = None, request_patch: dict | None = None, prev_pack_patch: dict | None = None):
    policy_name = {
        "8-32": "phase8_32_final_execution_gate_decision_design_only_policy.json",
        "8-33": "phase8_33_one_shot_lock_enforcement_abort_condition_design_only_policy.json",
        "8-34": "phase8_34_post_run_evidence_contract_rollback_trigger_design_only_policy.json",
    }[phase]
    request_name = {
        "8-32": "phase8_32_final_execution_gate_decision_design_only_request.example.json",
        "8-33": "phase8_33_one_shot_lock_enforcement_abort_condition_design_only_request.example.json",
        "8-34": "phase8_34_post_run_evidence_contract_rollback_trigger_design_only_request.example.json",
    }[phase]

    policy = _load(ROOT / "config" / policy_name)
    request = _load(ROOT / "exchange/examples" / request_name)
    if policy_patch:
        policy.update(policy_patch)
    if request_patch:
        request.update(request_patch)

    p = tmp_path / f"config/policy_{phase}.json"
    r = tmp_path / f"exchange/examples/request_{phase}.json"
    out = tmp_path / f"exchange/logs/result_{phase}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    r.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(policy), encoding="utf-8")
    r.write_text(json.dumps(request), encoding="utf-8")

    _copy_prereq(tmp_path)

    if prev_pack_patch:
        p2931 = tmp_path / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
        payload = _load(p2931)
        payload.update(prev_pack_patch)
        p2931.write_text(json.dumps(payload), encoding="utf-8")

    if phase == "8-32":
        return validate_phase8_32(policy_path=p, request_path=r, output_json_path=out)
    if phase == "8-33":
        return validate_phase8_33(policy_path=p, request_path=r, output_json_path=out)
    return validate_phase8_34(policy_path=p, request_path=r, output_json_path=out)


def test_phase832_normal():
    payload = validate_phase8_32()
    assert payload["simulated_gate_decision"] == "DESIGN_APPROVE_GATE_SPEC_ONLY"
    assert payload["final_status"] == "DESIGN_ONLY_FINAL_EXECUTION_GATE_SPEC_READY_NO_EXECUTION"
    assert payload["actual_go_decision_issued"] is False
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_attempted"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False


def test_phase833_normal():
    payload = validate_phase8_33()
    assert payload["lock_exists_simulated"] is False
    assert payload["final_status"] == "DESIGN_ONLY_ONE_SHOT_LOCK_ABORT_SPEC_READY_NO_EXECUTION"
    assert payload["lock_created"] is False
    assert payload["lock_released"] is False
    assert payload["execution_allowed"] is False


def test_phase834_normal():
    payload = validate_phase8_34()
    assert payload["final_status"] == "DESIGN_ONLY_POST_RUN_EVIDENCE_ROLLBACK_SPEC_READY_NO_EXECUTION"
    assert payload["post_run_evidence_generated"] is False
    assert payload["rollback_executed"] is False
    assert payload["handoff_evidence_generated_for_execution"] is False
    assert payload["execution_allowed"] is False


def test_required_false_true_abort(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", policy_patch={"execution_allowed": True})
    assert payload["final_status"] == "ABORT_POLICY_VIOLATION"


def test_missing_evidence_abort(tmp_path):
    payload = _tmp_case(tmp_path, "8-33")
    missing = tmp_path / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
    missing.unlink(missing_ok=True)
    payload = validate_phase8_33(
        policy_path=tmp_path / "config/policy_8-33.json",
        request_path=tmp_path / "exchange/examples/request_8-33.json",
        output_json_path=tmp_path / "exchange/logs/result_8-33-rerun.json",
    )
    assert payload["final_status"] == "ABORT_MISSING_EVIDENCE"
    assert payload["execution_allowed"] is False


@pytest.mark.parametrize(
    "dangerous_value",
    [
        "Authorization: Bearer dummy",
        "Basic abc",
        "password=dummy",
        "webhook=https://example.invalid",
    ],
)
def test_secret_leak_abort(tmp_path, dangerous_value):
    payload = _tmp_case(tmp_path, "8-34", request_patch={"next_step_if_design_pass": dangerous_value})
    assert payload["final_status"] == "ABORT_SECRET_LEAK_RISK"


def test_unknown_simulated_gate_decision(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", request_patch={"simulated_gate_decision": "UNKNOWN"})
    assert payload["final_status"] == "ABORT_UNKNOWN_DECISION_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["actual_go_decision_issued"] is False


def test_simulated_gate_request_fix(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", request_patch={"simulated_gate_decision": "REQUEST_FIX"})
    assert payload["final_status"] == "WARN_REQUEST_FIX_NO_EXECUTION"


def test_simulated_gate_reject(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", request_patch={"simulated_gate_decision": "REJECT"})
    assert payload["final_status"] == "FAIL_REJECTED_NO_EXECUTION"


def test_simulated_gate_abort(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", request_patch={"simulated_gate_decision": "ABORT"})
    assert payload["final_status"] == "ABORT_BY_GATE_DECISION_NO_EXECUTION"


def test_lock_exists_simulated_true(tmp_path):
    payload = _tmp_case(tmp_path, "8-33", request_patch={"lock_exists_simulated": True})
    assert payload["final_status"] == "ABORT_ONE_SHOT_LOCK_EXISTS_NO_EXECUTION"
    assert payload["lock_created"] is False
    assert payload["lock_released"] is False
    assert payload["execution_allowed"] is False


def test_previous_credentials_not_ready_does_not_fail(tmp_path):
    payload = _tmp_case(
        tmp_path,
        "8-32",
        prev_pack_patch={
            "pack_status": "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION",
            "credentials_ready": False,
            "credentials_not_ready": True,
        },
    )
    assert payload["previous_credentials_not_ready"] is True
    assert any("previous_credentials_not_ready_blocked_reason_recorded" in str(r) for r in payload["reasons"])
    assert payload["final_status"] == "DESIGN_ONLY_FINAL_EXECUTION_GATE_SPEC_READY_NO_EXECUTION"


def test_safe_key_allowlist_value_no_false_positive(tmp_path):
    payload = _tmp_case(tmp_path, "8-32", request_patch={"next_step_if_design_pass": "no_secret_leak_passed"})
    assert payload["final_status"] == "DESIGN_ONLY_FINAL_EXECUTION_GATE_SPEC_READY_NO_EXECUTION"


def test_report_has_no_secret_values(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", secret)
    payload = validate_phase8_32()
    dumped = json.dumps(payload, ensure_ascii=False)
    assert secret not in dumped

    report32_main()
    report_json = ROOT / "exchange/logs/phase8_32_final_execution_gate_decision_design_only_report.json"
    report_md = ROOT / "exchange/logs/phase8_32_final_execution_gate_decision_design_only_report.md"
    assert secret not in report_json.read_text(encoding="utf-8")
    assert secret not in report_md.read_text(encoding="utf-8")
