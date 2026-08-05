#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_13_post_credential_readiness_recheck_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_13_post_credential_readiness_recheck_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_13_post_credential_readiness_recheck_result.md"

# Required evidence relative paths → corresponding status key in required_statuses
_EVIDENCE_KEY_MAP = {
    "phase8_11": "phase8_11",
    "phase8_12": "phase8_12",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_post_credential_readiness_recheck(
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
    credentials: dict[str, dict[str, Any]] = {}

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        status = "ABORT"
        result = _build_result(status, credentials, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    # Safety flags check
    sop = policy.get("secret_output_policy", {})
    if sop.get("print_values") is not False:
        safety_violations.append("secret_output_policy.print_values must be false")
    if sop.get("write_values_to_logs") is not False:
        safety_violations.append("secret_output_policy.write_values_to_logs must be false")
    if sop.get("print_lengths") is not False:
        safety_violations.append("secret_output_policy.print_lengths must be false")
    if sop.get("print_prefix_suffix") is not False:
        safety_violations.append("secret_output_policy.print_prefix_suffix must be false")
    if sop.get("hash_values") is not False:
        safety_violations.append("secret_output_policy.hash_values must be false")
    if policy.get("recheck_is_execution_permission") is not False:
        safety_violations.append("recheck_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, credentials, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    root = _resolve_root(policy_path)

    # Evidence check
    required_statuses = policy.get("required_statuses", {})
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        actual_status = payload.get("status") or payload.get("overall_status")
        # Determine which phase key this evidence corresponds to
        for key_fragment, req_key in _EVIDENCE_KEY_MAP.items():
            if key_fragment in rel:
                expected = required_statuses.get(req_key)
                if expected is not None and actual_status != expected:
                    safety_violations.append(
                        f"{req_key} status must be {expected!r} but got {actual_status!r}"
                    )
                break

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, credentials, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Credential existence check (never read values)
    required_env = policy.get("required_env", [])
    all_present = True
    for var in required_env:
        exists = bool(os.environ.get(var, ""))
        credentials[var] = {"exists": exists}
        if not exists:
            all_present = False

    if all_present:
        status = "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT"
    else:
        status = "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"

    result = _build_result(status, credentials, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    credentials: dict,
    errors: list,
    warnings: list,
    safety_violations: list,
    policy: dict,
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-13",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "recheck_is_execution_permission": False,
        "credentials": credentials,
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-14 explicit rerun authorization renewal after credentials ready",
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
        "# Phase 8-13 Post-Credential Readiness Recheck Report",
        "",
        "## Purpose",
        "Verify that WordPress credentials are present in the execution environment.",
        "Outputs only exists=true/false. No values, lengths, prefixes, or hashes.",
        "",
        "## Credential Existence",
    ]
    for var, info in result.get("credentials", {}).items():
        lines.append(f"- {var}: exists={info.get('exists')}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- recheck_is_execution_permission: {result.get('recheck_is_execution_permission')}",
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
    result = validate_post_credential_readiness_recheck()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
        "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
