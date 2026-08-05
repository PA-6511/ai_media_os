from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FALSE_FLAGS: list[str] = [
    "execution_allowed",
    "external_network_allowed",
    "credential_access_allowed",
    "wordpress_write_allowed",
    "systemd_operation_allowed",
    "model_runtime_enabled",
    "real_llm_call_allowed",
]

REQUIRED_TRUE_FLAGS: list[str] = []

REQUIRED_ALLOWED_TASK_TYPES: list[str] = [
    "phase_log_summary",
    "validator_result_explain",
    "product_summary",
    "social_post_draft",
    "article_outline",
    "compliance_classify",
    "security_log_explain",
]

REQUIRED_PROHIBITED_ACTIONS: list[str] = [
    "credential_access",
    "wordpress_write",
    "external_api_call",
    "systemd_operation",
    "real_llm_call",
    "go_nogo_decision",
]


def load_json(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    with target.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {target}")
    return data


def validate_policy(policy: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if policy.get("block_id") != "GIB":
        issues.append("block_id must be GIB")
    if policy.get("status") != "DESIGN_ONLY":
        issues.append("status must be DESIGN_ONLY")
    if policy.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if policy.get("execution_mode") != "DRY_RUN_ONLY":
        issues.append("execution_mode must be DRY_RUN_ONLY")

    for flag in REQUIRED_FALSE_FLAGS:
        if policy.get(flag) is not False:
            issues.append(f"{flag} must be false")

    for flag in REQUIRED_TRUE_FLAGS:
        if policy.get(flag) is not True:
            issues.append(f"{flag} must be true")

    allowed_task_types = policy.get("allowed_task_types")
    if allowed_task_types != REQUIRED_ALLOWED_TASK_TYPES:
        issues.append("allowed_task_types must match the fixed alpha task list")

    prohibited_actions = policy.get("prohibited_actions")
    if not isinstance(prohibited_actions, list):
        issues.append("prohibited_actions must be a list")
    else:
        missing = sorted(set(REQUIRED_PROHIBITED_ACTIONS) - set(prohibited_actions))
        if missing:
            issues.append(f"missing prohibited_actions: {missing}")

    report_write_scope = policy.get("report_write_scope")
    if report_write_scope != ["generic_inference_block_ai/reports"]:
        issues.append("report_write_scope must be limited to generic_inference_block_ai/reports")

    return issues


def assert_policy_safe(policy_path: str | Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    issues = validate_policy(policy)
    if issues:
        raise RuntimeError("GIB alpha policy validation failed: " + "; ".join(issues))
    return policy
