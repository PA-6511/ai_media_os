import json
from pathlib import Path

from shared.block_manifest_registry import discover_block_manifests, load_block_registry


def test_discover_includes_generic_block_manifest() -> None:
    manifests = discover_block_manifests(".")
    normalized = [Path(path).as_posix() for path in manifests]
    assert any(path.endswith("generic_block_ai/block_manifest.json") for path in normalized)


def test_discover_includes_ebook_affiliate_manifest() -> None:
    manifests = discover_block_manifests(".")
    normalized = [Path(path).as_posix() for path in manifests]
    assert any(path.endswith("blocks/ebook_affiliate_block/block_manifest.json") for path in normalized)


def test_discover_excludes_ignored_directories(tmp_path: Path) -> None:
    root = tmp_path
    keep = root / "custom_block"
    keep.mkdir(parents=True, exist_ok=True)
    (keep / "block_manifest.json").write_text("{}", encoding="utf-8")

    ignored = root / "node_modules" / "x"
    ignored.mkdir(parents=True, exist_ok=True)
    (ignored / "block_manifest.json").write_text("{}", encoding="utf-8")

    manifests = discover_block_manifests(str(root))
    normalized = [Path(path).resolve().as_posix() for path in manifests]
    assert (keep / "block_manifest.json").resolve().as_posix() in normalized
    assert (ignored / "block_manifest.json").resolve().as_posix() not in normalized


def test_registry_handles_invalid_manifest_without_stopping(tmp_path: Path) -> None:
    root = tmp_path

    good_dir = root / "good_block"
    good_dir.mkdir(parents=True, exist_ok=True)
    good_manifest = {
        "block_id": "good_block",
        "risk_level": "low",
        "mode": "dry_run",
        "approval_policy": {
            "requires_human_approval": True,
            "auto_execute_allowed": False,
        },
        "forbidden_actions": ["delete_block"],
        "capabilities": {
            "publish_content": False,
            "delete_data": False,
            "change_config": False,
        },
    }
    (good_dir / "block_manifest.json").write_text(json.dumps(good_manifest), encoding="utf-8")

    bad_dir = root / "bad_block"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "block_manifest.json").write_text("{not valid json", encoding="utf-8")

    registry = load_block_registry(str(root))
    summary = registry["summary"]

    assert summary["total"] == 2
    assert summary["valid"] == 1
    assert summary["invalid"] == 1

    blocks = {entry["block_id"]: entry for entry in registry["blocks"]}
    assert blocks["good_block"]["valid"] is True

    invalid_entries = [entry for entry in registry["blocks"] if entry["valid"] is False]
    assert len(invalid_entries) == 1
    assert any("failed to load manifest" in err for err in invalid_entries[0]["errors"])


def test_registry_contains_two_valid_blocks_in_repo_root() -> None:
    registry = load_block_registry(".")
    blocks = registry["blocks"]

    target = {
        entry["block_id"]: entry
        for entry in blocks
        if entry["block_id"] in {"generic_block", "ebook_affiliate_block"}
    }

    assert "generic_block" in target
    assert "ebook_affiliate_block" in target
    assert target["generic_block"]["valid"] is True
    assert target["ebook_affiliate_block"]["valid"] is True
