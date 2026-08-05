#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_40_post_rerun_branch_decision_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_40_post_rerun_branch_decision.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_40_post_rerun_branch_decision.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_post_rerun_branch_decision(
    policy_path: Path = DEFAULT_POLICY,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    evidence_summary: list[dict[str, Any]] = []
    rerun_evidence_status = None

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", rerun_evidence_status, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)
    for flag in [
        "branch_decision_is_execution_permission",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"{flag} must be false")

    root = _resolve_root(policy_path)
    command_bundle_status = None
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        command_bundle_status = status
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"evidence_terminal_status: {rel}={status}")

    for rel in policy.get("optional_rerun_evidence", []):
        ev_path = root / rel
        if ev_path.exists():
            payload = _load_json(ev_path)
            rerun_evidence_status = payload.get("status") or payload.get("overall_status")
            evidence_summary.append({"path": rel, "exists": True, "status": rerun_evidence_status})
            if payload.get("secret_values_written") is True:
                safety_violations.append(f"secret_values_written=true in {rel}")
        else:
            evidence_summary.append({"path": rel, "exists": False, "status": None})

    if missing_evidence:
        status = "BRANCH_NOT_READY"
    elif safety_violations:
        status = "ABORT"
    elif command_bundle_status == policy.get("blocked_command_bundle_status"):
        status = "BRANCH_BLOCKED_CREDENTIALS_MISSING"
    elif command_bundle_status == policy.get("ready_command_bundle_status"):
        if rerun_evidence_status is None:
            status = "BRANCH_READY_FOR_MANUAL_RERUN_BUT_NOT_EXECUTED"
        elif rerun_evidence_status == policy.get("phase8_10_success_status"):
            status = "BRANCH_TO_PHASE8_41_MANUAL_DRAFT_INSPECTION"
        elif rerun_evidence_status == policy.get("phase8_10_not_executed_status"):
            status = "BRANCH_RERUN_NOT_EXECUTED_CONFIRMED"
        elif rerun_evidence_status == policy.get("phase8_10_freeze_status"):
            status = "BRANCH_FREEZE_REQUIRED"
        else:
            status = "BRANCH_READY_FOR_MANUAL_RERUN_BUT_NOT_EXECUTED"
            warnings.append(f"unexpected_optional_rerun_status: {rerun_evidence_status}")
    else:
        status = "BRANCH_NOT_READY"

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, rerun_evidence_status, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    rerun_evidence_status: str | None,
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    if status == "BRANCH_READY_FOR_MANUAL_RERUN_BUT_NOT_EXECUTED":
        allowed_next_step = policy.get("allowed_next_step_if_ready_not_executed", "")
    elif status == "BRANCH_TO_PHASE8_41_MANUAL_DRAFT_INSPECTION":
        allowed_next_step = policy.get("allowed_next_step_if_draft_created", "")
    elif status == "BRANCH_RERUN_NOT_EXECUTED_CONFIRMED":
        allowed_next_step = policy.get("allowed_next_step_if_not_executed", "")
    elif status == "BRANCH_FREEZE_REQUIRED":
        allowed_next_step = policy.get("allowed_next_step_if_freeze", "")
    else:
        allowed_next_step = policy.get("allowed_next_step_if_not_executed", "")

    return {
        "phase": "Phase 8-40",
        "status": status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "execution_allowed": False,
        "actual_go_decision_issued": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "secret_values_output": False,
        "branch_decision_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "rerun_evidence_status": rerun_evidence_status,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": allowed_next_step,
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-40 Post-Rerun Branch Decision Report",
        "",
        "## Purpose",
        "Provide branch decision before/after rerun evidence without execution.",
        "",
        "## Command Bundle Evidence",
    ]
    for item in result.get("evidence_summary", []):
        if "phase8_39" in item.get("path", ""):
            lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend([
        "",
        "## Optional Rerun Evidence",
    ])
    for item in result.get("evidence_summary", []):
        if "phase8_10" in item.get("path", ""):
            lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend([
        "",
        "## Branch Decision",
        f"- status: {result.get('status')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- branch_decision_is_execution_permission: {result.get('branch_decision_is_execution_permission')}",
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
    result = generate_post_rerun_branch_decision()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "BRANCH_READY_FOR_MANUAL_RERUN_BUT_NOT_EXECUTED",
        "BRANCH_BLOCKED_CREDENTIALS_MISSING",
        "BRANCH_TO_PHASE8_41_MANUAL_DRAFT_INSPECTION",
        "BRANCH_RERUN_NOT_EXECUTED_CONFIRMED",
        "BRANCH_FREEZE_REQUIRED",
        "BRANCH_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())