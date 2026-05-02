from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.block_manifest_loader import load_block_manifest, validate_block_manifest


EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def discover_block_manifests(root_path: str) -> list[str]:
    root = Path(root_path)
    if not root.exists():
        return []

    manifests: list[str] = []
    for path in root.rglob("block_manifest.json"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        manifests.append(str(path))

    manifests.sort()
    return manifests


def load_block_registry(root_path: str) -> dict[str, Any]:
    root = Path(root_path).resolve()
    manifest_paths = discover_block_manifests(str(root))

    blocks: list[dict[str, Any]] = []
    warning_count = 0
    error_count = 0
    valid_count = 0

    for manifest_path in manifest_paths:
        manifest = load_block_manifest(manifest_path)
        result = validate_block_manifest(manifest)

        warnings = list(result.get("warnings", []))
        errors = list(result.get("errors", []))

        warning_count += len(warnings)
        error_count += len(errors)
        if result.get("valid") is True:
            valid_count += 1

        manifest_path_obj = Path(manifest_path).resolve()
        try:
            relative_path = manifest_path_obj.relative_to(root).as_posix()
        except ValueError:
            relative_path = manifest_path_obj.as_posix()

        blocks.append(
            {
                "path": relative_path,
                "block_id": result.get("block_id", "unknown"),
                "risk_level": result.get("risk_level", "unknown"),
                "valid": bool(result.get("valid", False)),
                "warnings": warnings,
                "errors": errors,
            }
        )

    total = len(blocks)
    invalid = total - valid_count
    return {
        "blocks": blocks,
        "summary": {
            "total": total,
            "valid": valid_count,
            "invalid": invalid,
            "warnings": warning_count,
            "errors": error_count,
        },
    }
