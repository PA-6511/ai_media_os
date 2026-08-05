from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta1_prep_audit_index import build_beta1_prep_audit_index
from generic_inference_block_ai.src.gib_beta1_prep_validator import validate_beta1_prep_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta1_prep_b_approval_protocol.json"


@dataclass
class Beta1PrepBResult:
    config_valid: bool
    config_issues: list[str]
    prerequisites_ok: bool
    prerequisite_issues: list[str]
    protocol_ok: bool
    protocol_issues: list[str]
    non_execution_ok: bool
    non_execution_issues: list[str]
    can_execute_now: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def validate_beta1_prep_b_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta1.prep_b.approval_protocol.v0.1":
        issues.append("schema_version must be gib.beta1.prep_b.approval_protocol.v0.1")
    if config.get("phase") != "beta1_prep_b":
        issues.append("phase must be beta1_prep_b")
    if config.get("status") != "DRY_RUN_BETA1_PREP_B_APPROVAL_PROTOCOL_ONLY":
        issues.append("status must be DRY_RUN_BETA1_PREP_B_APPROVAL_PROTOCOL_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")

    for key in (
        "real_llm_call_allowed",
        "execution_allowed",
        "generate_call_allowed",
        "chat_call_allowed",
        "can_execute_now",
    ):
        if config.get(key) is not False:
            issues.append(f"{key} must be false")

    if config.get("output_scope") != "generic_inference_block_ai/reports":
        issues.append("output_scope must be generic_inference_block_ai/reports")

    protocol = config.get("approval_protocol", {})
    template = protocol.get("required_approval_statement_template")
    if not isinstance(template, str) or len(template) < 40:
        issues.append("approval_protocol.required_approval_statement_template must be a descriptive string")

    required_identifiers = protocol.get("required_identifiers")
    if required_identifiers != ["APPROVAL_TOKEN_ID", "CHANGE_MANAGEMENT_ID"]:
        issues.append("approval_protocol.required_identifiers must be [APPROVAL_TOKEN_ID, CHANGE_MANAGEMENT_ID]")

    id_rules = protocol.get("identifier_reference_rules", {})
    if not isinstance(id_rules.get("approval_token"), str):
        issues.append("approval_protocol.identifier_reference_rules.approval_token must be string regex")
    if not isinstance(id_rules.get("change_management_id"), str):
        issues.append("approval_protocol.identifier_reference_rules.change_management_id must be string regex")

    if protocol.get("manual_only") is not True:
        issues.append("approval_protocol.manual_only must be true")
    if protocol.get("auto_execute_after_approval") is not False:
        issues.append("approval_protocol.auto_execute_after_approval must be false")

    guards = config.get("non_execution_guards", {})
    for key in (
        "keep_real_llm_call_allowed_false",
        "keep_execution_allowed_false",
        "keep_generate_chat_unexecuted",
        "wordpress_write_forbidden",
        "credential_access_forbidden",
        "systemd_forbidden",
    ):
        if guards.get(key) is not True:
            issues.append(f"non_execution_guards.{key} must be true")

    required = config.get("required_prerequisites", {})
    if required.get("beta1_prep_report") != "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED":
        issues.append("required_prerequisites.beta1_prep_report must match expected status")
    if required.get("beta1_prep_a_report") != "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED":
        issues.append("required_prerequisites.beta1_prep_a_report must match expected status")

    return issues


def evaluate_beta1_prep_b(
    config: dict[str, Any],
    prep_report: dict[str, Any],
    prep_a_report: dict[str, Any],
) -> Beta1PrepBResult:
    config_issues = validate_beta1_prep_b_config(config)

    prereq_issues: list[str] = []
    if prep_report.get("final_status") != "PASS_DRY_RUN_BETA1_PREP_RUNBOOK_FIXED":
        prereq_issues.append("beta1 prep final_status is not PASS")
    if prep_report.get("can_execute_now") is not False:
        prereq_issues.append("beta1 prep can_execute_now must be false")

    if prep_a_report.get("final_status") != "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED":
        prereq_issues.append("beta1 prep-a final_status is not PASS")
    if prep_a_report.get("reference_reports_ready") is not True:
        prereq_issues.append("beta1 prep-a reference_reports_ready must be true")

    continuity = prep_a_report.get("guardrail_continuity", {})
    if continuity.get("all_real_llm_call_allowed_false") is not True:
        prereq_issues.append("beta1 prep-a all_real_llm_call_allowed_false must be true")
    if continuity.get("all_execution_allowed_false") is not True:
        prereq_issues.append("beta1 prep-a all_execution_allowed_false must be true")
    if continuity.get("all_can_execute_now_false") is not True:
        prereq_issues.append("beta1 prep-a all_can_execute_now_false must be true")

    protocol_issues: list[str] = []
    template = config["approval_protocol"]["required_approval_statement_template"]
    if "{APPROVAL_TOKEN_ID}" not in template:
        protocol_issues.append("approval statement template must contain {APPROVAL_TOKEN_ID}")
    if "{CHANGE_MANAGEMENT_ID}" not in template:
        protocol_issues.append("approval statement template must contain {CHANGE_MANAGEMENT_ID}")
    if "does not authorize automatic execution" not in template:
        protocol_issues.append("approval statement template must include non-auto-execution clause")

    non_exec_issues: list[str] = []
    for key in (
        "real_llm_call_allowed",
        "execution_allowed",
        "generate_call_allowed",
        "chat_call_allowed",
        "can_execute_now",
    ):
        if config.get(key) is not False:
            non_exec_issues.append(f"{key} must remain false")

    return Beta1PrepBResult(
        config_valid=(len(config_issues) == 0),
        config_issues=config_issues,
        prerequisites_ok=(len(prereq_issues) == 0),
        prerequisite_issues=prereq_issues,
        protocol_ok=(len(protocol_issues) == 0),
        protocol_issues=protocol_issues,
        non_execution_ok=(len(non_exec_issues) == 0),
        non_execution_issues=non_exec_issues,
        can_execute_now=False,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Beta1PrepBResult]:
    config = load_json(path or CONFIG_PATH)
    prep_report = validate_beta1_prep_contract()
    prep_a_report = build_beta1_prep_audit_index()
    result = evaluate_beta1_prep_b(config, prep_report, prep_a_report)

    if result.config_issues:
        raise RuntimeError("GIB beta1 prep-b config validation failed: " + "; ".join(result.config_issues))

    return config, prep_report, prep_a_report, result
