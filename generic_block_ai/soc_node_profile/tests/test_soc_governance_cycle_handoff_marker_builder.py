from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.soc_governance_cycle_handoff_marker_builder import (
    build_soc_governance_cycle_handoff_marker,
    validate_soc19_phase_constraints,
    validate_soc_governance_cycle_handoff_marker_contract,
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


def _build_soc18_terminal_preservation_receipt() -> dict:
    soc18_policy = _load_policy("soc_terminal_preservation_receipt_contract_policy.json")
    final_decl = {
        "schema_version": "soc_final_closure_audit_declaration_v1",
        "node_id": "soc_node_001",
        "request_id": "req_soc_19001",
        "closure_state": "AUDIT_CLOSED_NO_GO",
        "audit_summary": {
            "sealed_complete": True,
        },
    }
    return build_soc_terminal_preservation_receipt(final_decl, soc18_policy)


def test_soc_governance_cycle_handoff_marker_contract_pass() -> None:
    policy = _load_policy("soc_governance_cycle_handoff_marker_contract_policy.json")
    receipt = _build_soc18_terminal_preservation_receipt()

    marker = build_soc_governance_cycle_handoff_marker(receipt, policy)
    validation = validate_soc_governance_cycle_handoff_marker_contract(marker, policy)

    assert marker["handoff_state"] == "NEXT_GOVERNANCE_CYCLE_PENDING"
    assert marker["handoff_mode"] == "REPORTS_RECORD_ONLY_HANDOFF"
    assert marker["handoff_marker_issued"] is True
    assert marker["reports_only"] is True
    assert marker["record_only"] is True
    assert marker["no_go_lock_confirmed"] is True
    assert marker["production_status"] == "NO_GO"
    assert validation["result"] == "PASS"


def test_soc_governance_cycle_handoff_marker_contract_fails_on_unsafe_mutation() -> None:
    policy = _load_policy("soc_governance_cycle_handoff_marker_contract_policy.json")
    receipt = _build_soc18_terminal_preservation_receipt()

    marker = build_soc_governance_cycle_handoff_marker(receipt, policy)
    marker["execution_allowed"] = True

    validation = validate_soc_governance_cycle_handoff_marker_contract(marker, policy)
    assert validation["result"] == "FAIL"
    assert any("execution_allowed must be false" in x for x in validation["failed_checks"])


def test_soc19_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy("soc_governance_cycle_handoff_marker_contract_policy.json")

    violations = validate_soc19_phase_constraints(manifest, policy)
    assert violations == []
