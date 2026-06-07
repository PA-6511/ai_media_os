from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.task_acceptance_gate import (
    evaluate_task_acceptance_contract,
    validate_soc3_phase_constraints,
)


MANIFEST_PATH = Path("generic_block_ai/soc_node_profile/soc_block_manifest.json")
POLICY_PATH = Path("generic_block_ai/soc_node_profile/policy/soc_task_acceptance_contract_policy.json")


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_soc_task_acceptance_contract_pass_for_allowed_task() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_1",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["a", "b"],
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }

    result = evaluate_task_acceptance_contract(request, policy)
    assert result["schema_version"] == "soc_task_acceptance_result_v1"
    assert result["decision"] == "PASS"


def test_soc_task_acceptance_contract_aborts_on_invalid_execution_mode() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_2",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["a"],
        "constraints": {"execution_mode": "REAL_RUN"},
    }

    result = evaluate_task_acceptance_contract(request, policy)
    assert result["decision"] == "ABORT"
    assert "invalid_execution_mode" in result["reason"]


def test_soc_task_acceptance_contract_aborts_on_input_lines_exceeded() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_3",
        "node_id": "soc_node_001",
        "task_type": "log_summary",
        "input_lines": ["x"] * 201,
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }

    result = evaluate_task_acceptance_contract(request, policy)
    assert result["decision"] == "ABORT"
    assert "input_lines_exceeded" in result["reason"]


def test_soc_task_acceptance_contract_aborts_on_blocked_task_type() -> None:
    policy = _load_policy()
    request = {
        "request_id": "req_4",
        "node_id": "soc_node_001",
        "task_type": "wordpress_publish",
        "input_lines": ["a"],
        "constraints": {"execution_mode": "DRY_RUN_ONLY"},
    }

    result = evaluate_task_acceptance_contract(request, policy)
    assert result["decision"] == "ABORT"
    assert "blocked_task_type" in result["reason"]


def test_soc3_phase_constraints_remain_design_only_no_go() -> None:
    manifest = _load_manifest()
    policy = _load_policy()

    violations = validate_soc3_phase_constraints(manifest, policy)
    assert violations == []
