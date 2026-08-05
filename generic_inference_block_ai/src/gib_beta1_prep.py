from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta099_validator import validate_beta099_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
RUNBOOK_PATH = _ROOT / "config" / "gib_beta1_prep_runbook.json"


@dataclass
class Beta1PrepResult:
    config_valid: bool
    config_issues: list[str]
    beta099_prereq_ok: bool
    beta099_prereq_issues: list[str]
    constraints_ok: bool
    constraints_issues: list[str]
    can_execute_now: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta1_prep_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta1.prep.runbook.v0.1":
        issues.append("schema_version must be gib.beta1.prep.runbook.v0.1")
    if config.get("phase") != "beta1_prep":
        issues.append("phase must be beta1_prep")
    if config.get("status") != "DRY_RUN_BETA1_PREP_ONLY":
        issues.append("status must be DRY_RUN_BETA1_PREP_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false")
    if config.get("real_llm_call_allowed") is not False:
        issues.append("real_llm_call_allowed must be false")

    if config.get("target_runtime") != "ollama":
        issues.append("target_runtime must be ollama")
    if config.get("target_host") != "local_pc":
        issues.append("target_host must be local_pc")
    if config.get("target_model") != "gemma-4-qat-e2b":
        issues.append("target_model must be gemma-4-qat-e2b")

    constraints = config.get("constraints", {})
    expected_constraints = {
        "localhost_only": True,
        "reports_only_output": True,
        "wordpress_write_allowed": False,
        "credential_access_allowed": False,
        "systemd_operation_allowed": False,
        "generate_chat_execution": False,
    }
    for key, expected in expected_constraints.items():
        if constraints.get(key) is not expected:
            issues.append(f"constraints.{key} must be {str(expected).lower()}")

    req = config.get("required_inputs", {})
    if req.get("approval_token_format_valid") is not True:
        issues.append("required_inputs.approval_token_format_valid must be true")
    if req.get("change_management_id_format_valid") is not True:
        issues.append("required_inputs.change_management_id_format_valid must be true")
    if req.get("final_approval_granted") is not False:
        issues.append("required_inputs.final_approval_granted must be false")

    release_gate = config.get("release_gate", {})
    if release_gate.get("allow_beta1_execution_now") is not False:
        issues.append("release_gate.allow_beta1_execution_now must be false")

    steps = config.get("run_steps")
    if not isinstance(steps, list) or len(steps) < 5:
        issues.append("run_steps must be a list with at least 5 steps")

    return issues


def evaluate_beta1_prep(config: dict[str, Any], beta099_report: dict[str, Any]) -> Beta1PrepResult:
    config_issues = validate_beta1_prep_config(config)

    prereq_issues: list[str] = []
    if beta099_report.get("final_status") != "PASS_DRY_RUN_BETA099_FINAL_APPROVAL_GATE_NO_EXECUTION":
        prereq_issues.append("beta099 final_status is not PASS")
    if beta099_report.get("can_execute_now") is not False:
        prereq_issues.append("beta099 can_execute_now must be false")
    if beta099_report.get("production_status") != "NO_GO":
        prereq_issues.append("beta099 production_status must be NO_GO")

    constraint_issues: list[str] = []
    guard = beta099_report.get("current_guardrails", {})
    if guard.get("real_llm_call_allowed") is not False:
        constraint_issues.append("beta099 current_guardrails.real_llm_call_allowed must be false")
    if guard.get("execution_allowed") is not False:
        constraint_issues.append("beta099 current_guardrails.execution_allowed must be false")
    if guard.get("generate_call_allowed") is not False:
        constraint_issues.append("beta099 current_guardrails.generate_call_allowed must be false")
    if guard.get("chat_call_allowed") is not False:
        constraint_issues.append("beta099 current_guardrails.chat_call_allowed must be false")

    return Beta1PrepResult(
        config_valid=(len(config_issues) == 0),
        config_issues=config_issues,
        beta099_prereq_ok=(len(prereq_issues) == 0),
        beta099_prereq_issues=prereq_issues,
        constraints_ok=(len(constraint_issues) == 0),
        constraints_issues=constraint_issues,
        can_execute_now=False,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Beta1PrepResult]:
    config = load_json(path or RUNBOOK_PATH)
    beta099 = validate_beta099_contract()
    result = evaluate_beta1_prep(config, beta099)
    if result.config_issues:
        raise RuntimeError("GIB beta1 prep config validation failed: " + "; ".join(result.config_issues))
    return config, beta099, result
