from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile
from generic_block_ai.soc_node_profile.runtime.soc_audit_evidence_builder import (
    build_soc_audit_evidence_package,
    build_soc_re_evaluation_template,
    validate_soc7_phase_constraints,
    validate_soc_audit_evidence_package_contract,
    validate_soc_re_evaluation_template_contract,
)
from generic_block_ai.soc_node_profile.runtime.soc_core_connection_simulator import run_soc_core_connection_simulation
from generic_block_ai.soc_node_profile.runtime.soc_human_review_handoff_builder import build_soc_human_review_handoff_package
from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task
from generic_block_ai.soc_node_profile.runtime.task_acceptance_gate import evaluate_task_acceptance_contract


BASE = Path("generic_block_ai/soc_node_profile")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return _load_json(BASE / "soc_block_manifest.json")


def _load_policy(name: str) -> dict:
    return _load_json(BASE / "policy" / name)


def _build_reference_chain() -> tuple[dict, dict, dict, dict, dict]:
    manifest = _load_manifest()
    cap_policy = _load_policy("soc_capability_report_contract_policy.json")
    runner_policy = _load_policy("soc_task_runner_contract_policy.json")
    sim_policy = _load_policy("soc_core_connection_simulation_contract_policy.json")
    handoff_policy = _load_policy("soc_human_review_queue_handoff_contract_policy.json")

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)

    task_request = {
        "request_id": "req_soc_7001",
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
    return capability_report, acceptance_result, runner_result, simulation_result, handoff_package


def test_soc_audit_evidence_package_contract_pass() -> None:
    policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")
    cap, acc, run, sim, handoff = _build_reference_chain()

    package = build_soc_audit_evidence_package(
        capability_report=cap,
        acceptance_result=acc,
        runner_result=run,
        core_connection_simulation_result=sim,
        human_review_handoff_package=handoff,
        policy=policy,
    )
    validation = validate_soc_audit_evidence_package_contract(package, policy)

    assert validation["result"] == "PASS"
    assert package["evidence_integrity"]["is_complete"] is True


def test_soc_re_evaluation_template_contract_pass() -> None:
    policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")
    _, _, _, sim, handoff = _build_reference_chain()

    template = build_soc_re_evaluation_template(
        core_connection_simulation_result=sim,
        human_review_handoff_package=handoff,
        policy=policy,
    )
    validation = validate_soc_re_evaluation_template_contract(template, policy)

    assert validation["result"] == "PASS"
    assert template["re_evaluation_outcome"] in {"GO", "CONDITIONAL_GO", "NO_GO"}


def test_soc_audit_evidence_contract_fails_on_missing_evidence_key() -> None:
    policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")
    cap, acc, run, sim, handoff = _build_reference_chain()

    package = build_soc_audit_evidence_package(
        capability_report=cap,
        acceptance_result=acc,
        runner_result=run,
        core_connection_simulation_result=sim,
        human_review_handoff_package=handoff,
        policy=policy,
    )
    del package["evidence"]["soc4_runner_result"]

    validation = validate_soc_audit_evidence_package_contract(package, policy)
    assert validation["result"] == "FAIL"
    assert any("missing_required_evidence" in x for x in validation["failed_checks"])


def test_soc_reevaluation_contract_fails_on_invalid_outcome() -> None:
    policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")
    _, _, _, sim, handoff = _build_reference_chain()

    template = build_soc_re_evaluation_template(
        core_connection_simulation_result=sim,
        human_review_handoff_package=handoff,
        policy=policy,
    )
    template["re_evaluation_outcome"] = "UNKNOWN"

    validation = validate_soc_re_evaluation_template_contract(template, policy)
    assert validation["result"] == "FAIL"
    assert any("re_evaluation_outcome is not allowed" in x for x in validation["failed_checks"])


def test_soc7_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy("soc_audit_evidence_reevaluation_contract_policy.json")

    violations = validate_soc7_phase_constraints(manifest, policy)
    assert violations == []
