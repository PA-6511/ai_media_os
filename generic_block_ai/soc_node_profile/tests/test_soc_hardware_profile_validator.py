from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.hardware_profile_validator import (
    validate_hardware_profile,
    validate_soc1_phase_constraints,
)


MANIFEST_PATH = Path("generic_block_ai/soc_node_profile/soc_block_manifest.json")
POLICY_PATH = Path("generic_block_ai/soc_node_profile/policy/soc_hardware_profile_validation_policy.json")


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_soc_hardware_profile_validation_pass() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = {
        "node_id": "soc_node_001",
        "device_class": "SMARTPHONE_SOC",
        "cpu_available": True,
        "ram_gb": 8,
        "storage_gb": 128,
        "battery_powered": True,
        "thermal_status": "NORMAL",
        "battery_percent": 85,
    }

    result = validate_hardware_profile(profile, manifest, policy)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_soc_hardware_profile_validation_fails_on_ram_shortage() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = {
        "node_id": "soc_node_001",
        "device_class": "SMARTPHONE_SOC",
        "cpu_available": True,
        "ram_gb": 4,
        "storage_gb": 128,
        "battery_powered": True,
        "thermal_status": "NORMAL",
        "battery_percent": 80,
    }

    result = validate_hardware_profile(profile, manifest, policy)
    assert result["status"] == "FAIL"
    assert any("ram_below_min" in e for e in result["errors"])


def test_soc_hardware_profile_validation_fails_on_unsupported_device_class() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = {
        "node_id": "soc_node_001",
        "device_class": "DESKTOP_GPU_SERVER",
        "cpu_available": True,
        "ram_gb": 16,
        "storage_gb": 256,
        "battery_powered": False,
        "thermal_status": "NORMAL",
        "battery_percent": 100,
    }

    result = validate_hardware_profile(profile, manifest, policy)
    assert result["status"] == "FAIL"
    assert any("unsupported_device_class" in e for e in result["errors"])


def test_soc1_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    violations = validate_soc1_phase_constraints(manifest, policy)
    assert violations == []
