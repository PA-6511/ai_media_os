from pathlib import Path

from generic_block_ai.app.block_contract import BlockManifest
from generic_block_ai.app.safety_guard import evaluate_actions, load_policy


def test_safety_guard_blocks_forbidden_and_publish() -> None:
    manifest = BlockManifest.from_json_file(Path("generic_block_ai/block_manifest.json"))
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    requested_actions = [
        {"type": "collect_data", "target": "source_a"},
        {"type": "publish_content", "target": "wordpress"},
        {"type": "delete_block", "target": "generic_block"},
    ]

    decision = evaluate_actions(manifest, requested_actions, policy)

    assert len(decision.allowed_actions) == 1
    assert decision.allowed_actions[0]["type"] == "collect_data"
    assert len(decision.blocked_actions) == 2
    assert any("forbidden action blocked" in warning for warning in decision.warnings)
