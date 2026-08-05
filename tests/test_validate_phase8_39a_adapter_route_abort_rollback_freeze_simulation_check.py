import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_39a_adapter_route_abort_rollback_freeze_simulation_check import validate


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/phase8_39a_adapter_route_abort_rollback_freeze_simulation_check_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_39a_adapter_route_abort_rollback_freeze_simulation_check_request.example.json")

    policy["required_reports"] = {
        "phase8_39": "exchange/logs/p839.json",
        "phase8_38a": "exchange/logs/p838a.json",
        "adapter5_result": "exchange/logs/a5.json",
        "adapter5_mapped_request": "exchange/logs/a5map.json"
    }

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"
    _write(policy_path, policy)
    _write(request_path, request)

    false_flags = {
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
    }

    scenarios = []
    for i in range(13):
        scenarios.append(
            {
                "scenario_id": f"s{i}",
                "matched_expected": True,
                "external_change_executed": False,
                "rollback_executed": False,
                "freeze_executed": False,
            }
        )

    _write(
        tmp_path / "exchange/logs/p839.json",
        {
            "status": "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION",
            "scenario_count": 13,
            "scenario_results": scenarios,
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/p838a.json",
        {
            "status": "PHASE8_38A_ADAPTER5_TO_PHASE8_38_RECONNECTION_BASELINE_LOCK_PASS_HOLD_NO_EXECUTION",
        },
    )
    _write(
        tmp_path / "exchange/logs/a5.json",
        {
            "status": "EBOOK_TRIAL_ADAPTER_5_PHASE8_38_REQUEST_MAPPING_PASS_DRY_RUN_NO_EXECUTION",
            **false_flags,
        },
    )
    _write(
        tmp_path / "exchange/logs/a5map.json",
        {
            "mode": "CONNECTION_TEST",
            "execution": "DRY_RUN",
            "production_status": "NO_GO",
            **false_flags,
        },
    )

    return policy_path, request_path, output_path


def test_pass_when_all_simulation_conditions_hold(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_39A_ADAPTER_ROUTE_ROLLBACK_FREEZE_SIMULATION_PASS_HOLD_NO_EXECUTION"
    assert result["scenario_count"] == 13
    assert result["scenario_all_matched"] is True
    assert result["no_go_invariants_ok"] is True


def test_abort_when_report_missing(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    (tmp_path / "exchange/logs/p839.json").unlink(missing_ok=True)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_39A_ADAPTER_ROUTE_SIMULATION_ABORT_MISSING_EVIDENCE_NO_EXECUTION"
    assert "phase8_39" in result["missing_reports"]


def test_abort_when_status_mismatch(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/p838a.json")
    bad["status"] = "BAD"
    _write(tmp_path / "exchange/logs/p838a.json", bad)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "PHASE8_39A_ADAPTER_ROUTE_SIMULATION_ABORT_STATUS_MISMATCH_NO_EXECUTION"
    assert any(x.startswith("phase8_38a:") for x in result["status_mismatches"])


def test_abort_when_scenario_not_matched(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    p839 = _load(tmp_path / "exchange/logs/p839.json")
    p839["scenario_results"][0]["matched_expected"] = False
    _write(tmp_path / "exchange/logs/p839.json", p839)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "PHASE8_39A_ADAPTER_ROUTE_SIMULATION_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert "invariant_failure_detected" in result["policy_violations"]
