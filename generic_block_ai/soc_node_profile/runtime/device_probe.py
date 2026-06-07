from __future__ import annotations

from typing import Any


def probe_device_profile(raw_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = dict(raw_profile or {})
    return {
        "node_id": str(profile.get("node_id", "soc_node_001")),
        "device_class": str(profile.get("device_class", "SMARTPHONE_SOC")),
        "cpu_available": bool(profile.get("cpu_available", True)),
        "gpu_available": profile.get("gpu_available", "UNKNOWN"),
        "npu_available": profile.get("npu_available", "UNKNOWN"),
        "ram_gb": float(profile.get("ram_gb", 8)),
        "storage_gb": float(profile.get("storage_gb", 128)),
        "battery_powered": bool(profile.get("battery_powered", True)),
        "thermal_status": str(profile.get("thermal_status", "NORMAL")),
        "battery_percent": int(profile.get("battery_percent", 100)),
    }
