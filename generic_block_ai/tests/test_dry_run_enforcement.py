import json
from pathlib import Path

import pytest

from generic_block_ai.app.block_contract import BlockManifest
from generic_block_ai.app.safety_guard import load_policy, validate_runtime_configuration


def test_manifest_rejects_non_dry_run() -> None:
    payload = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    payload["mode"] = "live_run"

    with pytest.raises(ValueError, match="manifest.mode must be dry_run"):
        BlockManifest.from_dict(payload)


def test_runtime_configuration_rejects_missing_human_approval() -> None:
    payload = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    payload["approval_policy"]["requires_human_approval"] = False

    manifest = BlockManifest.from_dict(payload)
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    assert validate_runtime_configuration(manifest, policy) == ["requires_human_approval must remain true"]


def test_runtime_configuration_rejects_auto_execute_enabled() -> None:
    payload = json.loads(Path("generic_block_ai/block_manifest.json").read_text(encoding="utf-8"))
    payload["approval_policy"]["auto_execute_allowed"] = True

    manifest = BlockManifest.from_dict(payload)
    policy = load_policy(Path("generic_block_ai/config/policy.json"))

    assert validate_runtime_configuration(manifest, policy) == ["auto_execute_allowed must remain false"]