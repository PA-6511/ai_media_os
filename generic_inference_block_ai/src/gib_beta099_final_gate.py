from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta095_validator import validate_beta095_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta099_final_approval_gate.json"

_APPROVAL_TEXT = "I APPROVE GIB BETA1 FIRST REAL LOCAL LLM CALL TRANSITION UNDER CHANGE CONTROL."


@dataclass
class FinalGateScenario:
    scenario_name: str
    approval_granted: bool
    call_allowed: bool
    blocked_reason: str | None


@dataclass
class Beta099GateResult:
    config_valid: bool
    config_issues: list[str]
    beta095_prereq_ok: bool
    beta095_prereq_issues: list[str]
    target_valid: bool
    target_issues: list[str]
    switch_conditions_ok: bool
    switch_condition_issues: list[str]
    denied_scenario: FinalGateScenario
    approved_sim_scenario: FinalGateScenario


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta099_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta099.final_approval_gate.v0.1":
        issues.append("schema_version must be gib.beta099.final_approval_gate.v0.1")
    if config.get("beta_version") != "beta0.99":
        issues.append("beta_version must be beta0.99")
    if config.get("status") != "DRY_RUN_FINAL_APPROVAL_GATE_ONLY":
        issues.append("status must be DRY_RUN_FINAL_APPROVAL_GATE_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")

    if config.get("final_approval_required") is not True:
        issues.append("final_approval_required must be true")
    if config.get("final_approval_granted") is not False:
        issues.append("final_approval_granted must be false")
    if config.get("final_approval_statement") != _APPROVAL_TEXT:
        issues.append("final_approval_statement must match fixed statement")

    if config.get("real_llm_call_switch_conditions_documented") is not True:
        issues.append("real_llm_call_switch_conditions_documented must be true")

    switch = config.get("switch_conditions", {})
    required_switch_true = [
        "beta095_pass_required",
        "manual_approval_required",
        "approval_evidence_format_valid",
        "localhost_runtime_only",
        "allowlisted_model_only",
        "fallback_stub_plan_required",
        "execution_allowed_must_stay_false_at_beta099",
        "generate_chat_must_stay_unexecuted",
    ]
    for key in required_switch_true:
        if switch.get(key) is not True:
            issues.append(f"switch_conditions.{key} must be true")

    current = config.get("current_guardrails", {})
    for key in [
        "real_llm_call_allowed",
        "execution_allowed",
        "generate_call_allowed",
        "chat_call_allowed",
        "wordpress_write_allowed",
        "credential_access_allowed",
    ]:
        if current.get(key) is not False:
            issues.append(f"current_guardrails.{key} must be false")
    if current.get("fallback_runtime") != "stub":
        issues.append("current_guardrails.fallback_runtime must be stub")

    artifact = config.get("artifact_policy", {})
    if artifact.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def _validate_target(config: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    target = config.get("first_call_target", {})

    if target.get("runtime") != "ollama":
        issues.append("first_call_target.runtime must be ollama")
    if target.get("host") not in ["localhost", "127.0.0.1"]:
        issues.append("first_call_target.host must be localhost or 127.0.0.1")
    if target.get("port") != 11434:
        issues.append("first_call_target.port must be 11434")

    model = str(target.get("model", ""))
    patterns = target.get("allowlisted_model_patterns", [])
    if not patterns or not any(p in model for p in patterns):
        issues.append("first_call_target.model must match allowlisted_model_patterns")

    return len(issues) == 0, issues


def _evaluate_scenario(config: dict[str, Any], approval_granted: bool, name: str) -> FinalGateScenario:
    if config["final_approval_required"] is True and approval_granted is not True:
        return FinalGateScenario(name, approval_granted, False, "final_manual_approval_required")

    guard = config["current_guardrails"]
    if guard["real_llm_call_allowed"] is not True:
        return FinalGateScenario(name, approval_granted, False, "real_llm_call_allowed_false")
    if guard["execution_allowed"] is not True:
        return FinalGateScenario(name, approval_granted, False, "execution_allowed_false")

    return FinalGateScenario(name, approval_granted, True, None)


def evaluate_final_gate(config: dict[str, Any], beta095_report: dict[str, Any]) -> Beta099GateResult:
    config_issues = validate_beta099_config(config)

    prereq_issues: list[str] = []
    if beta095_report.get("final_status") != "PASS_DRY_RUN_BETA095_APPROVAL_EVIDENCE_FORMAT_ONLY":
        prereq_issues.append("beta095 final_status is not PASS")
    if beta095_report.get("token_format_valid") is not True:
        prereq_issues.append("beta095 token_format_valid must be true")
    if beta095_report.get("change_id_format_valid") is not True:
        prereq_issues.append("beta095 change_id_format_valid must be true")
    if beta095_report.get("production_status") != "NO_GO":
        prereq_issues.append("beta095 production_status must be NO_GO")

    target_valid, target_issues = _validate_target(config)

    switch_issues: list[str] = []
    if config.get("real_llm_call_switch_conditions_documented") is not True:
        switch_issues.append("real_llm_call_switch_conditions_documented is false")

    denied = _evaluate_scenario(config, approval_granted=False, name="approval_false")
    approved = _evaluate_scenario(config, approval_granted=True, name="approval_true_simulation")

    return Beta099GateResult(
        config_valid=(len(config_issues) == 0),
        config_issues=config_issues,
        beta095_prereq_ok=(len(prereq_issues) == 0),
        beta095_prereq_issues=prereq_issues,
        target_valid=target_valid,
        target_issues=target_issues,
        switch_conditions_ok=(len(switch_issues) == 0),
        switch_condition_issues=switch_issues,
        denied_scenario=denied,
        approved_sim_scenario=approved,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Beta099GateResult]:
    config = load_json(path or CONFIG_PATH)
    beta095 = validate_beta095_contract()
    result = evaluate_final_gate(config, beta095)
    if result.config_issues:
        raise RuntimeError("GIB beta0.99 config validation failed: " + "; ".join(result.config_issues))
    return config, beta095, result
