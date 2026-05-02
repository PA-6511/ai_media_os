from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
FORBIDDEN_CAPABILITY_KEYS = {"adult", "adult_content", "r18", "nsfw"}


def load_block_manifest(path: str) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "_load_error": f"failed to load manifest: {exc}",
            "_source_path": str(manifest_path),
        }

    if isinstance(payload, dict):
        payload.setdefault("_source_path", str(manifest_path))
        return payload

    return {
        "_load_error": "manifest root must be a JSON object",
        "_source_path": str(manifest_path),
    }


def validate_block_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    block_id = str(manifest.get("block_id", "")).strip()
    risk_level = str(manifest.get("risk_level", "")).strip().lower()

    load_error = manifest.get("_load_error")
    if load_error:
        errors.append(str(load_error))

    if not block_id:
        errors.append("block_id is required")

    if not risk_level:
        errors.append("risk_level is required")
    elif risk_level not in ALLOWED_RISK_LEVELS:
        errors.append(f"risk_level must be one of {sorted(ALLOWED_RISK_LEVELS)}")

    mode = str(manifest.get("mode", "")).strip().lower()
    if not mode:
        errors.append("mode is required")
    elif mode != "dry_run":
        errors.append("mode must be dry_run")

    approval_policy = manifest.get("approval_policy")
    if not isinstance(approval_policy, dict):
        errors.append("approval_policy must be an object")
    else:
        if "requires_human_approval" not in approval_policy:
            errors.append("approval_policy.requires_human_approval is required")
        elif not bool(approval_policy.get("requires_human_approval")):
            warnings.append("requires_human_approval=false is unsafe for Phase G-1.5")

        if bool(approval_policy.get("auto_execute_allowed", False)):
            warnings.append("auto_execute_allowed=true should stay false in Phase G-1.5")

    forbidden_actions = manifest.get("forbidden_actions")
    if not isinstance(forbidden_actions, list) or not forbidden_actions:
        errors.append("forbidden_actions must be a non-empty array")

    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append("capabilities must be an object")
        capabilities = {}

    for capability_name in ("publish_content", "delete_data", "change_config"):
        if bool(capabilities.get(capability_name, False)):
            warnings.append(f"{capability_name}=true increases risk")

    for capability_key in capabilities.keys():
        key = str(capability_key).strip().lower()
        if key in FORBIDDEN_CAPABILITY_KEYS:
            errors.append(f"forbidden capability detected: {capability_key}")

    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "block_id": block_id or "unknown",
        "risk_level": risk_level or "unknown",
    }
