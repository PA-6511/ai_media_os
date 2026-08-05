#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_37_credential_ready_revalidation_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_37_credential_ready_revalidation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_37_credential_ready_revalidation_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_credential_ready_revalidation(
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
    credentials: dict[str, dict[str, bool]] = {}

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", credentials, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)
    for flag in [
        "revalidation_is_execution_permission",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"{flag} must be false")

    sop = policy.get("secret_output_policy", {})
    for key in ["print_values", "write_values_to_logs", "print_lengths", "print_prefix_suffix", "hash_values", "mask_values"]:
        if sop.get(key) is not False:
            safety_violations.append(f"secret_output_policy.{key} must be false")
    if sop.get("allowed_output") != "exists_boolean_only":
        safety_violations.append("secret_output_policy.allowed_output must be 'exists_boolean_only'")

    root = _resolve_root(policy_path)
    overlay_status = None
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        overlay_status = status
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"evidence_terminal_status: {rel}={status}")

    if safety_violations:
        status = "ABORT"
    elif overlay_status == policy.get("ready_overlay_status"):
        all_present = True
        for name in policy.get("required_env", []):
            exists = bool(os.environ.get(name, ""))
            credentials[name] = {"exists": exists}
            if not exists:
                all_present = False
        if all_present:
            status = "CREDENTIAL_READY_REVALIDATED_NO_SECRET_OUTPUT"
        else:
            status = "CREDENTIAL_READY_REVALIDATION_MISSING_NO_SECRET_OUTPUT"
    elif overlay_status == policy.get("not_ready_overlay_status"):
        for name in policy.get("required_env", []):
            credentials[name] = {"exists": bool(os.environ.get(name, ""))}
        status = "CREDENTIAL_READY_REVALIDATION_NOT_READY_BY_DECLARATION"
    else:
        status = "ABORT"

    result = _build_result(status, credentials, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    credentials: dict[str, dict[str, bool]],
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-37",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "revalidation_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "credentials": credentials,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-38 final one-time rerun authorization checkpoint"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-37 Credential-Ready Revalidation Report",
        "",
        "## Purpose",
        "Revalidate credential readiness via existence checks only.",
        "",
        "## Overlay Rerun Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend([
        "",
        "## Credential Existence Summary",
    ])
    for name, info in result.get("credentials", {}).items():
        lines.append(f"- {name}: exists={info.get('exists')}")
    lines.extend([
        "",
        "## Secret Output Policy",
        "- only exists=true/false outputs are allowed.",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- revalidation_is_execution_permission: {result.get('revalidation_is_execution_permission')}",
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
    result = validate_credential_ready_revalidation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "CREDENTIAL_READY_REVALIDATED_NO_SECRET_OUTPUT",
        "CREDENTIAL_READY_REVALIDATION_MISSING_NO_SECRET_OUTPUT",
        "CREDENTIAL_READY_REVALIDATION_NOT_READY_BY_DECLARATION",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
