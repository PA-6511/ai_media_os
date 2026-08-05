#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_7_approve_draft_create_only_readiness_gate.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase7_7_approve_draft_create_only_readiness_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_7_approve_draft_create_only_readiness_gate_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_7_approve_draft_create_only_readiness_gate_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_gate(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    request = _load_json(request_path) if request_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not request_path.exists():
        safety_violations.append(f"missing_request: {request_path}")

    if request.get("activation_requested") is True:
        safety_violations.append("activation_requested must be false")
    if request.get("approve_draft_create_only_requested") is True:
        safety_violations.append("approve_draft_create_only_requested must be false")
    if policy.get("approve_draft_create_only_currently_allowed") is not False:
        safety_violations.append("approve_draft_create_only_currently_allowed must be false")
    if policy.get("readiness_is_activation") is not False:
        safety_violations.append("readiness_is_activation must be false")
    if policy.get("unlock_in_this_phase") is not False:
        safety_violations.append("unlock_in_this_phase must be false")

    if request.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    flags = request.get("safety_flags", {})
    for key in [
        "wordpress_write_executed",
        "publish_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]:
        if flags.get(key) is not False:
            safety_violations.append(f"safety_flags.{key} must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    missing_evidence = False
    evidence_fail_abort = False
    condition_missing = False

    p75_status = None
    p76_status = None

    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if "phase7_5" in rel:
            p75_status = status
        if "phase7_6" in rel:
            p76_status = status
        if status in {"FAIL", "ABORT"}:
            evidence_fail_abort = True

    req = policy.get("required_conditions", {})
    if p75_status is not None and p75_status != req.get("phase7_5_status"):
        condition_missing = True
        warnings.append(f"phase7_5_status mismatch: {p75_status}")
    if p76_status is not None and p76_status != req.get("phase7_6_status"):
        condition_missing = True
        warnings.append(f"phase7_6_status mismatch: {p76_status}")
    if request.get("target_item_count") != req.get("target_item_count"):
        condition_missing = True
    if request.get("human_approval_required") is not req.get("human_approval_required"):
        condition_missing = True
    if flags.get("publish_allowed") is not req.get("publish_allowed"):
        condition_missing = True
    if flags.get("wordpress_write_executed") is not req.get("wordpress_write_executed"):
        condition_missing = True

    if safety_violations:
        status = "ABORT"
    elif evidence_fail_abort:
        status = "ABORT"
    elif missing_evidence:
        status = "NOT_READY"
    elif condition_missing:
        status = "NOT_READY"
    else:
        status = "READY_BUT_LOCKED"

    result = {
        "phase": "Phase 7-7",
        "name": "approve_draft_create_only_readiness_gate",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "readiness_is_activation": False,
        "unlock_in_this_phase": False,
        "target_item_count": request.get("target_item_count"),
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "evidence_summary": evidence_summary,
        "blocked_operations": [
            "wordpress_draft_create",
            "wordpress_publish",
            "wordpress_update",
            "wordpress_delete",
            "bulk_posting",
            "external_export",
            "vps_self_builder_execution",
        ],
        "allowed_next_step": policy.get(
            "allowed_next_step", "Phase 7-8 single draft create execution simulation DRY_RUN only"
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
        "# Phase 7-7 APPROVE_DRAFT_CREATE_ONLY Readiness Gate Report",
        "",
        "## Purpose",
        "- Validate readiness conditions while keeping APPROVE_DRAFT_CREATE_ONLY locked.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend(
        [
            "",
            "## Readiness Decision",
            f"- status: {result.get('status')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
            "",
            "## Blocked Operations",
        ]
    )
    for item in result.get("blocked_operations", []):
        lines.append(f"- {item}")
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
    result = validate_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"READY_BUT_LOCKED", "NOT_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
