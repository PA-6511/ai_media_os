#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_10_human_unlock_decision_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase7_10_human_unlock_decision.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_10_human_unlock_decision_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_10_human_unlock_decision_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_decision(
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

    policy = _load_json(policy_path) if policy_path.exists() else {}
    review = _load_json(review_path) if review_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not review_path.exists():
        safety_violations.append(f"missing_review: {review_path}")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    evidence_missing = False
    evidence_status = None
    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            evidence_missing = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        evidence_status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": evidence_status})

    for key in [
        "human_decision_is_execution_permission",
        "approve_draft_create_only_currently_allowed",
        "approve_draft_create_only_activation_allowed_in_this_phase",
        "unlock_in_this_phase",
        "wordpress_write_executed",
        "wordpress_api_call_allowed",
        "publish_allowed",
    ]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    decision = review.get("decision")
    requested_token = review.get("requested_token")
    if decision in set(policy.get("forbidden_decisions_in_phase7_10", [])):
        safety_violations.append(f"forbidden_decision: {decision}")
    if requested_token == "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("requested_token APPROVE_DRAFT_CREATE_ONLY is forbidden in phase7_10")

    allowed_decisions = set(policy.get("allowed_decisions_in_phase7_10", []))
    if decision is not None and decision not in allowed_decisions and decision not in set(policy.get("forbidden_decisions_in_phase7_10", [])):
        safety_violations.append(f"invalid_decision: {decision}")

    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for ack_key in policy.get("required_acknowledgements", []):
        if review.get(ack_key) is not True:
            safety_violations.append(f"{ack_key} must be true")

    scope = review.get("approval_scope", {})
    for key in ["draft_create_only", "publish", "update", "delete", "bulk", "external_export"]:
        if scope.get(key) is not False:
            safety_violations.append(f"approval_scope.{key} must be false")

    if evidence_missing:
        safety_violations.append("required evidence missing")
    elif evidence_status != policy.get("required_phase7_9_status"):
        safety_violations.append(
            f"phase7_9 status must be {policy.get('required_phase7_9_status')} but got {evidence_status}"
        )

    if safety_violations:
        status = "ABORT"
    elif decision == "ACKNOWLEDGE_UNLOCK_REVIEW_ONLY":
        status = "PASS_REVIEW_ONLY_NO_GO"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("human requested fix before token validation")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("human rejected unlock review package")
    elif decision == "ABORT":
        status = "ABORT"
        errors.append("human abort decision")
    else:
        status = "ABORT"
        errors.append(f"invalid decision: {decision}")

    result = {
        "phase": "Phase 7-10",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "human_decision_is_execution_permission": False,
        "target_item_count": review.get("target_item_count"),
        "human_decision_summary": {
            "review_id": review.get("review_id"),
            "operator": review.get("operator"),
            "decision": decision,
            "requested_token": requested_token,
            "candidate_id": review.get("candidate_id"),
        },
        "evidence_summary": evidence_summary,
        "approval_scope": scope,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-11 APPROVE_DRAFT_CREATE_ONLY unlock token final validation, still locked",
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
        "# Phase 7-10 Human Unlock Decision Report",
        "",
        "## Purpose",
        "- Validate human unlock-review decision while keeping NO_GO and lock state.",
        "",
        "## Human Decision Summary",
        f"- review_id: {result.get('human_decision_summary', {}).get('review_id')}",
        f"- operator: {result.get('human_decision_summary', {}).get('operator')}",
        f"- decision: {result.get('human_decision_summary', {}).get('decision')}",
        f"- requested_token: {result.get('human_decision_summary', {}).get('requested_token')}",
        f"- target_item_count: {result.get('target_item_count')}",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
            "",
            "## Approval Scope",
        ]
    )
    for key, value in result.get("approval_scope", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
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
    result = validate_decision()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_REVIEW_ONLY_NO_GO", "WARN", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
