#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_34_one_time_manual_rerun_lock_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_34_one_time_manual_rerun_lock.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_34_one_time_manual_rerun_lock.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_one_time_manual_rerun_lock(
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
    manual_rerun_lock: dict[str, Any] = {}

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", manual_rerun_lock, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)
    for flag in [
        "lock_is_execution_permission",
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
    env_status = None
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
        env_status = status
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"evidence_terminal_status: {rel}={status}")

    if missing_evidence:
        status = "ONE_TIME_RERUN_LOCK_NOT_READY"
    elif safety_violations:
        status = "ABORT"
    elif env_status == policy.get("ready_env_status"):
        status = "ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED"
    elif env_status in set(policy.get("not_ready_statuses", [])):
        status = "ONE_TIME_RERUN_LOCK_BLOCKED_CREDENTIALS_MISSING"
    else:
        status = "ONE_TIME_RERUN_LOCK_NOT_READY"

    manual_rerun_lock = _build_lock_fields(policy)

    forbidden_fields = [f.lower() for f in policy.get("forbidden_lock_fields", [])]
    for field in policy.get("non_secret_lock_fields", []):
        field_lower = field.lower()
        for forbidden in forbidden_fields:
            if forbidden in field_lower:
                safety_violations.append(f"forbidden_non_secret_lock_field_configured: {field}")

    for key in manual_rerun_lock.keys():
        key_lower = key.lower()
        for forbidden in forbidden_fields:
            if forbidden in key_lower:
                safety_violations.append(f"forbidden_lock_field_detected: {key}")

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, manual_rerun_lock, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_lock_fields(policy: dict[str, Any]) -> dict[str, Any]:
    values = {
        "phase": "Phase 8-34",
        "target_item_count": policy.get("target_item_count", 1),
        "max_manual_rerun_count": policy.get("max_manual_rerun_count", 1),
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
    }
    result = {}
    for field in policy.get("non_secret_lock_fields", []):
        if field in values:
            result[field] = values[field]
    return result


def _build_result(
    status: str,
    manual_rerun_lock: dict[str, Any],
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-34",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "lock_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "max_manual_rerun_count": policy.get("max_manual_rerun_count", 1),
        "manual_rerun_lock": manual_rerun_lock,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-35 final READY/BLOCKED decision before manually rerunning existing Phase 8-6 to Phase 8-10"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-34 One-Time Manual Rerun Lock Package",
        "",
        "## Purpose",
        "Generate one-time non-secret lock package for manual rerun boundary with no execution.",
        "",
        "## Environment Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend([
        "",
        "## Lock Decision",
        f"- status: {result.get('status')}",
        "",
        "## Non-Secret Lock Fields",
    ])
    for key, value in result.get("manual_rerun_lock", {}).items():
        lines.append(f"- {key}: {value}")
    if not result.get("manual_rerun_lock"):
        lines.append("- none")

    lines.extend([
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- lock_is_execution_permission: {result.get('lock_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- phase8_6_to_8_10_executed: {result.get('phase8_6_to_8_10_executed')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
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
    result = generate_one_time_manual_rerun_lock()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
        "ONE_TIME_RERUN_LOCK_BLOCKED_CREDENTIALS_MISSING",
        "ONE_TIME_RERUN_LOCK_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
