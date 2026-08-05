#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_17_env_credential_presence_smoke_check_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_17_env_credential_presence_smoke_check_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_17_env_credential_presence_smoke_check_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_env_credential_presence_smoke_check(
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
        result = _build_result(
            "ABORT",
            credentials,
            errors,
            warnings,
            safety_violations,
            {},
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("env_check_is_execution_permission") is not False:
        safety_violations.append("env_check_is_execution_permission must be false")
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
    for op_name, op_value in dangerous_ops.items():
        if op_value is not False:
            safety_violations.append(f"dangerous_operations.{op_name} must be false")

    root = _resolve_root(policy_path)
    allowed_phase8_16_statuses = set(policy.get("allowed_phase8_16_statuses", []))
    phase8_16_status = None

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        phase8_16_status = payload.get("status") or payload.get("overall_status")

    if phase8_16_status is not None and phase8_16_status not in allowed_phase8_16_statuses:
        safety_violations.append(f"phase8_16 status {phase8_16_status!r} is not allowed")

    if safety_violations:
        result = _build_result(
            "ABORT",
            credentials,
            errors,
            warnings,
            safety_violations,
            policy,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    all_present = True
    for key in policy.get("required_env", []):
        exists = bool(os.environ.get(key, ""))
        credentials[key] = {"exists": exists}
        if not exists:
            all_present = False

    status = (
        "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT"
        if all_present
        else "ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT"
    )
    result = _build_result(
        status,
        credentials,
        errors,
        warnings,
        safety_violations,
        policy,
    )
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
        "phase": "Phase 8-17",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "env_check_is_execution_permission": False,
        "credentials": credentials,
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-18 post-credential rerun readiness transition report",
        ),
        "checked_at": _now_iso(),
    }


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-17 Environment Credential Presence Smoke Check Report",
        "",
        "## Purpose",
        "Check only environment credential existence after Phase 8-16.",
        "",
        "## Prior Evidence",
        "- Phase 8-16 operator confirmation result is required.",
        "",
        "## Credential Existence Summary",
    ]
    for key, value in result.get("credentials", {}).items():
        lines.append(f"- {key}: exists={value.get('exists')}")

    lines.extend(
        [
            "",
            "## Secret Output Policy",
            "- only exists boolean is allowed.",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- env_check_is_execution_permission: {result.get('env_check_is_execution_permission')}",
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


def main() -> int:
    result = validate_env_credential_presence_smoke_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT",
        "ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())