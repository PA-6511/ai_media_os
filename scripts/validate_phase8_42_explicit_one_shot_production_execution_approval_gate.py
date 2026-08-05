#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_42_explicit_one_shot_production_execution_approval_gate_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_42_explicit_one_shot_production_execution_approval_gate.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_42_explicit_one_shot_production_execution_approval_gate_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_42_explicit_one_shot_production_execution_approval_gate_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase 8-42 Explicit One-Shot Production Execution Approval Gate Result",
        "",
        "## Final Status",
        f"- status: {result.get('status')}",
        f"- decision: {result.get('decision')}",
        f"- production_status: {result.get('production_status')}",
        f"- execution: {result.get('execution')}",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- execution_allowed: {result.get('execution_allowed')}",
            f"- actual_go_decision_issued: {result.get('actual_go_decision_issued')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_draft_created: {result.get('wordpress_draft_created')}",
            f"- secret_values_output: {result.get('secret_values_output')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_phase8_42(
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
        result = {
            "phase": "Phase 8-42",
            "status": "ABORT",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "execution_allowed": False,
            "actual_go_decision_issued": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "secret_values_output": False,
            "decision": "MISSING_POLICY",
            "errors": [f"missing_policy: {policy_path}"],
            "warnings": warnings,
            "safety_violations": safety_violations,
            "evidence_summary": evidence_summary,
            "allowed_next_step": "Keep NO_GO until policy is restored",
            "checked_at": _now_iso(),
        }
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)
    root = _resolve_root(policy_path)

    for flag in [
        "approval_gate_is_execution_permission",
        "execution_allowed",
        "actual_go_decision_issued",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "publish_allowed",
        "secret_values_output",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"policy.{flag} must be false")

    if policy.get("target_item_count") != 1:
        safety_violations.append("policy.target_item_count must be 1")

    required_statuses = policy.get("required_statuses", {})
    missing_evidence = False
    bad_status = False

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            errors.append(f"missing_evidence: {rel}")
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue

        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})

        accepted = required_statuses.get(rel, [])
        if accepted and status not in accepted:
            bad_status = True
            errors.append(f"unexpected_status: {rel}={status}")

        for must_false in [
            "execution_allowed",
            "actual_go_decision_issued",
            "wordpress_api_call_allowed",
            "wordpress_write_executed",
            "wordpress_draft_created",
            "secret_values_output",
        ]:
            if payload.get(must_false) is True:
                safety_violations.append(f"{rel}:{must_false}=true")

    decision = "MISSING_REVIEW"
    if not review_path.exists():
        errors.append(f"missing_human_review: {review_path}")
        result_status = "FAIL"
    else:
        review = _load_json(review_path)
        decision = str(review.get("decision", ""))

        if review.get("secret_values_included") is True:
            safety_violations.append("review.secret_values_included must be false")

        if review.get("target_item_count") != 1:
            safety_violations.append("review.target_item_count must be 1")

        for ack in policy.get("required_review_acknowledgements", []):
            if review.get(ack) is not True:
                safety_violations.append(f"review.{ack} must be true")

        if decision not in set(policy.get("allowed_decisions", [])):
            safety_violations.append(f"unknown_decision: {decision}")

        result_status = "PENDING"

    if safety_violations:
        result_status = "ABORT"
    elif missing_evidence or bad_status:
        result_status = "FAIL"
    elif decision == "DEFINE_GATE_ONLY_NO_EXECUTION":
        result_status = "PHASE8_42_APPROVAL_GATE_DEFINED_NO_EXECUTION"
    elif decision == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY":
        result_status = "PHASE8_42_EXPLICIT_ONE_SHOT_PRODUCTION_EXECUTION_APPROVAL_GRANTED_GATE_ONLY"
    elif decision == "REQUEST_FIX":
        result_status = "PHASE8_42_APPROVAL_GATE_REQUEST_FIX_NO_EXECUTION"
    elif decision == "REJECT":
        result_status = "PHASE8_42_APPROVAL_GATE_REJECTED_NO_EXECUTION"
    elif decision == "ABORT":
        result_status = "ABORT"
    else:
        result_status = "FAIL"

    if result_status in {
        "PHASE8_42_APPROVAL_GATE_DEFINED_NO_EXECUTION",
        "PHASE8_42_EXPLICIT_ONE_SHOT_PRODUCTION_EXECUTION_APPROVAL_GRANTED_GATE_ONLY",
    }:
        allowed_next_step = policy.get("allowed_next_step_if_gate_defined", "")
    else:
        allowed_next_step = policy.get("allowed_next_step_if_fix_required", "")

    result = {
        "phase": "Phase 8-42",
        "status": result_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "execution_allowed": False,
        "actual_go_decision_issued": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "secret_values_output": False,
        "approval_gate_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": 1,
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "evidence_summary": evidence_summary,
        "allowed_next_step": allowed_next_step,
        "checked_at": _now_iso(),
    }

    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_42()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_42_APPROVAL_GATE_DEFINED_NO_EXECUTION",
        "PHASE8_42_EXPLICIT_ONE_SHOT_PRODUCTION_EXECUTION_APPROVAL_GRANTED_GATE_ONLY",
        "PHASE8_42_APPROVAL_GATE_REQUEST_FIX_NO_EXECUTION",
        "PHASE8_42_APPROVAL_GATE_REJECTED_NO_EXECUTION",
        "FAIL",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())