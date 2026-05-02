import json
from pathlib import Path

from shared.block_manifest_loader import load_block_manifest, validate_block_manifest


def test_load_and_validate_generic_block_manifest() -> None:
    manifest = load_block_manifest("generic_block_ai/block_manifest.json")
    result = validate_block_manifest(manifest)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["warnings"] == []
    assert result["block_id"] == "generic_block"
    assert result["risk_level"] == "low"


def test_validate_manifest_reports_forbidden_capability_and_risky_flags() -> None:
    manifest = {
        "block_id": "bad_block",
        "risk_level": "medium",
        "mode": "dry_run",
        "approval_policy": {
            "requires_human_approval": True,
            "auto_execute_allowed": False,
        },
        "forbidden_actions": ["delete_block"],
        "capabilities": {
            "publish_content": True,
            "delete_data": True,
            "change_config": True,
            "adult": True,
        },
    }

    result = validate_block_manifest(manifest)

    assert result["valid"] is False
    assert any("forbidden capability detected" in e for e in result["errors"])
    assert any("publish_content=true" in w for w in result["warnings"])
    assert any("delete_data=true" in w for w in result["warnings"])
    assert any("change_config=true" in w for w in result["warnings"])


def test_load_block_manifest_does_not_raise_on_broken_json(tmp_path: Path) -> None:
    broken_path = tmp_path / "broken_manifest.json"
    broken_path.write_text("{ this is not valid json", encoding="utf-8")

    manifest = load_block_manifest(str(broken_path))
    result = validate_block_manifest(manifest)

    assert result["valid"] is False
    assert any("failed to load manifest" in e for e in result["errors"])


def test_load_block_manifest_does_not_raise_on_non_object_root(tmp_path: Path) -> None:
    array_path = tmp_path / "array_manifest.json"
    array_path.write_text(json.dumps(["not", "object"]), encoding="utf-8")

    manifest = load_block_manifest(str(array_path))
    result = validate_block_manifest(manifest)

    assert result["valid"] is False
    assert any("manifest root must be a JSON object" in e for e in result["errors"])
