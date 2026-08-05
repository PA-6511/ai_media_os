from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta07_validator import validate_beta07_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta08_manual_approval_gate.json"

_EXPECTED_APPROVAL_TEXT = "I APPROVE FIRST REAL LOCAL LLM CALL FOR GIB BETA1 UNDER CHANGE CONTROL."


@dataclass
class ApprovalScenarioResult:
    scenario_name: str
    approval_granted: bool
    ready_source: bool
    call_allowed: bool
    blocked_reason: str | None


@dataclass
class Beta08GateResult:
    config_valid: bool
    config_issues: list[str]
    denied_scenario: ApprovalScenarioResult
    approved_sim_scenario: ApprovalScenarioResult
    auto_connect_triggered: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta08_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta08.manual_approval_gate.v0.1":
        issues.append("schema_version must be gib.beta08.manual_approval_gate.v0.1")
    if config.get("beta_version") != "beta0.8":
        issues.append("beta_version must be beta0.8")
    if config.get("status") != "DRY_RUN_MANUAL_APPROVAL_GATE_ONLY":
        issues.append("status must be DRY_RUN_MANUAL_APPROVAL_GATE_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")

    if config.get("manual_approval_required") is not True:
        issues.append("manual_approval_required must be true")
    if config.get("approval_granted") is not False:
        issues.append("approval_granted must be false in beta0.8")

    if config.get("first_real_call_approval_text") != _EXPECTED_APPROVAL_TEXT:
        issues.append("first_real_call_approval_text must match the fixed approval statement")

    for flag in ["real_llm_call_allowed", "execution_allowed", "generate_call_allowed", "chat_call_allowed"]:
        if config.get(flag) is not False:
            issues.append(f"{flag} must be false")

    if config.get("auto_connect_on_ready") is not False:
        issues.append("auto_connect_on_ready must be false")

    artifact = config.get("artifact_policy", {})
    if artifact.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def _evaluate_scenario(config: dict[str, Any], ready_source: bool, approval_granted: bool, name: str) -> ApprovalScenarioResult:
    if not ready_source:
        return ApprovalScenarioResult(
            scenario_name=name,
            approval_granted=approval_granted,
            ready_source=ready_source,
            call_allowed=False,
            blocked_reason="ready_condition_false",
        )

    if config["manual_approval_required"] is True and approval_granted is not True:
        return ApprovalScenarioResult(
            scenario_name=name,
            approval_granted=approval_granted,
            ready_source=ready_source,
            call_allowed=False,
            blocked_reason="manual_approval_required",
        )

    if config["real_llm_call_allowed"] is not True:
        return ApprovalScenarioResult(
            scenario_name=name,
            approval_granted=approval_granted,
            ready_source=ready_source,
            call_allowed=False,
            blocked_reason="real_llm_call_allowed_false",
        )

    if config["execution_allowed"] is not True:
        return ApprovalScenarioResult(
            scenario_name=name,
            approval_granted=approval_granted,
            ready_source=ready_source,
            call_allowed=False,
            blocked_reason="execution_allowed_false",
        )

    return ApprovalScenarioResult(
        scenario_name=name,
        approval_granted=approval_granted,
        ready_source=ready_source,
        call_allowed=True,
        blocked_reason=None,
    )


def run_manual_approval_gate(config: dict[str, Any], beta07_report: dict[str, Any]) -> Beta08GateResult:
    issues = validate_beta08_config(config)

    ready_source = bool(beta07_report.get("simulated_ready_conditions_ok"))

    denied = _evaluate_scenario(
        config=config,
        ready_source=ready_source,
        approval_granted=False,
        name="approval_false",
    )
    approved_sim = _evaluate_scenario(
        config=config,
        ready_source=ready_source,
        approval_granted=True,
        name="approval_true_simulation",
    )

    auto_connect_triggered = (
        ready_source
        and config["auto_connect_on_ready"] is True
        and approved_sim.call_allowed is True
    )

    return Beta08GateResult(
        config_valid=(len(issues) == 0),
        config_issues=issues,
        denied_scenario=denied,
        approved_sim_scenario=approved_sim,
        auto_connect_triggered=auto_connect_triggered,
    )


def load_and_run(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Beta08GateResult]:
    config = load_json(path or CONFIG_PATH)
    beta07_report = validate_beta07_contract()
    result = run_manual_approval_gate(config, beta07_report)
    if result.config_issues:
        raise RuntimeError("GIB beta0.8 config validation failed: " + "; ".join(result.config_issues))
    return config, beta07_report, result
