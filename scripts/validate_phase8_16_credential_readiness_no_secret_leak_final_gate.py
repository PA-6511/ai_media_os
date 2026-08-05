#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_16_credential_readiness_no_secret_leak_final_gate_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_16_credential_readiness_no_secret_leak_final_gate_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _credential_state(env_key: str) -> dict[str, Any]:
    is_present = env_key in os.environ
    raw_value = os.environ.get(env_key, "")
    is_non_empty = bool(str(raw_value).strip()) if is_present else False
    if not is_present:
        status = "MISSING"
    elif not is_non_empty:
        status = "EMPTY"
    else:
        status = "READY"
    return {
        "credential_key": env_key,
        "present": is_present,
        "non_empty": is_non_empty,
        "status": status,
    }


def _has_forbidden_term(text: str, forbidden_terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in forbidden_terms)


def _looks_sensitive_header_or_assignment(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "authorization:",
        "bearer ",
        "basic ",
        "cookie:",
        "password=",
        "token=",
        "webhook=",
        "client_secret=",
        "api_key=",
    ]
    return any(marker in lowered for marker in markers)


def _scan_payload_forbidden_terms(
    value: Any,
    forbidden_terms: list[str],
    allowed_key_names: set[str],
    leaks: list[str],
    path: str = "root",
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            _scan_payload_forbidden_terms(item, forbidden_terms, allowed_key_names, leaks, key_path)
        return

    if isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_payload_forbidden_terms(item, forbidden_terms, allowed_key_names, leaks, f"{path}[{idx}]")
        return

    if isinstance(value, str):
        # Env key names are permitted only under credential_key field.
        if path.endswith(".credential_key") and value.isupper() and "_" in value:
            return
        if _looks_sensitive_header_or_assignment(value):
            leaks.append(f"forbidden_value:{path}")
            return
        # Keep a light lexical check for explicit secret-bearing free-form values,
        # but avoid flagging standard metadata such as final_status labels.
        if (
            path.startswith("root.errors")
            or path.startswith("root.warnings")
            or path.startswith("root.secret_leak_findings")
        ) and _has_forbidden_term(value, forbidden_terms):
            leaks.append(f"forbidden_value:{path}")


def _scan_for_secret_values(text: str, secret_values: list[str]) -> bool:
    for secret_value in secret_values:
        if secret_value and secret_value in text:
            return True
    return False


def validate_phase8_16_credential_readiness_no_secret_leak_final_gate(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)

    errors: list[str] = []
    warnings: list[str] = []
    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    if not policy_path.exists():
        result = {
            "phase": "8-16",
            "phase_name": "Credential readiness / no-secret-leak final gate",
            "final_status": "ABORT_POLICY_VIOLATION",
            "errors": ["missing_policy"],
            "warnings": [],
            "policy_violations": ["missing_policy_file"],
            "secret_leak_findings": [],
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    if not request_path.exists():
        result = {
            "phase": "8-16",
            "phase_name": "Credential readiness / no-secret-leak final gate",
            "final_status": "ABORT_POLICY_VIOLATION",
            "errors": ["missing_request"],
            "warnings": [],
            "policy_violations": ["missing_request_file"],
            "secret_leak_findings": [],
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    policy = _load_json(policy_path)
    request = _load_json(request_path)

    required_false_flags = policy.get("required_false_flags", [])
    for flag in required_false_flags:
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    request_false_flags = [
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
    ]
    for flag in request_false_flags:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("credential_check_only") is not True:
        policy_violations.append("request.credential_check_only must be true")
    if request.get("no_secret_leak_required") is not True:
        policy_violations.append("request.no_secret_leak_required must be true")

    credentials = [_credential_state(key) for key in policy.get("required_env", [])]
    missing_credential_keys = [
        item["credential_key"] for item in credentials if item["status"] in {"MISSING", "EMPTY"}
    ]
    all_ready = all(item["status"] == "READY" for item in credentials)

    no_secret_policy = policy.get("no_secret_leak_detection", {})
    forbidden_terms = list(no_secret_policy.get("forbidden_terms", []))
    allowed_key_names = {k.lower() for k in no_secret_policy.get("allowed_key_names", [])}

    result: dict[str, Any] = {
        "phase": "8-16",
        "phase_name": policy.get("phase_name", "Credential readiness / no-secret-leak final gate"),
        "phase_status": policy.get("phase_status", "FINAL_GATE_DRY_RUN_ONLY"),
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "mode": request.get("mode", "CREDENTIAL_READINESS_FINAL_GATE"),
        "human_approval_required": bool(request.get("human_approval_required", True)),
        "target_item_count": int(request.get("target_item_count", 1)),
        "credential_check_only": True,
        "no_secret_leak_required": True,
        "credentials": credentials,
        "missing_credential_keys": missing_credential_keys,
        "credentials_ready": all_ready,
        "no_secret_leak_passed": True,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_action_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "executor_action_allowed": False,
        "wordpress_api_call_not_executed": True,
        "wordpress_write_not_executed": True,
        "draft_creation_not_executed": True,
        "errors": errors,
        "warnings": warnings,
        "policy_violations": policy_violations,
        "secret_leak_findings": secret_leak_findings,
        "checked_at": _now_iso(),
    }

    _scan_payload_forbidden_terms(
        result,
        forbidden_terms,
        allowed_key_names,
        secret_leak_findings,
    )

    required_env_values = [os.environ.get(k, "") for k in policy.get("required_env", []) if os.environ.get(k, "")]
    serialized_result = json.dumps(result, ensure_ascii=False)
    if _scan_for_secret_values(serialized_result, required_env_values):
        secret_leak_findings.append("secret_value_detected_in_result_payload")

    lowered_result = serialized_result.lower()
    direct_leak_markers = ["authorization:", "bearer ", "basic ", "cookie:"]
    if any(marker in lowered_result for marker in direct_leak_markers):
        secret_leak_findings.append("sensitive_header_like_output_detected")

    if policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["no_secret_leak_passed"] = False
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["no_secret_leak_passed"] = False
    elif all_ready:
        result["final_status"] = "CREDENTIALS_READY_NO_SECRET_LEAK_PASS"
    else:
        result["final_status"] = "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"

    if result["final_status"] == "CREDENTIALS_READY_NO_SECRET_LEAK_PASS":
        result["next_step"] = request.get(
            "next_step_if_pass",
            policy.get("allowed_next_step_if_ready", "phase8_17_or_manual_human_approval_before_single_draft_creation"),
        )
    else:
        result["next_step"] = request.get(
            "next_step_if_not_ready",
            policy.get("allowed_next_step_if_not_ready", "manual_credential_provisioning_or_env_fix_without_secret_output"),
        )

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate_phase8_16_credential_readiness_no_secret_leak_final_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
        "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
