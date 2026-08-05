import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_40b_monitoring_cycle_diff_check import validate


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/phase8_40b_monitoring_cycle_diff_check_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_40b_monitoring_cycle_diff_check_request.example.json")

    policy["required_reports"] = {
        "phase8_40b": "exchange/logs/p840b.json",
        "adapter_route_index": "exchange/logs/adapter_index.json",
        "credential_non_secret": "exchange/logs/credential.json",
        "creators_tracking": "exchange/logs/creators.json",
        "evidence_index": "reports/evidence/index.json",
        "readiness_pack": "reports/trial_operation_master_readiness_pack.md"
    }

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"

    _write(policy_path, policy)
    _write(request_path, request)

    p840b = {
        "status": "PHASE8_40B_ADAPTER_ROUTE_FINAL_HOLD_BASELINE_LOCK_PASS_NO_EXECUTION",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "hold_state": "HOLD",
        "baseline_locked": True,
        "approval_token_consumed": False,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "executed_external_changes": 0
    }

    adapter_index = {
        "missing": [],
        "next_action": "KEEP_HOLD_AND_MONITOR"
    }

    credential = {
        "status": "READY_NON_SECRET_CHECK_PASS",
        "secret_values_output": False
    }

    creators = {
        "status": "EXTERNAL_TRACKING_REQUIRED"
    }

    evidence_index = {
        "entries": [
            {"name": "phase8_adapter_route_hold_evidence_index"},
            {"name": "phase8_40b_final_hold_lock"},
            {"name": "creators_api_eligibility_tracking"},
            {"name": "credential_env_non_secret_readiness"}
        ]
    }

    readiness_pack = "\n".join([
        "Phase8-40B: final HOLD baseline lock PASS",
        "exchange/logs/phase8_adapter_route_hold_evidence_index.json",
        "exchange/logs/credential_env_non_secret_readiness_check.json",
        "Keep HOLD and monitor."
    ])

    _write(tmp_path / "exchange/logs/p840b.json", p840b)
    _write(tmp_path / "exchange/logs/adapter_index.json", adapter_index)
    _write(tmp_path / "exchange/logs/credential.json", credential)
    _write(tmp_path / "exchange/logs/creators.json", creators)
    _write(tmp_path / "reports/evidence/index.json", evidence_index)
    _write(tmp_path / "reports/trial_operation_master_readiness_pack.md", readiness_pack)

    return policy_path, request_path, output_path


def test_monitor_1_pass(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "MONITOR_1_PHASE8_40B_HOLD_DIFF_CHECK_PASS"
    assert result["all_checks_passed"] is True


def test_monitor_1_abort_when_missing_report(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    (tmp_path / "exchange/logs/credential.json").unlink(missing_ok=True)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "MONITOR_1_ABORT_MISSING_EVIDENCE"
    assert "credential_non_secret" in result["missing_reports"]


def test_monitor_1_drift_detected_on_creators_status(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/creators.json")
    bad["status"] = "ELIGIBLE"
    _write(tmp_path / "exchange/logs/creators.json", bad)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "MONITOR_1_ABORT_STATUS_MISMATCH"
    assert any(x.startswith("creators_tracking:") for x in result["status_mismatches"])


def test_monitor_1_drift_detected_on_write_flag(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/p840b.json")
    bad["wordpress_write_allowed"] = True
    _write(tmp_path / "exchange/logs/p840b.json", bad)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "MONITOR_1_DRIFT_DETECTED_KEEP_HOLD"
    assert "phase8_40b.wordpress_write_allowed" in result["drift_items"]