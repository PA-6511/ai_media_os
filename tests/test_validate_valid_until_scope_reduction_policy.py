import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_valid_until_scope_reduction_policy import validate


POLICY_PATH = Path("config/valid_until_scope_reduction_policy.json")


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_policy_file_exists_and_valid_json():
    policy = _load_policy()
    assert policy["policy_name"] == "VALID_UNTIL_SCOPE_REDUCTION_POLICY"


def test_policy_validator_passes():
    policy = _load_policy()
    assert validate(policy) == []


def test_non_execution_decisions_do_not_require_valid_until():
    policy = _load_policy()
    non_execution = policy["non_execution_decision_policy"]
    assert non_execution["valid_until_required"] is False
    assert non_execution["requires_time_based_recheck"] is False
    assert non_execution["freshness_policy"] == "STATIC_UNTIL_INPUT_CHANGE"


def test_execution_gate_requires_valid_until_and_single_use():
    policy = _load_policy()
    execution_gate = policy["execution_gate_policy"]
    assert execution_gate["valid_until_required"] is True
    assert execution_gate["single_use"] is True
    assert execution_gate["auto_revoke_after_use"] is True
    assert "wordpress_write" in execution_gate["applies_to"]
    assert "external_api_real_call" in execution_gate["applies_to"]


def test_prohibited_changes_include_all_required_entries():
    policy = _load_policy()
    prohibited = set(policy["prohibited_changes"])
    assert "no_production_write" in prohibited
    assert "no_wordpress_api_call" in prohibited
    assert "no_external_api_call" in prohibited
    assert "no_credential_read" in prohibited
    assert "no_credential_output" in prohibited
    assert "no_systemd_operation" in prohibited
    assert "no_approval_label_consumption" in prohibited
    assert "no_phase_forward_execution" in prohibited


def test_invalid_non_execution_valid_until_required_fails():
    policy = _load_policy()
    policy["non_execution_decision_policy"]["valid_until_required"] = True
    errors = validate(policy)
    assert any("valid_until_required" in error for error in errors)


def test_invalid_requires_time_based_recheck_fails():
    policy = _load_policy()
    policy["non_execution_decision_policy"]["requires_time_based_recheck"] = True
    errors = validate(policy)
    assert any("requires_time_based_recheck" in error for error in errors)


def test_invalid_production_status_go_fails():
    policy = _load_policy()
    policy["production_status"] = "GO"
    errors = validate(policy)
    assert any("production_status" in error for error in errors)


def test_invalid_execution_mode_live_fails():
    policy = _load_policy()
    policy["execution_mode"] = "LIVE"
    errors = validate(policy)
    assert any("execution_mode" in error for error in errors)


def test_invalid_execution_gate_single_use_false_fails():
    policy = _load_policy()
    policy["execution_gate_policy"]["single_use"] = False
    errors = validate(policy)
    assert any("single_use" in error for error in errors)


def test_missing_prohibited_changes_fail():
    policy = _load_policy()
    policy["prohibited_changes"] = ["no_production_write"]
    errors = validate(policy)
    assert any("prohibited_changes" in error for error in errors)
