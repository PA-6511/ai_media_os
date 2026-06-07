from __future__ import annotations

from typing import Any


def build_soc_capability_report(node_id: str, manifest: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    allowed = set(manifest.get("allowed_capabilities", []))
    blocked = set(manifest.get("blocked_capabilities", []))

    return {
        "schema_version": "soc_capability_report_v1",
        "node_id": node_id,
        "status": manifest.get("status", "DESIGN_ONLY"),
        "execution_mode": manifest.get("execution", "DRY_RUN"),
        "can_summarize": "summarize" in allowed,
        "can_classify": "classify" in allowed,
        "can_generate_long_text": False,
        "can_call_external_api": manifest.get("external_api_call_allowed", False),
        "can_write_wordpress": manifest.get("wordpress_write_allowed", False),
        "recommended_task_size": "SMALL",
        "battery_powered": bool(profile.get("battery_powered", True)),
        "thermal_status": profile.get("thermal_status", "NORMAL"),
        "blocked_capabilities": sorted(blocked),
    }
