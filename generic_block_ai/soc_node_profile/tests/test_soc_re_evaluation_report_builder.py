from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile
from generic_block_ai.soc_node_profile.runtime.soc_audit_evidence_builder import (
    build_soc_audit_evidence_package,
    build_soc_re_evaluation_template,
)
from generic_block_ai.soc_node_profile.runtime.soc_core_connection_simulator import run_soc_core_connection_simulation
from generic_block_ai.soc_node_profile.runtime.soc_human_review_handoff_builder import build_soc_human_review_handoff_package
from generic_block_ai.soc_node_profile.runtime.soc_re_evaluation_report_builder import (
    build_soc_re_evaluation_report,
    validate_soc8_phase_constraints,
    validate_soc_re_evaluation_report_contract,
)
from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task
from generic_block_ai.soc_node_profile.runtime.task_acceptance_gate import evaluate_task_acceptance_contract


BASE = Path("generic_block_ai/soc_node_profile")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return _load_json(BASE / "soc_block_manifest.json")


def _load_policy(name: str) -> dict:
    return _load_json(BASE / "policy" / name)


def _build_soc7_inputs() -> tuple[dict, dict]:
    manifest = _load_manifest()

    cap_policy = _load_policy("soc_capability_report_contract_policy.json")
    runner_policy = _load_policy("soc_task_runner_contract_policy.json")
    sim_policy = _load_policy("soc_core_connection_simulation_contract_policy.json")
    handoff_policy = _load_policy("soc_human_review_queue_handoff_contract_policy.json")
    soc7_policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)

    task_request = {
        "request_id": "req_soc_8001",
        "node_id": "soc_node_001",
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
    return audit_package, template


def test_soc8_re_evaluation_report_contract_pass() -> None:
    policy = _load_policy("soc_reports_only_reevaluation_contract_policy.json")
    audit_package, template = _build_soc7_inputs()

    report = build_soc_re_evaluation_report(audit_package, template, policy)
    validation = validate_soc_re_evaluation_report_contract(report, policy)

    assert report["reports_only"] is True
    assert report["no_external_dispatch"] is True
    assert report["actual_execution"] is False
    assert report["final_recommendation"] in {"GO", "CONDITIONAL_GO", "NO_GO"}
    assert validation["result"] == "PASS"


def test_soc8_re_evaluation_report_degrades_go_when_evidence_incomplete() -> None:
    policy = _load_policy("soc_reports_only_reevaluation_contract_policy.json")
    audit_package, template = _build_soc7_inputs()

    template["re_evaluation_outcome"] = "GO"
    audit_package["evidence_integrity"]["is_complete"] = False
    audit_package["evidence_integrity"]["missing_evidence_keys"] = ["soc4_runner_result"]

    report = build_soc_re_evaluation_report(audit_package, template, policy)
    validation = validate_soc_re_evaluation_report_contract(report, policy)

    assert report["final_recommendation"] == "CONDITIONAL_GO"
    assert validation["result"] in {"PASS", "WARN"}


def test_soc8_re_evaluation_report_contract_fails_on_unsafe_mutation() -> None:
    policy = _load_policy("soc_reports_only_reevaluation_contract_policy.json")
    audit_package, template = _build_soc7_inputs()

    report = build_soc_re_evaluation_report(audit_package, template, policy)
    report["actual_execution"] = True

    validation = validate_soc_re_evaluation_report_contract(report, policy)
    assert validation["result"] == "FAIL"
    assert any("actual_execution must be false" in x for x in validation["failed_checks"])


def test_soc8_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy("soc_reports_only_reevaluation_contract_policy.json")

    violations = validate_soc8_phase_constraints(manifest, policy)
    assert violations == []
