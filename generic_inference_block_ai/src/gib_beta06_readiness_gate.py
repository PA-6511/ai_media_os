from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta06_env_prep_gate.json"


@dataclass
class Beta06GateResult:
    config_valid: bool
    config_issues: list[str]
    guardrails_ok: bool
    guardrail_issues: list[str]
    ready_conditions_ok: bool
    missing_true_conditions: list[str]
    violated_false_conditions: list[str]
    ready_for_connecting_stage: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta06_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta06.env_prep_gate.v0.1":
        issues.append("schema_version must be gib.beta06.env_prep_gate.v0.1")
    if config.get("beta_version") != "beta0.6":
        issues.append("beta_version must be beta0.6")
    if config.get("status") != "DRY_RUN_ENV_PREP_ONLY":
        issues.append("status must be DRY_RUN_ENV_PREP_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("runtime_target") != "ollama":
        issues.append("runtime_target must be ollama")
    if config.get("no_generate_call_required") is not True:
        issues.append("no_generate_call_required must be true")
    if config.get("localhost_only_required") is not True:
        issues.append("localhost_only_required must be true")
    if config.get("allowlist_enforced") is not True:
        issues.append("allowlist_enforced must be true")

    true_conditions = config.get("required_true_conditions_for_ready")
    false_conditions = config.get("required_false_conditions_for_ready")
    if not isinstance(true_conditions, list) or not true_conditions:
        issues.append("required_true_conditions_for_ready must be a non-empty list")
    if not isinstance(false_conditions, list) or not false_conditions:
        issues.append("required_false_conditions_for_ready must be a non-empty list")

    guardrails = config.get("guardrail_requirements")
    if not isinstance(guardrails, dict):
        issues.append("guardrail_requirements must be an object")

    artifact_policy = config.get("artifact_policy", {})
    if artifact_policy.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact_policy.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def evaluate_beta06_gate(config: dict[str, Any], beta05_report: dict[str, Any]) -> Beta06GateResult:
    config_issues = validate_beta06_config(config)

    guardrail_issues: list[str] = []
    required_guardrails = config["guardrail_requirements"]
    for key, expected in required_guardrails.items():
        actual = beta05_report.get(key)
        if actual != expected:
            guardrail_issues.append(f"{key} expected {expected!r}, got {actual!r}")
    guardrails_ok = len(guardrail_issues) == 0

    missing_true: list[str] = []
    for key in config["required_true_conditions_for_ready"]:
        if beta05_report.get(key) is not True:
            missing_true.append(key)

    violated_false: list[str] = []
    for key in config["required_false_conditions_for_ready"]:
        if beta05_report.get(key) is not False:
            violated_false.append(key)

    ready_conditions_ok = (len(missing_true) == 0) and (len(violated_false) == 0)
    ready_for_connecting_stage = guardrails_ok and ready_conditions_ok

    return Beta06GateResult(
        config_valid=(len(config_issues) == 0),
        config_issues=config_issues,
        guardrails_ok=guardrails_ok,
        guardrail_issues=guardrail_issues,
        ready_conditions_ok=ready_conditions_ok,
        missing_true_conditions=missing_true,
        violated_false_conditions=violated_false,
        ready_for_connecting_stage=ready_for_connecting_stage,
    )


def load_and_evaluate(beta05_report: dict[str, Any], path: Path | None = None) -> tuple[dict[str, Any], Beta06GateResult]:
    config = load_json(path or CONFIG_PATH)
    result = evaluate_beta06_gate(config, beta05_report)
    if result.config_issues:
        raise RuntimeError("GIB beta0.6 gate config validation failed: " + "; ".join(result.config_issues))
    return config, result
