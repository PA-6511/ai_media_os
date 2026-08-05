import json
from pathlib import Path

from generic_block_ai.app.block_contract import BlockManifest
from generic_block_ai.app.safety_guard import load_policy, validate_runtime_configuration


def test_runtime_configuration_accepts_observe_mode() -> None:
    manifest = BlockManifest.from_json_file(Path("generic_block_ai/block_manifest.json"))
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    assert validate_runtime_configuration(manifest, policy) == []


def test_runtime_configuration_rejects_non_observe_mode() -> None:
    payload = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    payload["operation_mode"] = "ACTIVE"

    manifest = BlockManifest.from_dict(payload)
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    assert validate_runtime_configuration(manifest, policy) == ["operation_mode must be OBSERVE"]