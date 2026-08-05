#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_1_explicit_human_approval_policy.json"
DEFAULT_APPROVAL = ROOT / "exchange/human_review/phase8_1_explicit_human_approval.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_1_explicit_human_approval_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_1_explicit_human_approval_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_explicit_human_approval(
    policy_path: Path = DEFAULT_POLICY,
    approval_path: Path = DEFAULT_APPROVAL,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    approval_path = Path(approval_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    approval = _load_json(approval_path) if approval_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not approval_path.exists():
        safety_violations.append(f"missing_approval_file: {approval_path}")

    for key in [
        "approval_file_is_execution_permission",
        "approve_draft_create_only_currently_allowed",
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

    decision = approval.get("decision")
    if decision in set(policy.get("forbidden_human_decisions", [])):
        safety_violations.append(f"forbidden_human_decision: {decision}")

    allowed_decisions = set(policy.get("allowed_human_decisions", []))
    if decision and decision not in allowed_decisions and decision not in set(policy.get("forbidden_human_decisions", [])):
        safety_violations.append(f"invalid_human_decision: {decision}")

    if approval.get("approval_token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approval_token must be APPROVE_DRAFT_CREATE_ONLY")

    if approval.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for key in policy.get("required_acknowledgements", []):
        if approval.get(key) is not True:
            safety_violations.append(f"{key} must be true")

    scope = approval.get("approval_scope", {})
    required_scope = policy.get("approval_scope_required", {})
    if scope.get("draft_create_only") is not required_scope.get("draft_create_only"):
        safety_violations.append("approval_scope.draft_create_only must be true")

    for key in ["publish", "update", "delete", "bulk", "external_export"]:
        if scope.get(key) is not False:
            safety_violations.append(f"approval_scope.{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    evidence_missing = False
    phase714_status = None
    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            evidence_missing = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        status = payload.get("status") or payload.get("overall_status")
        phase714_status = status
        evidence_summary.append({"path": rel, "exists": True, "status": status})

    if evidence_missing:
        safety_violations.append("required evidence missing")
    elif phase714_status != policy.get("required_phase7_14_status"):
        safety_violations.append(
            f"phase7_14 status must be {policy.get('required_phase7_14_status')} but got {phase714_status}"
        )

    if safety_violations:
        status = "ABORT"
    elif decision == "APPROVE_DRAFT_CREATE_ONLY_EXPLICIT_FOR_PHASE8_PREFLIGHT":
        status = "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("human requested fix before final preflight")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("human rejected explicit approval package")
    elif decision == "ABORT":
        status = "ABORT"
        errors.append("human abort decision")
    else:
        status = "ABORT"
        errors.append(f"invalid decision: {decision}")

    result = {
        "phase": "Phase 8-1",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "approval_file_is_execution_permission": False,
        "target_item_count": approval.get("target_item_count"),
        "approval_token": approval.get("approval_token"),
        "evidence_summary": evidence_summary,
        "approval_scope": scope,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-2 final live-preflight with explicit approval file",
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
        "# Phase 8-1 Explicit Human Approval Report",
        "",
        "## Purpose",
        "- Validate explicit human approval file for preflight use only.",
        "",
        "## Human Approval Summary",
        f"- status: {result.get('status')}",
        f"- approval_token: {result.get('approval_token')}",
        f"- target_item_count: {result.get('target_item_count')}",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
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
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
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
    result = validate_explicit_human_approval()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY", "WARN", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
