#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_9_pre_unlock_overall_report_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_9_pre_unlock_overall_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_9_pre_unlock_overall_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_report(
    policy_path: Path = DEFAULT_POLICY,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    policy = _load_json(policy_path)
    root = _resolve_root(policy_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    summary: list[dict[str, Any]] = []

    for key in [
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")
    if policy.get("overall_is_execution_permission") is not False:
        safety_violations.append("overall_is_execution_permission must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    acceptable = set(policy.get("acceptable_statuses", []))
    warn_set = set(policy.get("warn_statuses", []))
    reject_set = set(policy.get("reject_statuses", []))

    missing = False
    has_warn = False
    has_reject = False

    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            missing = True
            summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        status = payload.get("status") or payload.get("overall_status") or payload.get("decision")
        summary.append({"path": rel, "exists": True, "status": status})
        if status in reject_set:
            has_reject = True
        elif status in warn_set:
            has_warn = True
        elif status not in acceptable:
            has_reject = True
            warnings.append(f"unlisted_status_treated_as_reject: {rel}={status}")

    if safety_violations:
        status = "ABORT"
    elif missing:
        status = "PRE_UNLOCK_NOT_READY"
    elif has_reject:
        status = "PRE_UNLOCK_NOT_READY"
    elif has_warn:
        status = "PRE_UNLOCK_READY_WITH_WARN_BUT_NO_GO"
    else:
        status = "PRE_UNLOCK_READY_BUT_NO_GO"

    result = {
        "phase": "Phase 7-9",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "overall_is_execution_permission": False,
        "evidence_summary": summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-10 human decision for one-item controlled WordPress draft creation unlock, still requiring explicit approval",
        ),
        "blocked_next_steps": policy.get("blocked_next_steps", []),
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-9 Pre-Unlock Overall Report",
        "",
        "## Purpose",
        "- Aggregate Phase 7 evidence and determine pre-unlock readiness while maintaining NO_GO.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Overall Decision",
            f"- status: {result.get('status')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
            f"- unlock_in_this_phase: {result.get('unlock_in_this_phase')}",
            "",
            "## Blocked Operations",
        ]
    )
    for item in result.get("blocked_next_steps", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Remaining Human Decision",
            "- Explicit human approval is still required before any unlock consideration.",
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
    result = generate_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "PRE_UNLOCK_READY_BUT_NO_GO",
        "PRE_UNLOCK_READY_WITH_WARN_BUT_NO_GO",
        "PRE_UNLOCK_NOT_READY",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
