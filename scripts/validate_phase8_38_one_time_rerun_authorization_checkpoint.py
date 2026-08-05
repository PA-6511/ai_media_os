#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_38_one_time_rerun_authorization_checkpoint_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_38_one_time_rerun_authorization_checkpoint.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_38_one_time_rerun_authorization_checkpoint_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_38_one_time_rerun_authorization_checkpoint_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_one_time_rerun_authorization_checkpoint(
    policy_path: Path = DEFAULT_POLICY,
    review_path: Path = DEFAULT_REVIEW,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    review_path = Path(review_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    evidence_summary: list[dict[str, Any]] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)
    for flag in [
        "authorization_is_execution_permission",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"{flag} must be false")

    if policy.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")
    if policy.get("max_manual_rerun_count") != 1:
        safety_violations.append("max_manual_rerun_count must be 1")

    root = _resolve_root(policy_path)
    revalidation_status = None
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        revalidation_status = status
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status == "ABORT":
            safety_violations.append(f"evidence_terminal_status: {rel}={status}")

    if not review_path.exists():
        errors.append(f"missing_human_review: {review_path}")
        result = _build_result("FAIL", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    review = _load_json(review_path)
    decision = review.get("decision", "")
    if review.get("secret_values_included") is True:
        safety_violations.append("secret_values_included must be false")
    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")
    if review.get("max_manual_rerun_count") != 1:
        safety_violations.append("max_manual_rerun_count must be 1")

    for ack in policy.get("required_acknowledgements", []):
        if review.get(ack) is not True:
            safety_violations.append(f"{ack} must be true")

    scope = review.get("approval_scope", {})
    for key, expected in policy.get("approval_scope_required", {}).items():
        if scope.get(key) != expected:
            safety_violations.append(f"approval_scope.{key} must be {expected}")

    if safety_violations:
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    ready_status = policy.get("ready_revalidation_status")
    blocked_statuses = set(policy.get("blocked_revalidation_statuses", []))

    if decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("operator requested fix")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("operator rejected authorization checkpoint")
    elif decision == "ABORT":
        status = "ABORT"
    elif decision == "AUTHORIZE_ONE_TIME_MANUAL_RERUN_HANDOFF_ONLY":
        if revalidation_status == ready_status:
            status = "ONE_TIME_RERUN_AUTHORIZED_FOR_HANDOFF_ONLY"
        else:
            status = "ABORT"
            safety_violations.append("cannot authorize while revalidation is not ready")
    elif decision == "NO_GO_CREDENTIALS_MISSING":
        if revalidation_status in blocked_statuses:
            status = "ONE_TIME_RERUN_AUTH_BLOCKED_CREDENTIALS_MISSING"
        else:
            status = "ABORT"
            safety_violations.append("NO_GO decision does not match revalidation status")
    else:
        status = "ABORT"
        safety_violations.append(f"unknown_decision: {decision}")

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-38",
        "status": status,
        "production_status": "NO_GO",
        "actual_go_decision_issued": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "authorization_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "max_manual_rerun_count": policy.get("max_manual_rerun_count", 1),
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-39 existing Phase 8-6 to Phase 8-10 manual rerun command bundle"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-38 One-Time Rerun Authorization Checkpoint Report",
        "",
        "## Purpose",
        "Validate one-time rerun authorization checkpoint without execution.",
        "",
        "## Revalidation Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend([
        "",
        "## Operator Decision",
        f"- status: {result.get('status')}",
        "",
        "## Authorization Scope",
        "- one-time handoff scope is enforced.",
        "",
        "## One-Time Boundary",
        f"- max_manual_rerun_count: {result.get('max_manual_rerun_count')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- authorization_is_execution_permission: {result.get('authorization_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- phase8_6_to_8_10_executed: {result.get('phase8_6_to_8_10_executed')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_one_time_rerun_authorization_checkpoint()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "ONE_TIME_RERUN_AUTHORIZED_FOR_HANDOFF_ONLY",
        "ONE_TIME_RERUN_AUTH_BLOCKED_CREDENTIALS_MISSING",
        "WARN",
        "FAIL",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
