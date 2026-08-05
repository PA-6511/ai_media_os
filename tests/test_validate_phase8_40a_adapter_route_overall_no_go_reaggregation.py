import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_40a_adapter_route_overall_no_go_reaggregation import validate


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/phase8_40a_adapter_route_overall_no_go_reaggregation_policy.json")
    request = _load(ROOT / "exchange/examples/phase8_40a_adapter_route_overall_no_go_reaggregation_request.example.json")

    policy["required_reports"] = {
        "adapter6": "exchange/logs/a6.json",
        "phase8_38a": "exchange/logs/p838a.json",
        "phase8_39a": "exchange/logs/p839a.json",
        "phase8_38_from_adapter5": "exchange/logs/p838.json",
        "adapter5_result": "exchange/logs/a5.json"
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

    _write(tmp_path / "exchange/logs/a6.json", {
        "status": "EBOOK_TRIAL_ADAPTER_6_BASELINE_LOCK_PASS_HOLD_NO_EXECUTION",
        **false_flags,
    })
    _write(tmp_path / "exchange/logs/p838a.json", {
        "status": "PHASE8_38A_ADAPTER5_TO_PHASE8_38_RECONNECTION_BASELINE_LOCK_PASS_HOLD_NO_EXECUTION",
        **false_flags,
    })
    _write(tmp_path / "exchange/logs/p839a.json", {
        "status": "PHASE8_39A_ADAPTER_ROUTE_ROLLBACK_FREEZE_SIMULATION_PASS_HOLD_NO_EXECUTION",
        **false_flags,
    })
    _write(tmp_path / "exchange/logs/p838.json", {
        "status": "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_READY_NO_EXECUTION",
        **false_flags,
    })
    _write(tmp_path / "exchange/logs/a5.json", {
        "status": "EBOOK_TRIAL_ADAPTER_5_PHASE8_38_REQUEST_MAPPING_PASS_DRY_RUN_NO_EXECUTION",
        **false_flags,
    })

    return policy_path, request_path, output_path


def test_pass_when_all_sources_match(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_FIXED"
    assert result["summary"]["adapter_route_pack_completed"] is True
    assert result["summary"]["safety_violations_empty"] is True
    assert result["summary"]["publish_execution_unlocked"] is False


def test_abort_when_source_missing(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    (tmp_path / "exchange/logs/p839a.json").unlink(missing_ok=True)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_MISSING_EVIDENCE_NO_EXECUTION"
    assert "phase8_39a" in result["missing_sources"]


def test_abort_when_status_mismatch(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/p838a.json")
    bad["status"] = "BAD_STATUS"
    _write(tmp_path / "exchange/logs/p838a.json", bad)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_STATUS_MISMATCH_NO_EXECUTION"
    assert any(x.startswith("phase8_38a:") for x in result["status_mismatch_sources"])


def test_abort_when_invariant_breaks(tmp_path: Path):
    policy_path, request_path, output_path = _prepare_case(tmp_path)
    bad = _load(tmp_path / "exchange/logs/a5.json")
    bad["wordpress_write_executed"] = True
    _write(tmp_path / "exchange/logs/a5.json", bad)
    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)

    assert result["status"] == "PHASE8_40A_ADAPTER_ROUTE_OVERALL_NO_GO_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert "invariant_failure_detected" in result["policy_violations"]
