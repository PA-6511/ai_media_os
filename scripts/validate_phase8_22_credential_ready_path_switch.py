#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_22_credential_ready_path_switch_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_22_credential_ready_path_switch_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_22_credential_ready_path_switch_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_credential_ready_path_switch(
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
    credentials: dict[str, dict[str, bool]] = {}

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", credentials, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("path_switch_is_execution_permission") is not False:
        safety_violations.append("path_switch_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    sop = policy.get("secret_output_policy", {})
    for key in [
        "print_values",
        "write_values_to_logs",
        "print_lengths",
        "print_prefix_suffix",
        "hash_values",
        "mask_values",
    ]:
        if sop.get(key) is not False:
            safety_violations.append(f"secret_output_policy.{key} must be false")

    dangerous_ops = policy.get("dangerous_operations", {})
    for name, value in dangerous_ops.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{name} must be false")

    root = _resolve_root(policy_path)
    required_status = policy.get("required_phase8_21_status", "PASS_CHECKLIST_ONLY")

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        if status != required_status:
            safety_violations.append(f"phase8_21 status must be {required_status!r} but got {status!r}")

    if safety_violations:
        result = _build_result("ABORT", credentials, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    all_present = True
    for name in policy.get("required_env", []):
        exists = bool(os.environ.get(name, ""))
        credentials[name] = {"exists": exists}
        if not exists:
            all_present = False

    status = (
        "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT"
        if all_present
        else "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS"
    )

    result = _build_result(status, credentials, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    credentials: dict[str, dict[str, bool]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-22",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "path_switch_is_execution_permission": False,
        "credentials": credentials,
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-23 pre-rerun immutable safety snapshot"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-22 Credential-Ready Path Switch Validation Report",
        "",
        "## Purpose",
        "Validate whether path switch to credential-ready route is possible without execution.",
        "",
        "## Prior Evidence",
        "- Phase 8-21 result must be PASS_CHECKLIST_ONLY.",
        "",
        "## Credential Existence Summary",
    ]
    for name, info in result.get("credentials", {}).items():
        lines.append(f"- {name}: exists={info.get('exists')}")

    lines.extend(
        [
            "",
            "## Secret Output Policy",
            "- only exists=true/false is allowed in outputs.",
            "",
            "## Path Switch Decision",
            f"- status: {result.get('status')}",
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- path_switch_is_execution_permission: {result.get('path_switch_is_execution_permission')}",
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
    result = validate_credential_ready_path_switch()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT",
        "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
