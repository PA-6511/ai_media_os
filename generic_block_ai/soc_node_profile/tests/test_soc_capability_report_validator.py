from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_report_validator import (
    validate_capability_report_contract,
    validate_soc2_phase_constraints,
)
from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile


MANIFEST_PATH = Path("generic_block_ai/soc_node_profile/soc_block_manifest.json")
POLICY_PATH = Path("generic_block_ai/soc_node_profile/policy/soc_capability_report_contract_policy.json")


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_soc_capability_report_contract_pass() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    report = build_soc_capability_report("soc_node_001", manifest, profile)

    validation = validate_capability_report_contract(report, policy)
    assert validation["result"] == "PASS"
    assert validation["failed_checks"] == []


def test_soc_capability_report_contract_fails_when_external_api_enabled() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    report = build_soc_capability_report("soc_node_001", manifest, profile)
    report["can_call_external_api"] = True

    validation = validate_capability_report_contract(report, policy)
    assert validation["result"] == "FAIL"
    assert any("can_call_external_api must be false" in x for x in validation["failed_checks"])


def test_soc_capability_report_contract_fails_when_required_blocked_cap_missing() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    report = build_soc_capability_report("soc_node_001", manifest, profile)
    report["blocked_capabilities"] = ["publish"]

    validation = validate_capability_report_contract(report, policy)
    assert validation["result"] == "FAIL"
    assert any("blocked_capabilities missing required entries" in x for x in validation["failed_checks"])


def test_soc2_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    violations = validate_soc2_phase_constraints(manifest, policy)
    assert violations == []
