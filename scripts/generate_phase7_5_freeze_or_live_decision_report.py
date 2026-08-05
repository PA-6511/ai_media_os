#!/usr/bin/env python3
"""Phase 7-5 Freeze-or-Live decision report (NO_GO maintained)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"
POLICY = ROOT / "config/phase7_5_freeze_or_live_decision_policy.json"
OUTPUT_JSON = LOGS / "phase7_5_freeze_or_live_decision_report.json"
OUTPUT_MD = LOGS / "phase7_5_freeze_or_live_decision_report.md"

REJECT_STATUSES = {"FAIL", "ABORT"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def build_report(logs_dir: Path | None = None, policy_path: Path | None = None) -> dict:
    policy_path = Path(policy_path or POLICY)
    policy = _load_json(policy_path)
    root_dir = _resolve_root(policy_path)
    effective_logs = Path(logs_dir) if logs_dir else root_dir / "exchange/logs"

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    evidence_summary: list[dict[str, Any]] = []

    if policy.get("approve_draft_create_only_currently_allowed") is not False:
        safety_violations.append("approve_draft_create_only_currently_allowed must be false")
    if policy.get("unlock_in_this_phase") is not False:
        safety_violations.append("unlock_in_this_phase must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    acceptable = set(policy.get("acceptable_statuses", []))
    missing_evidence = False
    has_reject = False

    for rel in policy.get("required_phase7_evidence", []):
        if logs_dir:
            evidence_path = effective_logs / Path(rel).name
        else:
            evidence_path = root_dir / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue

        payload = _load_json(evidence_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if status in REJECT_STATUSES:
            has_reject = True
        elif status not in acceptable:
            warnings.append(f"unacceptable_but_non_reject_status: {rel}={status}")

    outputs = policy.get("decision_outputs", {})
    if safety_violations:
        decision = outputs.get("any_dangerous_flag_true", "ABORT")
        status = "ABORT"
    elif missing_evidence:
        decision = outputs.get("any_missing_evidence", "FREEZE_MAINTAINED")
        status = "FREEZE_MAINTAINED"
    elif has_reject:
        decision = outputs.get("any_fail_or_abort", "FREEZE_MAINTAINED")
        status = "FREEZE_MAINTAINED"
    else:
        decision = outputs.get("all_pass_but_unlock_not_allowed", "LIVE_CANDIDATE_BUT_LOCKED")
        status = decision

    all_prerequisite_phases_pass = bool(
        evidence_summary and all(item.get("exists") and item.get("status") in acceptable for item in evidence_summary)
    )

    return {
        "phase": "Phase 7-5",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "live_is_execution_permission": bool(policy.get("live_is_execution_permission", False)),
        "decision": decision,
        "phase7_5_decision": decision,
        "all_prerequisite_phases_pass": all_prerequisite_phases_pass,
        "live_execution_allowed": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "evidence_summary": evidence_summary,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 7-6 human approval evidence package design only"),
        "blocked_next_steps": policy.get("blocked_next_steps", []),
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "publish_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "generated_at": _now_iso(),
    }


def build_md(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-5 Freeze-or-Live Decision Report",
        "",
        "## Purpose",
        "- Aggregate Phase 7-1 to 7-4 evidence and decide whether to keep freeze or mark live candidate while still locked.",
        "",
        "## Evidence Summary",
    ]
    for item in report.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Decision",
            f"- status: {report.get('status')}",
            f"- decision: {report.get('decision')}",
            f"- live_is_execution_permission: {report.get('live_is_execution_permission')}",
            "",
            "## Safety Flags",
            f"- production_status: {report.get('production_status')}",
            f"- wordpress_draft_creation: {report.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {report.get('wordpress_write_executed')}",
            f"- approve_draft_create_only_currently_allowed: {report.get('approve_draft_create_only_currently_allowed')}",
            f"- unlock_in_this_phase: {report.get('unlock_in_this_phase')}",
            f"- publish_allowed: {report.get('publish_allowed')}",
            "",
            "## Blocked Operations",
        ]
    )
    for item in report.get("blocked_next_steps", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Final Judgment",
            f"- {report.get('decision')}",
            "",
            "## Next Step",
            f"- {report.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def run_report(
    logs_dir: Path | None = None,
    output_json: Path | None = None,
    output_md: Path | None = None,
    policy_path: Path | None = None,
) -> dict:
    report = build_report(logs_dir, policy_path)
    out_json = Path(output_json) if output_json else OUTPUT_JSON
    out_md = Path(output_md) if output_md else OUTPUT_MD
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(build_md(report), encoding="utf-8")
    return report


def main() -> int:
    report = run_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") in {"LIVE_CANDIDATE_BUT_LOCKED", "FREEZE_MAINTAINED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
