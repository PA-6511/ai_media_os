from pathlib import Path

from generic_inference_block_ai.src.gib_alpha_policy import (
    assert_policy_safe,
    validate_policy,
)

POLICY_PATH = Path(__file__).parent.parent / "config" / "gib_alpha_policy.json"


def test_policy_passes_validation() -> None:
    policy = assert_policy_safe(POLICY_PATH)

    assert policy["status"] == "DESIGN_ONLY"
    assert policy["production_status"] == "NO_GO"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["execution_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["credential_access_allowed"] is False
    assert policy["wordpress_write_allowed"] is False
    assert policy["systemd_operation_allowed"] is False
    assert policy["model_runtime_enabled"] is False
    assert policy["real_llm_call_allowed"] is False


def test_policy_validator_rejects_execution_enabled() -> None:
    policy = assert_policy_safe(POLICY_PATH)
    modified = dict(policy)
    modified["execution_allowed"] = True

    issues = validate_policy(modified)

    assert any("execution_allowed" in issue for issue in issues)
