#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_6_human_approval_evidence_package_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase7_6_human_approval_evidence_package.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_6_human_approval_evidence_package_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_6_human_approval_evidence_package_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_package(
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

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        policy: dict[str, Any] = {}
    else:
        policy = _load_json(policy_path)

    if not review_path.exists():
        safety_violations.append(f"missing_review: {review_path}")
        review: dict[str, Any] = {}
    else:
        review = _load_json(review_path)

    if policy.get("approval_is_execution_permission") is not False:
        safety_violations.append("approval_is_execution_permission must be false")
    if policy.get("approve_draft_create_only_currently_allowed") is not False:
        safety_violations.append("approve_draft_create_only_currently_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    required = policy.get("required_human_approval_fields", [])
    for field in required:
        if field not in review:
            safety_violations.append(f"missing_field: {field}")

    decision = review.get("decision")
    if decision in set(policy.get("forbidden_decisions_in_phase7_6", [])):
        safety_violations.append(f"forbidden_decision: {decision}")

    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")
    if review.get("acknowledged_no_go") is not True:
        safety_violations.append("acknowledged_no_go must be true")
    if review.get("acknowledged_no_publish") is not True:
        safety_violations.append("acknowledged_no_publish must be true")

    scope = review.get("approval_scope", {})
    required_scope = policy.get("approval_scope_required", {})
    for key, expected in required_scope.items():
        if scope.get(key) != expected:
            safety_violations.append(f"approval_scope.{key} must be {expected}")

    if safety_violations:
        status = "ABORT"
    elif decision == "ACKNOWLEDGE_PRE_UNLOCK_REVIEW_ONLY":
        status = "PASS_DESIGN_ONLY"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("human requested fix before next phase")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("human rejected pre-unlock package")
    elif decision == "ABORT":
        status = "ABORT"
        errors.append("human abort decision")
    else:
        status = "ABORT"
        errors.append(f"invalid decision: {decision}")

    result = {
        "phase": "Phase 7-6",
        "name": "human_approval_evidence_package_policy",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "approval_is_execution_permission": False,
        "human_review_summary": {
            "review_id": review.get("review_id"),
            "operator": review.get("operator"),
            "decision": decision,
            "target_item_count": review.get("target_item_count"),
            "candidate_id": review.get("candidate_id"),
        },
        "approval_scope": scope,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-7 APPROVE_DRAFT_CREATE_ONLY activation readiness gate design only",
        ),
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-6 Human Approval Evidence Package Report",
        "",
        "## Purpose",
        "- Validate human approval evidence package for pre-unlock review only.",
        "",
        "## Human Review Summary",
        f"- review_id: {result.get('human_review_summary', {}).get('review_id')}",
        f"- operator: {result.get('human_review_summary', {}).get('operator')}",
        f"- decision: {result.get('human_review_summary', {}).get('decision')}",
        f"- target_item_count: {result.get('human_review_summary', {}).get('target_item_count')}",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        "",
        "## Approval Scope",
    ]
    for key, value in result.get("approval_scope", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_package()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DESIGN_ONLY", "WARN", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
