#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_7_rerun_approval_review_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_7_rerun_approval_review.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_7_rerun_approval_review_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_7_rerun_approval_review_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_rerun_approval_review(
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

    if policy.get("rerun_review_is_execution_permission") is not False:
        safety_violations.append("rerun_review_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    decision = review.get("decision")
    if decision in set(policy.get("forbidden_decisions", [])):
        safety_violations.append(f"forbidden_decision: {decision}")

    allowed_decisions = set(policy.get("allowed_decisions", []))
    if decision and decision not in allowed_decisions and decision not in set(policy.get("forbidden_decisions", [])):
        safety_violations.append(f"invalid_decision: {decision}")

    if review.get("approval_token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approval_token must be APPROVE_DRAFT_CREATE_ONLY")

    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for key in policy.get("required_acknowledgements", []):
        if review.get(key) is not True:
            safety_violations.append(f"{key} must be true")

    scope = review.get("approval_scope", {})
    required_scope = policy.get("approval_scope_required", {})
    if scope.get("rerun_preflight_only") is not required_scope.get("rerun_preflight_only"):
        safety_violations.append("approval_scope.rerun_preflight_only must be true")
    if scope.get("draft_create_only") is not False:
        safety_violations.append("approval_scope.draft_create_only must be false")
    for key in ["publish", "update", "delete", "bulk", "external_export"]:
        if scope.get(key) is not False:
            safety_violations.append(f"approval_scope.{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    evidence_map: dict[str, Any] = {}
    missing_evidence = False

    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        st = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": st})
        if "phase8_1" in rel:
            evidence_map["phase8_1"] = st
        elif "phase8_5" in rel:
            evidence_map["phase8_5"] = st
        elif "phase8_6" in rel:
            evidence_map["phase8_6"] = st

    if missing_evidence:
        safety_violations.append("required evidence missing")
    else:
        required_statuses = policy.get("required_statuses", {})
        for key in ["phase8_1", "phase8_5"]:
            actual = evidence_map.get(key)
            expected = required_statuses.get(key)
            if actual != expected:
                safety_violations.append(f"{key} status must be {expected} but got {actual}")

        phase86_status = evidence_map.get("phase8_6")
        allowed_cred = set(policy.get("allowed_credential_statuses", []))
        if phase86_status not in allowed_cred:
            safety_violations.append(f"phase8_6 status must be in allowed_credential_statuses but got {phase86_status}")

    if safety_violations:
        status = "ABORT"
    elif decision == "ACKNOWLEDGE_RERUN_REVIEW_ONLY":
        status = "PASS_RERUN_REVIEW_ONLY"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("human requested fix before rerun preflight")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("human rejected rerun review package")
    elif decision == "ABORT":
        status = "ABORT"
        errors.append("human abort decision")
    else:
        status = "ABORT"
        errors.append(f"invalid decision: {decision}")

    result = {
        "phase": "Phase 8-7",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "rerun_review_is_execution_permission": False,
        "target_item_count": review.get("target_item_count"),
        "approval_token": review.get("approval_token"),
        "evidence_summary": evidence_summary,
        "approval_scope": scope,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-8 final credentialed live-preflight",
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
        "# Phase 8-7 Rerun Approval Review Report",
        "",
        "## Purpose",
        "- Confirm that prior approval can be preserved for rerun preflight. Not direct execution permission.",
        "",
        "## Prior Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Human Review Summary",
            f"- status: {result.get('status')}",
            f"- approval_token: {result.get('approval_token')}",
            f"- target_item_count: {result.get('target_item_count')}",
            "",
            "## Approval Scope",
        ]
    )
    for key, value in result.get("approval_scope", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- rerun_review_is_execution_permission: {result.get('rerun_review_is_execution_permission')}",
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
    result = validate_rerun_approval_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_RERUN_REVIEW_ONLY", "WARN", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
