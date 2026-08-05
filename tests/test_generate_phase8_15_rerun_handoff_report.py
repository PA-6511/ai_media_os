"""Tests for generate_phase8_15_rerun_handoff_report."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_15_rerun_handoff_report import (  # noqa: E402
    generate_rerun_handoff_report,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-15",
        "name": "rerun_handoff_report_policy",
        "policy_status": "HANDOFF_REPORT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "handoff_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json",
            "exchange/logs/phase8_12_no_secret_leak_audit_result.json",
            "exchange/logs/phase8_13_post_credential_readiness_recheck_result.json",
            "exchange/logs/phase8_14_rerun_authorization_renewal_result.json",
        ],
        "ready_statuses": {
            "phase8_11": "PASS_RUNBOOK_ONLY",
            "phase8_12": "NO_SECRET_LEAK_AUDIT_PASS",
            "phase8_13": "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
            "phase8_14": "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY",
        },
        "not_ready_statuses": [
            "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
            "RERUN_AUTHORIZATION_NOT_READY_CREDENTIALS_MISSING",
        ],
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step_if_ready": "Manually rerun Phase 8-6 to Phase 8-10 commands, with explicit operator confirmation",
        "allowed_next_step_if_not_ready": "Set credentials manually without exposing secrets, then rerun Phase 8-13",
    }


def _write_all_evidences(
    tmp_path: Path,
    p811: str = "PASS_RUNBOOK_ONLY",
    p812: str = "NO_SECRET_LEAK_AUDIT_PASS",
    p813: str = "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
    p814: str = "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY",
    secret_values_written: bool = False,
) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "phase8_11_credentials_manual_runbook_validation_result.json": {"status": p811, "secret_values_written": secret_values_written},
        "phase8_12_no_secret_leak_audit_result.json": {"status": p812, "secret_values_written": secret_values_written},
        "phase8_13_post_credential_readiness_recheck_result.json": {"status": p813, "secret_values_written": secret_values_written},
        "phase8_14_rerun_authorization_renewal_result.json": {"status": p814, "secret_values_written": secret_values_written},
    }
    for fname, payload in payloads.items():
        (ev_dir / fname).write_text(json.dumps(payload), encoding="utf-8")


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    p811: str = "PASS_RUNBOOK_ONLY",
    p812: str = "NO_SECRET_LEAK_AUDIT_PASS",
    p813: str = "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
    p814: str = "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY",
    missing_evidence: bool = False,
    secret_values_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"

    if not missing_evidence:
        _write_all_evidences(tmp_path, p811, p812, p813, p814, secret_values_written)

    pol_path.write_text(json.dumps(p), encoding="utf-8")

    return generate_rerun_handoff_report(
        policy_path=pol_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_all_ready_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"


def test_phase813_not_ready_credentials_missing(tmp_path):
    result = run_case(tmp_path, p813="POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING"


def test_phase814_not_ready_credentials_missing(tmp_path):
    result = run_case(tmp_path, p814="RERUN_AUTHORIZATION_NOT_READY_CREDENTIALS_MISSING")
    assert result["status"] == "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_not_ready(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "RERUN_HANDOFF_NOT_READY"


def test_phase811_fail_abort(tmp_path):
    result = run_case(tmp_path, p811="FAIL")
    assert result["status"] == "ABORT"


def test_phase812_abort_abort(tmp_path):
    result = run_case(tmp_path, p812="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_true_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_handoff_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["handoff_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_dangerous_op_auto_post_true_abort(tmp_path):
    p = base_policy()
    p["dangerous_operations"]["auto_post"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_dangerous_op_wordpress_api_call_allowed_true_abort(tmp_path):
    p = base_policy()
    p["dangerous_operations"]["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_dangerous_op_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["dangerous_operations"]["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["handoff_is_execution_permission"] is False
    assert result["secret_values_written"] is False
    assert result["target_item_count"] == 1


def test_ready_next_step_correct(tmp_path):
    result = run_case(tmp_path)
    assert "Phase 8-6" in result.get("allowed_next_step", "")


def test_not_ready_next_step_correct(tmp_path):
    result = run_case(tmp_path, p813="POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")
    assert "Phase 8-13" in result.get("allowed_next_step", "")
