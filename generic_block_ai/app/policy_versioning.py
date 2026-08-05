from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_task_id(source_task_id: str) -> str:
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in source_task_id.strip())
    return normalized or "unknown_task"


def _normalized_policy_for_hash(policy: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(policy, ensure_ascii=False))
    metadata = payload.get("policy_metadata")
    if isinstance(metadata, dict) and "policy_hash" in metadata:
        metadata = {**metadata}
        metadata.pop("policy_hash", None)
        payload["policy_metadata"] = metadata
    return payload


def compute_policy_hash(policy: dict[str, Any]) -> str:
    normalized = _normalized_policy_for_hash(policy)
    canonical = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_policy_version_info(policy: dict[str, Any]) -> dict[str, Any]:
    metadata = policy.get("policy_metadata", {})
    version = str(metadata.get("version", "v0"))
    environment = str(metadata.get("environment", "unknown"))
    updated_at = str(metadata.get("updated_at", ""))
    change_reason = str(metadata.get("change_reason", ""))
    policy_hash = compute_policy_hash(policy)

    return {
        "version": version,
        "environment": environment,
        "updated_at": updated_at,
        "change_reason": change_reason,
        "policy_hash": policy_hash,
    }


def write_policy_history(
    *,
    base_path: Path,
    policy: dict[str, Any],
    source_task_id: str,
) -> dict[str, Any]:
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_key = _safe_task_id(source_task_id)
    path = reports_dir / f"policy_history_{task_key}.json"

    version_info = build_policy_version_info(policy)
    payload = {
        "_meta": {
            "purpose": "policy_history",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_task_id": source_task_id,
        },
        "policy": version_info,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        **version_info,
        "history_path": str(path),
        "external_write_executed": False,
    }