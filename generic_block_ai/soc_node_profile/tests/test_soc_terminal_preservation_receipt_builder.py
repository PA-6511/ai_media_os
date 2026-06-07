from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile
from generic_block_ai.soc_node_profile.runtime.soc_approval_seal_builder import (
    build_soc_approval_event_record,
    build_soc_final_design_package_seal,
)
from generic_block_ai.soc_node_profile.runtime.soc_audit_evidence_builder import (
    build_soc_audit_evidence_package,
    build_soc_re_evaluation_template,
)
from generic_block_ai.soc_node_profile.runtime.soc_core_connection_simulator import run_soc_core_connection_simulation
from generic_block_ai.soc_node_profile.runtime.soc_design_freeze_closure_builder import build_soc_design_freeze_closure_summary
from generic_block_ai.soc_node_profile.runtime.soc_final_closure_audit_builder import build_soc_final_closure_audit_declaration
from generic_block_ai.soc_node_profile.runtime.soc_final_dossier_index_builder import build_soc_final_design_dossier_index
from generic_block_ai.soc_node_profile.runtime.soc_governance_loop_continuation_builder import build_soc_governance_loop_continuation
from generic_block_ai.soc_node_profile.runtime.soc_human_review_handoff_builder import build_soc_human_review_handoff_package
from generic_block_ai.soc_node_profile.runtime.soc_long_term_audit_retention_builder import build_soc_long_term_audit_retention_package
from generic_block_ai.soc_node_profile.runtime.soc_periodic_reverification_builder import build_soc_periodic_reverification_checklist
from generic_block_ai.soc_node_profile.runtime.soc_re_evaluation_report_builder import build_soc_re_evaluation_report
from generic_block_ai.soc_node_profile.runtime.soc_release_readiness_design_gate import build_soc_release_readiness_design_gate
from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task
from generic_block_ai.soc_node_profile.runtime.soc_terminal_archive_manifest_builder import build_soc_terminal_archive_manifest
from generic_block_ai.soc_node_profile.runtime.soc_terminal_preservation_receipt_builder import (
    build_soc_terminal_preservation_receipt,
    validate_soc18_phase_constraints,
    validate_soc_terminal_preservation_receipt_contract,
)
from generic_block_ai.soc_node_profile.runtime.task_acceptance_gate import evaluate_task_acceptance_contract


BASE = Path("generic_block_ai/soc_node_profile")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return _load_json(BASE / "soc_block_manifest.json")


def _load_policy(name: str) -> dict:
    return _load_json(BASE / "policy" / name)


def _build_soc17_final_closure_declaration() -> dict:
    manifest = _load_manifest()

    cap_policy = _load_policy("soc_capability_report_contract_policy.json")
    runner_policy = _load_policy("soc_task_runner_contract_policy.json")
    sim_policy = _load_policy("soc_core_connection_simulation_contract_policy.json")
    handoff_policy = _load_policy("soc_human_review_queue_handoff_contract_policy.json")
    soc7_policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")
    soc8_policy = _load_policy("soc_reports_only_reevaluation_contract_policy.json")
    soc9_policy = _load_policy("soc_approval_seal_contract_policy.json")
    soc10_policy = _load_policy("soc_final_design_dossier_index_contract_policy.json")
    soc11_policy = _load_policy("soc_release_readiness_design_gate_contract_policy.json")
    soc12_policy = _load_policy("soc_long_term_audit_retention_contract_policy.json")
    soc13_policy = _load_policy("soc_periodic_reverification_checklist_contract_policy.json")
    soc14_policy = _load_policy("soc_design_freeze_closure_contract_policy.json")
    soc15_policy = _load_policy("soc_terminal_archive_manifest_contract_policy.json")
    soc16_policy = _load_policy("soc_governance_loop_continuation_contract_policy.json")
    soc17_policy = _load_policy("soc_final_closure_audit_declaration_contract_policy.json")

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)

    request_id = "req_soc_18001"
    node_id = "soc_node_001"
    task_request = {
        "request_id": request_id,
        "node_id": node_id,
        "task_type": "log_summary",
        "input_lines": ["WARN timeout", "INFO retry"],
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }
    acceptance_result = evaluate_task_acceptance_contract(task_request)
    runner_result = run_soc_dry_run_task(task_request)
    simulation_result = run_soc_core_connection_simulation(
        capability_report,
        runner_result,
        cap_policy,
        runner_policy,
        sim_policy,
    )
    handoff_package = build_soc_human_review_handoff_package(simulation_result, handoff_policy)
    audit_package = build_soc_audit_evidence_package(
        capability_report=capability_report,
        acceptance_result=acceptance_result,
        runner_result=runner_result,
        core_connection_simulation_result=simulation_result,
        human_review_handoff_package=handoff_package,
        policy=soc7_policy,
    )
    template = build_soc_re_evaluation_template(
        core_connection_simulation_result=simulation_result,
        human_review_handoff_package=handoff_package,
        policy=soc7_policy,
    )
    soc8_report = build_soc_re_evaluation_report(audit_package, template, soc8_policy)

    approval = build_soc_approval_event_record(soc8_report, soc9_policy)
    seal = build_soc_final_design_package_seal(soc8_report, approval, soc9_policy)

    dossier = build_soc_final_design_dossier_index(
        node_id=node_id,
        request_id=request_id,
        soc9_approval_event_record=approval,
        soc9_final_design_package_seal=seal,
        policy=soc10_policy,
    )
    gate = build_soc_release_readiness_design_gate(dossier, soc11_policy)
    retention = build_soc_long_term_audit_retention_package(gate, soc12_policy)
    checklist = build_soc_periodic_reverification_checklist(retention, soc13_policy)
    closure = build_soc_design_freeze_closure_summary(checklist, soc14_policy)
    terminal_archive = build_soc_terminal_archive_manifest(closure, soc15_policy)
    governance = build_soc_governance_loop_continuation(terminal_archive, soc16_policy)
    return build_soc_final_closure_audit_declaration(governance, soc17_policy)


def test_soc_terminal_preservation_receipt_contract_pass() -> None:
    policy = _load_policy("soc_terminal_preservation_receipt_contract_policy.json")
    final_decl = _build_soc17_final_closure_declaration()

    receipt = build_soc_terminal_preservation_receipt(final_decl, policy)
    validation = validate_soc_terminal_preservation_receipt_contract(receipt, policy)

    assert receipt["preservation_mode"] == "REPORTS_RECORD_PRESERVATION_ONLY"
    assert receipt["receipt_status"] == "PRESERVATION_RECEIVED"
    assert receipt["preservation_confirmed"] is True
    assert receipt["reports_only"] is True
    assert receipt["record_only"] is True
    assert receipt["no_go_lock_confirmed"] is True
    assert receipt["production_status"] == "NO_GO"
    assert validation["result"] == "PASS"


def test_soc_terminal_preservation_receipt_contract_fails_on_unsafe_mutation() -> None:
    policy = _load_policy("soc_terminal_preservation_receipt_contract_policy.json")
    final_decl = _build_soc17_final_closure_declaration()

    receipt = build_soc_terminal_preservation_receipt(final_decl, policy)
    receipt["execution_allowed"] = True

    validation = validate_soc_terminal_preservation_receipt_contract(receipt, policy)
    assert validation["result"] == "FAIL"
    assert any("execution_allowed must be false" in x for x in validation["failed_checks"])


def test_soc18_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy("soc_terminal_preservation_receipt_contract_policy.json")

    violations = validate_soc18_phase_constraints(manifest, policy)
    assert violations == []
