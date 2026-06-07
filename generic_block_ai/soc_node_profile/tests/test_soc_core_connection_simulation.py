from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile
from generic_block_ai.soc_node_profile.runtime.soc_core_connection_simulator import (
    run_soc_core_connection_simulation,
    validate_soc5_phase_constraints,
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


def test_soc_core_connection_simulation_pass_path() -> None:
    manifest = _load_manifest()
    cap_policy = _load_cap_policy()
    runner_policy = _load_runner_policy()
    sim_policy = _load_sim_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)

    runner_result = run_soc_dry_run_task(
        {
            "request_id": "req_soc_c1",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["WARN timeout", "INFO retry"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )

    simulation = run_soc_core_connection_simulation(
        capability_report,
        runner_result,
        cap_policy,
        runner_policy,
        sim_policy,
    )

    assert simulation["integration_result"] == "PASS"
    assert simulation["connection_status"] == "ACCEPT_DRY_RUN_REVIEW_QUEUE"
    assert simulation["core_receive_rule"] == "ACCEPT_DRY_RUN_REVIEW_QUEUE"


def test_soc_core_connection_simulation_warn_when_runner_aborts() -> None:
    manifest = _load_manifest()
    cap_policy = _load_cap_policy()
    runner_policy = _load_runner_policy()
    sim_policy = _load_sim_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)

    runner_result = run_soc_dry_run_task(
        {
            "request_id": "req_soc_c2",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["WARN timeout"],
            "constraints": {"execution_mode": "REAL_RUN"},
        }
    )

    simulation = run_soc_core_connection_simulation(
        capability_report,
        runner_result,
        cap_policy,
        runner_policy,
        sim_policy,
    )

    assert simulation["integration_result"] == "WARN"
    assert simulation["connection_status"] == "BLOCKED_BY_GATE"
    assert simulation["core_receive_rule"] == "BLOCK_AND_PRESERVE_AUDIT_EVIDENCE"


def test_soc_core_connection_simulation_fail_when_capability_invalid() -> None:
    manifest = _load_manifest()
    cap_policy = _load_cap_policy()
    runner_policy = _load_runner_policy()
    sim_policy = _load_sim_policy()

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    capability_report = build_soc_capability_report("soc_node_001", manifest, profile)
    capability_report["can_call_external_api"] = True

    runner_result = run_soc_dry_run_task(
        {
            "request_id": "req_soc_c3",
            "node_id": "soc_node_001",
            "task_type": "log_summary",
            "input_lines": ["INFO ok"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )

    simulation = run_soc_core_connection_simulation(
        capability_report,
        runner_result,
        cap_policy,
        runner_policy,
        sim_policy,
    )

    assert simulation["integration_result"] == "FAIL"
    assert simulation["connection_status"] == "REJECTED"
    assert simulation["core_receive_rule"] == "REJECT_AND_KEEP_NO_GO"


def test_soc5_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    sim_policy = _load_sim_policy()

    violations = validate_soc5_phase_constraints(manifest, sim_policy)
    assert violations == []
