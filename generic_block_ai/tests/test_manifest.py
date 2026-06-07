from pathlib import Path

from generic_block_ai.app.block_contract import BlockManifest


def test_manifest_load_and_defaults() -> None:
    manifest_path = Path("generic_block_ai/block_manifest.json")
    manifest = BlockManifest.from_json_file(manifest_path)

    assert manifest.block_id == "generic_block"
    assert manifest.operation_mode == "OBSERVE"
    assert manifest.mode == "dry_run"
    assert manifest.requires_human_approval is True
    assert manifest.capabilities["publish_content"] is False
    assert manifest.hardware_profile["device_class"] == "GENERIC_COMPUTE_NODE"
