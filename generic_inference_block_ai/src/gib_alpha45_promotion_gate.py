from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CHECKLIST_PATH = _ROOT / "config" / "gib_alpha45_beta0_promotion_checklist.json"


@dataclass
class PromotionGateResult:
    checklist_valid: bool
    checklist_issues: list[str]
    all_decisions_made: bool
    missing_decisions: list[str]
    beta0_ready: bool
    blocked_reasons: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_checklist_schema(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.alpha45.promotion_checklist.v0.1":
        issues.append("schema_version must be gib.alpha45.promotion_checklist.v0.1")
    if config.get("design_status") != "DESIGN_ONLY":
        issues.append("design_status must be DESIGN_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("beta0_ready") is not False:
        issues.append("beta0_ready must be false in alpha4.5")

    check_items = config.get("check_items")
    if not isinstance(check_items, dict):
        return issues + ["check_items must be an object"]

    required_items = [
        "runtime_target",
        "execution_host",
        "model_allowlist",
        "network_policy",
        "artifact_policy",
        "failure_fallback",
    ]
    for item in required_items:
        if item not in check_items:
            issues.append(f"missing check_items.{item}")

    runtime_target = check_items.get("runtime_target", {})
    if isinstance(runtime_target, dict) and runtime_target.get("decided") is True:
        selected = runtime_target.get("selected")
        allowed_values = runtime_target.get("allowed_values", [])
        if selected not in allowed_values:
            issues.append("check_items.runtime_target.selected must be in allowed_values when decided")

    execution_host = check_items.get("execution_host", {})
    if isinstance(execution_host, dict) and execution_host.get("decided") is True:
        selected = execution_host.get("selected")
        allowed_values = execution_host.get("allowed_values", [])
        if selected not in allowed_values:
            issues.append("check_items.execution_host.selected must be in allowed_values when decided")

    model_allowlist = check_items.get("model_allowlist", {})
    if isinstance(model_allowlist, dict) and model_allowlist.get("decided") is True:
        selected_models = model_allowlist.get("selected_models", [])
        allowed_patterns = model_allowlist.get("allowed_patterns", [])
        if not isinstance(selected_models, list) or not selected_models:
            issues.append("check_items.model_allowlist.selected_models must be a non-empty list when decided")
        else:
            for model in selected_models:
                if not any(pattern in str(model) for pattern in allowed_patterns):
                    issues.append("check_items.model_allowlist.selected_models contains value outside allowed_patterns")

    network_policy = check_items.get("network_policy", {})
    if isinstance(network_policy, dict) and network_policy.get("decided") is True:
        if network_policy.get("localhost_only_required") is not True:
            issues.append("check_items.network_policy.localhost_only_required must be true")
        if network_policy.get("localhost_only_confirmed") is not True:
            issues.append("check_items.network_policy.localhost_only_confirmed must be true when decided")

    artifact_policy = check_items.get("artifact_policy", {})
    if isinstance(artifact_policy, dict) and artifact_policy.get("decided") is True:
        if artifact_policy.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
            issues.append("check_items.artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
        if artifact_policy.get("reports_only_confirmed") is not True:
            issues.append("check_items.artifact_policy.reports_only_confirmed must be true when decided")

    failure_fallback = check_items.get("failure_fallback", {})
    if isinstance(failure_fallback, dict) and failure_fallback.get("decided") is True:
        if failure_fallback.get("fallback_runtime") != "stub":
            issues.append("check_items.failure_fallback.fallback_runtime must be stub")
        if failure_fallback.get("fallback_mandatory") is not True:
            issues.append("check_items.failure_fallback.fallback_mandatory must be true")

    guardrails = config.get("beta0_guardrails")
    if not isinstance(guardrails, dict):
        issues.append("beta0_guardrails must be an object")
    else:
        if guardrails.get("wordpress_write_allowed") is not False:
            issues.append("beta0_guardrails.wordpress_write_allowed must be false")
        if guardrails.get("credential_access_allowed") is not False:
            issues.append("beta0_guardrails.credential_access_allowed must be false")
        if guardrails.get("execution_allowed") is not False:
            issues.append("beta0_guardrails.execution_allowed must be false")
        if guardrails.get("model_runtime_enabled") is not True:
            issues.append("beta0_guardrails.model_runtime_enabled must be true")
        if guardrails.get("real_llm_call_allowed") is not False:
            issues.append("beta0_guardrails.real_llm_call_allowed must be false")

    return issues


def evaluate_promotion_gate(config: dict[str, Any]) -> PromotionGateResult:
    issues = validate_checklist_schema(config)
    check_items = config.get("check_items", {})

    missing_decisions: list[str] = []
    for key in [
        "runtime_target",
        "execution_host",
        "model_allowlist",
        "network_policy",
        "artifact_policy",
        "failure_fallback",
    ]:
        item = check_items.get(key, {})
        if not isinstance(item, dict) or item.get("decided") is not True:
            missing_decisions.append(key)

    all_decisions_made = len(missing_decisions) == 0

    blocked_reasons: list[str] = []
    if not all_decisions_made:
        blocked_reasons.append("promotion_checklist_not_fully_decided")

    guardrails = config.get("beta0_guardrails", {})
    if guardrails.get("real_llm_call_allowed") is not False:
        blocked_reasons.append("real_llm_call_must_remain_false_before_beta0")
    if guardrails.get("execution_allowed") is not False:
        blocked_reasons.append("execution_must_remain_false_before_beta0")

    beta0_ready = False
    return PromotionGateResult(
        checklist_valid=(len(issues) == 0),
        checklist_issues=issues,
        all_decisions_made=all_decisions_made,
        missing_decisions=missing_decisions,
        beta0_ready=beta0_ready,
        blocked_reasons=blocked_reasons,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], PromotionGateResult]:
    config = load_json(path or CHECKLIST_PATH)
    result = evaluate_promotion_gate(config)
    if result.checklist_issues:
        raise RuntimeError("GIB alpha4.5 checklist validation failed: " + "; ".join(result.checklist_issues))
    return config, result
