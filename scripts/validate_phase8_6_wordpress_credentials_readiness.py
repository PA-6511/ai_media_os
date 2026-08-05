#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_6_wordpress_credentials_readiness_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_6_wordpress_credentials_readiness_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_6_wordpress_credentials_readiness_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_credentials_readiness(
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

    policy = _load_json(policy_path) if policy_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")

    if policy.get("credential_check_is_execution_permission") is not False:
        safety_violations.append("credential_check_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    sop = policy.get("secret_output_policy", {})
    for key in ["print_values", "write_values_to_logs", "print_lengths", "print_prefix_suffix", "hash_values"]:
        if sop.get(key) is not False:
            safety_violations.append(f"secret_output_policy.{key} must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    phase85_status = None
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        st = payload.get("status") or payload.get("overall_status")
        phase85_status = st
        evidence_summary.append({"path": rel, "exists": True, "status": st})

    if missing_evidence:
        safety_violations.append("required evidence missing")
    elif phase85_status != policy.get("required_phase8_5_status"):
        safety_violations.append(
            f"phase8_5 status must be {policy.get('required_phase8_5_status')} but got {phase85_status}"
        )

    if safety_violations:
        credentials_info: dict[str, dict[str, bool]] = {
            k: {"exists": False} for k in policy.get("required_env", [])
        }
        status = "ABORT"
    else:
        credentials_info = {}
        all_present = True
        for key in policy.get("required_env", []):
            val = os.getenv(key, "")
            exists = bool(str(val).strip())
            credentials_info[key] = {"exists": exists}
            if not exists:
                all_present = False
        status = (
            "CREDENTIALS_READY_NO_SECRET_OUTPUT"
            if all_present
            else "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
        )
        if not all_present:
            missing_keys = [k for k, v in credentials_info.items() if not v["exists"]]
            warnings.append(f"missing credentials: {', '.join(missing_keys)}")

    result = {
        "phase": "Phase 8-6",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "credential_check_is_execution_permission": False,
        "credentials": credentials_info,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-7 rerun approval preservation review",
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
        "# Phase 8-6 WordPress Credentials Readiness Report",
        "",
        "## Purpose",
        "- Check existence of WordPress credentials only. Values are never output.",
        "",
        "## Prior Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(["", "## Credential Existence Summary"])
    for key, info in result.get("credentials", {}).items():
        lines.append(f"- {key}: exists={info.get('exists')}")

    lines.extend(
        [
            "",
            "## Secret Output Policy",
            "- print_values: false",
            "- write_values_to_logs: false",
            "- print_lengths: false",
            "- print_prefix_suffix: false",
            "- hash_values: false",
            "- secret_values_written: false",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- credential_check_is_execution_permission: {result.get('credential_check_is_execution_permission')}",
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
    result = validate_credentials_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "CREDENTIALS_READY_NO_SECRET_OUTPUT",
        "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
