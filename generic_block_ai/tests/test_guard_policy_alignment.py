import json
from pathlib import Path

from generic_block_ai.app.block_contract import BlockManifest
from generic_block_ai.app.safety_guard import load_policy, validate_runtime_configuration


def test_runtime_configuration_rejects_observe_only_false() -> None:
    manifest = BlockManifest.from_json_file(Path("generic_block_ai/block_manifest.json"))
    policy = load_policy(Path("generic_block_ai/config/policy.json"))
    policy["observe_only"] = False

    assert validate_runtime_configuration(manifest, policy) == ["policy.observe_only must be true"]


def test_runtime_configuration_rejects_dangerous_capability_enablement() -> None:
    payload = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    payload["capabilities"]["publish_content"] = True

    manifest = BlockManifest.from_dict(payload)
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    assert validate_runtime_configuration(manifest, policy) == ["capability must remain disabled: publish_content"]