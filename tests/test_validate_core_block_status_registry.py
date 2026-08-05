import json
import subprocess
from pathlib import Path


def test_registry_and_policy_json_are_valid():
    json.loads(Path("core_ai/registries/block_status_registry.json").read_text(encoding="utf-8"))
    json.loads(Path("core_ai/policies/core_block_status_registry_policy.json").read_text(encoding="utf-8"))


def test_registry_preserves_locked_baseline():
    registry = json.loads(Path("core_ai/registries/block_status_registry.json").read_text(encoding="utf-8"))
    assert registry["block_ai"] == "ebook_affiliate_block_ai"
    assert registry["current_phase"] == "Phase 8-50B"
    assert registry["status"] == "PHASE8_50B_HARDENING_PASS_DRY_RUN_ONLY"
    assert registry["execution_mode"] == "DRY_RUN_ONLY"
    assert registry["production_status"] == "NO_GO"
    assert registry["next_action"] == "KEEP_HOLD_AND_MONITOR"
    assert registry["next_phase_lock"] == "NOT_STARTED_LOCKED"

    assert registry["amazon_api_call_allowed"] is False
    assert registry["wordpress_write_allowed"] is False
    assert registry["x_api_call_allowed"] is False
    assert registry["x_post_allowed"] is False
    assert registry["publish_allowed"] is False
    assert registry["approval_token_consumed"] is False


def test_policy_requires_same_locked_state():
    policy = json.loads(Path("core_ai/policies/core_block_status_registry_policy.json").read_text(encoding="utf-8"))
    assert policy["policy_id"] == "CORE_BLOCK_STATUS_REGISTRY_POLICY_V1"
    assert policy["phase_pack"] == "LS-2"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    assert policy["required_registry"]["block_ai"] == "ebook_affiliate_block_ai"
    assert policy["required_registry"]["next_phase_lock"] == "NOT_STARTED_LOCKED"


def test_validator_passes_and_writes_outputs(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_core_block_status_registry.py",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["execution_mode"] == "DRY_RUN_ONLY"
    assert result["production_status"] == "NO_GO"
    assert result["checks"]["block_ai"] == "ebook_affiliate_block_ai"
    assert result["checks"]["current_phase"] == "Phase 8-50B"
    assert result["checks"]["next_phase_lock"] == "NOT_STARTED_LOCKED"
    assert result["checks"]["amazon_api_call_allowed"] is False
    assert result["checks"]["publish_allowed"] is False
    assert report.exists()
    assert "LS-2 Core AI Minimal Status Registry Report" in report.read_text(encoding="utf-8")
    assert "PASS_DESIGN_ONLY_NO_EXECUTION" in completed.stdout