#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_23_pre_rerun_safety_snapshot_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_23_pre_rerun_safety_snapshot.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_23_pre_rerun_safety_snapshot.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_pre_rerun_safety_snapshot(
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
    snapshot: dict[str, Any] = {}

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", snapshot, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("snapshot_is_execution_permission") is not False:
        safety_violations.append("snapshot_is_execution_permission must be false")
    if policy.get("commands_executed_in_this_phase") is not False:
        safety_violations.append("commands_executed_in_this_phase must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    required_flags = dict(policy.get("snapshot_required_flags", {}))
    for key, value in required_flags.items():
        if value not in (False, 0):
            safety_violations.append(f"snapshot_required_flags.{key} must be false")
    snapshot.update(required_flags)

    root = _resolve_root(policy_path)
    phase821 = None
    phase822 = None
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
        evidence_summary.append({"path": rel, "exists": True, "status": status})

        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"{rel} has terminal status: {status}")

        if "phase8_21" in rel:
            phase821 = status
        if "phase8_22" in rel:
            phase822 = status

    if missing_evidence:
        status = "SAFETY_SNAPSHOT_NOT_READY"
    elif safety_violations:
        status = "ABORT"
    else:
        required_phase821 = policy.get("required_phase8_21_status", "PASS_CHECKLIST_ONLY")
        if phase821 != required_phase821:
            safety_violations.append(f"phase8_21 status must be {required_phase821!r} but got {phase821!r}")
            status = "ABORT"
        elif phase822 == policy.get("ready_status"):
            status = "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED"
        elif phase822 == policy.get("not_ready_status"):
            status = "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING"
        else:
            status = "SAFETY_SNAPSHOT_NOT_READY"
            warnings.append(f"unexpected_phase8_22_status: {phase822}")

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, snapshot, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    snapshot: dict[str, Any],
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-23",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "snapshot_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": policy.get("target_item_count", 1),
        "secret_values_written": False,
        "snapshot": snapshot,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-24 operator GO/NO-GO decision for manual rerun sequence"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-23 Pre-Rerun Immutable Safety Snapshot",
        "",
        "## Purpose",
        "Capture immutable pre-rerun safety state without execution.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Credential Readiness",
            f"- status: {result.get('status')}",
            "",
            "## Immutable Safety Snapshot",
        ]
    )
    for key, value in result.get("snapshot", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- snapshot_is_execution_permission: {result.get('snapshot_is_execution_permission')}",
            f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
            f"- secret_values_written: {result.get('secret_values_written')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = generate_pre_rerun_safety_snapshot()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED",
        "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING",
        "SAFETY_SNAPSHOT_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
