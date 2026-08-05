from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta09_validator import validate_beta09_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta095_approval_evidence_format.json"


@dataclass
class EvidenceFormatResult:
    config_valid: bool
    config_issues: list[str]
    token_format_valid: bool
    change_id_format_valid: bool
    secret_handling_allowed: bool
    beta09_prereq_ok: bool
    beta09_prereq_issues: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta095_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta095.approval_evidence_format.v0.1":
        issues.append("schema_version must be gib.beta095.approval_evidence_format.v0.1")
    if config.get("beta_version") != "beta0.95":
        issues.append("beta_version must be beta0.95")
    if config.get("status") != "DRY_RUN_APPROVAL_EVIDENCE_FORMAT_ONLY":
        issues.append("status must be DRY_RUN_APPROVAL_EVIDENCE_FORMAT_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("manual_approval_required") is not True:
        issues.append("manual_approval_required must be true")

    for flag in ["real_llm_call_allowed", "execution_allowed", "generate_call_allowed", "chat_call_allowed"]:
        if config.get(flag) is not False:
            issues.append(f"{flag} must be false")

    evidence = config.get("approval_evidence")
    if not isinstance(evidence, dict):
        return issues + ["approval_evidence must be an object"]

    if evidence.get("token_required") is not True:
        issues.append("approval_evidence.token_required must be true")
    if evidence.get("change_id_required") is not True:
        issues.append("approval_evidence.change_id_required must be true")
    if evidence.get("secret_value_handling_allowed") is not False:
        issues.append("approval_evidence.secret_value_handling_allowed must be false")

    for key in ["token_regex", "token_sample", "change_id_regex", "change_id_sample"]:
        if not isinstance(evidence.get(key), str) or not evidence.get(key):
            issues.append(f"approval_evidence.{key} must be a non-empty string")

    artifact = config.get("artifact_policy", {})
    if artifact.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def evaluate_evidence_gate(config: dict[str, Any], beta09_report: dict[str, Any]) -> EvidenceFormatResult:
    issues = validate_beta095_config(config)
    evidence = config["approval_evidence"]

    token_format_valid = re.fullmatch(evidence["token_regex"], evidence["token_sample"]) is not None
    change_id_format_valid = re.fullmatch(evidence["change_id_regex"], evidence["change_id_sample"]) is not None

    beta09_prereq_issues: list[str] = []
    if beta09_report.get("final_status") != "PASS_DRY_RUN_BETA09_FIRST_CALL_HANDOFF_NO_EXECUTION":
        beta09_prereq_issues.append("beta09 final_status is not PASS")
    if beta09_report.get("can_execute_now") is not False:
        beta09_prereq_issues.append("beta09 can_execute_now must be false")
    if beta09_report.get("production_status") != "NO_GO":
        beta09_prereq_issues.append("beta09 production_status must be NO_GO")

    return EvidenceFormatResult(
        config_valid=(len(issues) == 0),
        config_issues=issues,
        token_format_valid=token_format_valid,
        change_id_format_valid=change_id_format_valid,
        secret_handling_allowed=bool(evidence["secret_value_handling_allowed"]),
        beta09_prereq_ok=(len(beta09_prereq_issues) == 0),
        beta09_prereq_issues=beta09_prereq_issues,
    )


def load_and_evaluate(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], EvidenceFormatResult]:
    config = load_json(path or CONFIG_PATH)
    beta09 = validate_beta09_contract()
    result = evaluate_evidence_gate(config, beta09)
    if result.config_issues:
        raise RuntimeError("GIB beta0.95 config validation failed: " + "; ".join(result.config_issues))
    return config, beta09, result
