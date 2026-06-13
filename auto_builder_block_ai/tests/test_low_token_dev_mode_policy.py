import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from auto_builder_block_ai.src.low_token_dev_mode import (
    DEFAULT_EXECUTION_MODE,
    DEFAULT_PRODUCTION_STATUS,
    REQUIRED_POLICY_KEYS,
    load_low_token_policy,
    validate_low_token_policy,
)


def test_policy_file_contains_required_keys():
    policy = load_low_token_policy()
    for key in REQUIRED_POLICY_KEYS:
        assert key in policy


def test_policy_stays_in_no_go_dry_run_mode():
    policy = load_low_token_policy()
    errors = validate_low_token_policy(policy)

    assert errors == []
    assert policy["production_status"] == DEFAULT_PRODUCTION_STATUS
    assert policy["execution_mode"] == DEFAULT_EXECUTION_MODE
    assert policy["external_calls_allowed"] is False
    assert policy["credential_access_allowed"] is False
    assert policy["systemd_changes_allowed"] is False
    assert policy["wordpress_write_allowed"] is False