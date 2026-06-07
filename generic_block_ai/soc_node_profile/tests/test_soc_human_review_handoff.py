from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile
from generic_block_ai.soc_node_profile.runtime.soc_core_connection_simulator import run_soc_core_connection_simulation
from generic_block_ai.soc_node_profile.runtime.soc_human_review_handoff_builder import (
    build_soc_human_review_handoff_package,
    validate_soc6_phase_constraints,
    validate_soc_human_review_handoff_package_contract,
)
from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task


BASE = Path("generic_block_ai/soc_node_profile")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest() -> dict:
    return _load_json(BASE / "soc_block_manifest.json")


def _load_cap_policy() -> dict:
    return _load_json(BASE / "policy" / "soc_capability_report_contract_policy.json")


def _load_runner_policy() -> dict:
    return _load_json(BASE / "policy" / "soc_task_runner_contract_policy.json")


def _load_sim_policy() -> dict:
    return _load_json(BASE / "policy" / "soc_core_connection_simulation_contract_policy.json")


def _load_handoff_policy() -> dict:
    return _load_json(BASE / "policy" / "soc_human_review_queue_handoff_contract_policy.json")


def _build_simulation(request: dict) -> dict:
    manifest = _load_manifest()
    cap_policy = _load_cap_policy()
    runner_policy = _load_runner_policy()
    sim_policy = _load_sim_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)
    runner_result = run_soc_dry_run_task(request)

    return run_soc_core_connection_simulation(
        capability_report,
        runner_result,
        cap_policy,
        runner_policy,
        sim_policy,
    )


def test_soc_handoff_package_for_accept_queue_path() -> None:
    handoff_policy = _load_handoff_policy()

    simulation = _build_simulation(
        {
            "request_id": "req_soc_h1",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["WARN timeout", "INFO retry"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )
    package = build_soc_human_review_handoff_package(simulation, handoff_policy)
    validation = validate_soc_human_review_handoff_package_contract(package, handoff_policy)

    assert package["handoff_status"] == "QUEUED_FOR_HUMAN_REVIEW"
    assert package["review_priority"] == "NORMAL"
    assert validation["result"] == "PASS"


def test_soc_handoff_package_for_blocked_path() -> None:
    handoff_policy = _load_handoff_policy()

    simulation = _build_simulation(
        {
            "request_id": "req_soc_h2",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["WARN timeout"],
            "constraints": {"execution_mode": "REAL_RUN"},
        }
    )
    package = build_soc_human_review_handoff_package(simulation, handoff_policy)
    validation = validate_soc_human_review_handoff_package_contract(package, handoff_policy)

    assert package["handoff_status"] == "BLOCKED_REVIEW_REQUIRED"
    assert package["review_priority"] == "HIGH"
    assert validation["result"] in {"PASS", "WARN"}


def test_soc_handoff_package_for_rejected_path() -> None:
    handoff_policy = _load_handoff_policy()

    simulation = _build_simulation(
        {
            "request_id": "req_soc_h3",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["INFO ok"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )
    simulation["integration_result"] = "FAIL"
    simulation["connection_status"] = "REJECTED"
    simulation["core_receive_rule"] = "REJECT_AND_KEEP_NO_GO"

    package = build_soc_human_review_handoff_package(simulation, handoff_policy)
    validation = validate_soc_human_review_handoff_package_contract(package, handoff_policy)

    assert package["handoff_status"] == "REJECTED_NO_GO_LOCK"
    assert package["review_priority"] == "CRITICAL"
    assert validation["result"] == "PASS"


def test_soc_handoff_package_contract_fails_on_unsafe_mutation() -> None:
    handoff_policy = _load_handoff_policy()

    simulation = _build_simulation(
        {
            "request_id": "req_soc_h4",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["INFO ok"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )
    package = build_soc_human_review_handoff_package(simulation, handoff_policy)
    package["external_send_executed"] = True

    validation = validate_soc_human_review_handoff_package_contract(package, handoff_policy)
    assert validation["result"] == "FAIL"
    assert any("external_send_executed must be false" in x for x in validation["failed_checks"])


def test_soc6_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    handoff_policy = _load_handoff_policy()

    violations = validate_soc6_phase_constraints(manifest, handoff_policy)
    assert violations == []
