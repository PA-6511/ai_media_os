from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta08_validator import validate_beta08_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta09_first_call_handoff.json"

_APPROVAL_TEXT = "I APPROVE FIRST REAL LOCAL LLM CALL FOR GIB BETA1 UNDER CHANGE CONTROL."


@dataclass
class HandoffEvaluation:
    config_valid: bool
    config_issues: list[str]
    beta08_prereq_ok: bool
    beta08_prereq_issues: list[str]
    target_valid: bool
    target_issues: list[str]
    promotion_conditions_documented: bool
    promotion_issues: list[str]
    can_execute_now: bool
    blocked_reasons: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta09_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta09.first_call_handoff.v0.1":
        issues.append("schema_version must be gib.beta09.first_call_handoff.v0.1")
    if config.get("beta_version") != "beta0.9":
        issues.append("beta_version must be beta0.9")
    if config.get("status") != "DRY_RUN_FIRST_CALL_HANDOFF_ONLY":
        issues.append("status must be DRY_RUN_FIRST_CALL_HANDOFF_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("handoff_ready") is not False:
        issues.append("handoff_ready must be false in beta0.9")

    manual = config.get("manual_approval", {})
    if manual.get("required") is not True:
        issues.append("manual_approval.required must be true")
    if manual.get("granted") is not False:
        issues.append("manual_approval.granted must be false")
    if manual.get("approval_statement") != _APPROVAL_TEXT:
        issues.append("manual_approval.approval_statement must match fixed text")

    current = config.get("current_guardrails", {})
    for flag in [
        "real_llm_call_allowed",
        "execution_allowed",
        "generate_call_allowed",
        "chat_call_allowed",
        "wordpress_write_allowed",
        "credential_access_allowed",
    ]:
        if current.get(flag) is not False:
            issues.append(f"current_guardrails.{flag} must be false")
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


def _validate_promotion_requirements(config: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    req = config.get("promotion_requirements_to_enable_real_call", {})

    expected_true_keys = [
        "real_llm_call_allowed_must_be_true",
        "execution_allowed_must_be_true",
        "change_control_ticket_required",
        "rollback_to_stub_plan_required",
        "localhost_only_required",
        "no_wordpress_write",
        "no_credential_direct_access",
    ]
    for key in expected_true_keys:
        if req.get(key) is not True:
            issues.append(f"promotion_requirements_to_enable_real_call.{key} must be true")

    return len(issues) == 0, issues


def evaluate_handoff(config: dict[str, Any], beta08_report: dict[str, Any]) -> HandoffEvaluation:
    config_issues = validate_beta09_config(config)

    beta08_issues: list[str] = []
    if beta08_report.get("final_status") != "PASS_DRY_RUN_BETA08_MANUAL_APPROVAL_GATE_NO_REAL_CALL":
        beta08_issues.append("beta08 final_status is not PASS")
    if beta08_report.get("auto_connect_triggered") is not False:
        beta08_issues.append("beta08 auto_connect_triggered must be false")
    if beta08_report.get("real_llm_call_allowed") is not False:
        beta08_issues.append("beta08 real_llm_call_allowed must be false")

    target_valid, target_issues = _validate_target(config)
    promo_ok, promo_issues = _validate_promotion_requirements(config)

    blocked_reasons: list[str] = []
    if config.get("manual_approval", {}).get("granted") is not True:
        blocked_reasons.append("manual_approval_not_granted")
    current = config.get("current_guardrails", {})
    if current.get("real_llm_call_allowed") is not True:
        blocked_reasons.append("real_llm_call_allowed_false")
    if current.get("execution_allowed") is not True:
        blocked_reasons.append("execution_allowed_false")

    can_execute_now = False

    return HandoffEvaluation(
        config_valid=(len(config_issues) == 0),
        config_issues=config_issues,
        beta08_prereq_ok=(len(beta08_issues) == 0),
        beta08_prereq_issues=beta08_issues,
        target_valid=target_valid,
        target_issues=target_issues,
        promotion_conditions_documented=promo_ok,
        promotion_issues=promo_issues,
        can_execute_now=can_execute_now,
        blocked_reasons=blocked_reasons,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], HandoffEvaluation]:
    config = load_json(path or CONFIG_PATH)
    beta08 = validate_beta08_contract()
    result = evaluate_handoff(config, beta08)
    if result.config_issues:
        raise RuntimeError("GIB beta0.9 config validation failed: " + "; ".join(result.config_issues))
    return config, beta08, result
