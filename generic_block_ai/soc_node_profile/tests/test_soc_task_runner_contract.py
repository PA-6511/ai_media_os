from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.soc_task_runner import (
    run_soc_dry_run_task,
    validate_soc4_phase_constraints,
)
from generic_block_ai.soc_node_profile.runtime.soc_task_runner_validator import (
    validate_soc_task_runner_result_contract,
)


MANIFEST_PATH = Path("generic_block_ai/soc_node_profile/soc_block_manifest.json")
POLICY_PATH = Path("generic_block_ai/soc_node_profile/policy/soc_task_runner_contract_policy.json")


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_soc_task_runner_contract_pass_for_allowed_request() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_soc_10",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["WARN timeout", "INFO retry"],
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }

    result = run_soc_dry_run_task(request)
    validation = validate_soc_task_runner_result_contract(result, policy)

    assert result["status"] == "PASS"
    assert result["acceptance_decision"] == "PASS"
    assert validation["result"] == "PASS"


def test_soc_task_runner_contract_aborts_when_acceptance_fails() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_soc_11",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["WARN timeout"],
        "constraints": {"execution_mode": "REAL_RUN"},
    }

    result = run_soc_dry_run_task(request)
    validation = validate_soc_task_runner_result_contract(result, policy)

    assert result["status"] == "ABORT"
    assert result["acceptance_decision"] == "ABORT"
    assert "invalid_execution_mode" in result["decision_reason"]
    assert validation["result"] in {"PASS", "WARN"}


def test_soc_task_runner_contract_fails_validation_on_unsafe_mutation() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_soc_12",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["INFO ok"],
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }

    result = run_soc_dry_run_task(request)
    result["safeguards"]["external_api_call"] = True

    validation = validate_soc_task_runner_result_contract(result, policy)
    assert validation["result"] == "FAIL"
    assert any("safeguards.external_api_call must be false" in x for x in validation["failed_checks"])


def test_soc4_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    violations = validate_soc4_phase_constraints(manifest, policy)
    assert violations == []
