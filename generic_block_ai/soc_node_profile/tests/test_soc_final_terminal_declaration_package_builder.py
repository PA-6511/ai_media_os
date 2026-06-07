from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.soc_final_terminal_declaration_package_builder import (
    build_soc_final_terminal_declaration_package,
    validate_soc20_phase_constraints,
    validate_soc_final_terminal_declaration_package_contract,
)
from generic_block_ai.soc_node_profile.runtime.soc_governance_cycle_handoff_marker_builder import (
    build_soc_governance_cycle_handoff_marker,
)
from generic_block_ai.soc_node_profile.runtime.soc_terminal_preservation_receipt_builder import (
    build_soc_terminal_preservation_receipt,
)

BASE = Path("generic_block_ai/soc_node_profile")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return _load_json(BASE / "soc_block_manifest.json")


def _load_policy(name: str) -> dict:
    return _load_json(BASE / "policy" / name)


def _build_soc19_governance_handoff_marker() -> dict:
    soc18_policy = _load_policy("soc_terminal_preservation_receipt_contract_policy.json")
    soc19_policy = _load_policy("soc_governance_cycle_handoff_marker_contract_policy.json")

    final_decl = {
        "schema_version": "soc_final_closure_audit_declaration_v1",
        "node_id": "soc_node_001",
        "request_id": "req_soc_20001",
        "closure_state": "AUDIT_CLOSED_NO_GO",
        "audit_summary": {
            "sealed_complete": True,
        },
    }
    receipt = build_soc_terminal_preservation_receipt(final_decl, soc18_policy)
    return build_soc_governance_cycle_handoff_marker(receipt, soc19_policy)


def test_soc_final_terminal_declaration_package_contract_pass() -> None:
    policy = _load_policy("soc_final_terminal_declaration_package_contract_policy.json")
    marker = _build_soc19_governance_handoff_marker()

    package = build_soc_final_terminal_declaration_package(marker, policy)
    validation = validate_soc_final_terminal_declaration_package_contract(package, policy)

    assert package["declaration_state"] == "TERMINAL_DECLARATION_FINALIZED"
    assert package["declaration_mode"] == "REPORTS_RECORD_ONLY_FINAL_DECLARATION"
    assert package["terminal_declaration_issued"] is True
    assert package["reports_only"] is True
    assert package["record_only"] is True
    assert package["no_go_lock_confirmed"] is True
    assert package["production_status"] == "NO_GO"
    assert validation["result"] == "PASS"


def test_soc_final_terminal_declaration_package_contract_fails_on_unsafe_mutation() -> None:
    policy = _load_policy("soc_final_terminal_declaration_package_contract_policy.json")
    marker = _build_soc19_governance_handoff_marker()

    package = build_soc_final_terminal_declaration_package(marker, policy)
    package["execution_allowed"] = True

    validation = validate_soc_final_terminal_declaration_package_contract(package, policy)
    assert validation["result"] == "FAIL"
    assert any("execution_allowed must be false" in x for x in validation["failed_checks"])


def test_soc20_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy("soc_final_terminal_declaration_package_contract_policy.json")

    violations = validate_soc20_phase_constraints(manifest, policy)
    assert violations == []
