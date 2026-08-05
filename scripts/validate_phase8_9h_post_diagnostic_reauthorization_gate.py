#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_9h_post_diagnostic_reauthorization_gate_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_9h_post_diagnostic_reauthorization_gate_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_9h_post_diagnostic_reauthorization_gate_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _contains_sensitive_marker(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _scan_payload(value: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _scan_payload(item, markers, findings, f"{path}.{key}")
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_payload(item, markers, findings, f"{path}[{idx}]")
        return
    if isinstance(value, str) and _contains_sensitive_marker(value, markers):
        findings.append(f"forbidden_output_marker:{path}")


def validate_phase8_9h_post_diagnostic_reauthorization_gate(
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

    if not policy_path.exists() or not request_path.exists():
        result = _build_result(
            "ABORT_POLICY_VIOLATION",
            {},
            errors,
            warnings,
            ["missing_required_file"],
            secret_leak_findings,
            {},
        )
        _write_output(output_json_path, result)
        return result

    policy = _load_json(policy_path)
    request = _load_json(request_path)
    root = _resolve_root(policy_path)

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    for flag in [
        "execution_allowed",
        "wordpress_api_call_allowed",
        "wordpress_api_call_attempted",
        "wordpress_write_allowed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "unlock_in_this_phase",
    ]:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("design_only") is not True:
        policy_violations.append("request.design_only must be true")
    if request.get("retry_consumed") is not True:
        policy_violations.append("request.retry_consumed must be true")
    if request.get("retry_allowed") is not False:
        policy_violations.append("request.retry_allowed must be false")
    if int(request.get("retry_limit", -1)) != 0:
        policy_violations.append("request.retry_limit must be 0")
    if request.get("freeze_required") is not True:
        policy_violations.append("request.freeze_required must be true")
    if request.get("secret_values_included") is not False:
        policy_violations.append("request.secret_values_included must be false")

    diagnostic_reauth_conditions = request.get("diagnostic_reauth_conditions", {})
    for key in [
        "phase8_9g_completed",
        "wordpress_root_cause_checklist_completed",
        "credential_env_reinjected",
        "phase8_16_ready_maintained",
        "phase8_17_ready_maintained",
        "freeze_maintained",
        "no_go_maintained",
    ]:
        if diagnostic_reauth_conditions.get(key) is not True:
            policy_violations.append(f"request.diagnostic_reauth_conditions.{key} must be true")

    operator_confirmations = request.get("operator_confirmations", {})
    for key in [
        "base_url_public_site",
        "username_is_login_username",
        "user_role_editor_or_higher",
        "application_password_regenerated",
        "wp_json_reachable",
        "security_or_waf_not_restricting",
    ]:
        if operator_confirmations.get(key) is not True:
            policy_violations.append(f"request.operator_confirmations.{key} must be true")

    decision = str(request.get("decision", "")).strip()
    if decision not in set(request.get("allowed_decisions", [])):
        policy_violations.append("request decision is outside allowed_decisions")

    previous_paths = policy.get("required_previous_evidence", [])
    previous_statuses: dict[str, str | None] = {}
    retry_consumed = True
    for rel in previous_paths:
        path = root / rel
        if not path.exists():
            previous_statuses[rel] = None
            policy_violations.append(f"missing_previous_evidence: {rel}")
            retry_consumed = False
            continue
        payload = _load_json(path)
        actual_status = payload.get("status") or payload.get("overall_status") or payload.get("final_status")
        previous_statuses[rel] = actual_status
        expected_status = policy.get("required_previous_statuses", {}).get(rel)
        if expected_status and actual_status != expected_status:
            policy_violations.append(f"{rel} status must be {expected_status}")

        if rel.endswith("phase8_9_first_one_item_wordpress_draft_create_rerun_result.json"):
            if payload.get("freeze_required") is not True:
                policy_violations.append("phase8_9.freeze_required must be true")
            if payload.get("wordpress_api_call_attempted") is not True:
                policy_violations.append("phase8_9.wordpress_api_call_attempted must be true")
            if payload.get("wordpress_write_executed") is not False:
                policy_violations.append("phase8_9.wordpress_write_executed must be false")

        if rel.endswith("phase8_9f_401_freeze_closure_diagnostic_plan_result.json"):
            if payload.get("retry_allowed") is not False:
                policy_violations.append("phase8_9F.retry_allowed must be false")
            if payload.get("freeze_required") is not True:
                policy_violations.append("phase8_9F.freeze_required must be true")

        if rel.endswith("phase8_9g_wordpress_401_root_cause_operator_checklist_result.json"):
            if payload.get("retry_allowed") is not False:
                policy_violations.append("phase8_9G.retry_allowed must be false")
            if payload.get("freeze_required") is not True:
                policy_violations.append("phase8_9G.freeze_required must be true")

        if rel.endswith("phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"):
            if payload.get("credentials_ready") is not True:
                policy_violations.append("phase8_16.credentials_ready must be true")
            if payload.get("no_secret_leak_passed") is not True:
                policy_violations.append("phase8_16.no_secret_leak_passed must be true")

        if rel.endswith("phase8_17_env_credential_presence_smoke_check_result.json"):
            credentials = payload.get("credentials", {})
            for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
                if credentials.get(key, {}).get("exists") is not True:
                    policy_violations.append(f"phase8_17.credentials.{key}.exists must be true")

    if policy.get("required_previous_retry_limit_consumed") is True and retry_consumed is False:
        policy_violations.append("retry_limit must already be consumed")

    markers = list(policy.get("no_secret_leak_detection", {}).get("forbidden_markers", []))
    _scan_payload(request, markers, secret_leak_findings)

    result = _build_result(
        final_status="POST_DIAGNOSTIC_REAUTHORIZATION_GATE_READY_NO_EXECUTION",
        previous_statuses=previous_statuses,
        errors=errors,
        warnings=warnings,
        policy_violations=policy_violations,
        secret_leak_findings=secret_leak_findings,
        extra={
            "retry_consumed": True,
            "retry_allowed": False,
            "retry_limit": 0,
            "freeze_required": True,
            "wordpress_api_call_allowed": False,
            "wordpress_api_call_attempted": False,
            "wordpress_write_allowed": False,
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
            "executor_action_allowed": False,
            "secret_values_output": False,
            "secret_values_written": False,
            "secret_values_logged": False,
            "human_approval_valid": decision == "APPROVE_POST_DIAGNOSTIC_REAUTH_GATE_ONLY",
            "human_decision": decision,
            "diagnostic_reauth_conditions": diagnostic_reauth_conditions,
            "operator_confirmations": operator_confirmations,
            "next_step": policy.get("allowed_next_step_if_ready", "phase8_9h_human_reauthorization_review_only"),
        },
    )

    if policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["next_step"] = "manual_freeze_investigation_without_execution"
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["next_step"] = "manual_freeze_investigation_without_execution"
    elif decision == "REQUEST_FIX":
        result["final_status"] = "REQUEST_FIX_NO_EXECUTION"
        result["next_step"] = "manual_freeze_investigation_without_execution"
    elif decision == "REJECT":
        result["final_status"] = "REJECTED_NO_EXECUTION"
        result["next_step"] = "stop_without_execution"
    elif decision == "ABORT":
        result["final_status"] = "ABORTED_NO_EXECUTION"
        result["next_step"] = "stop_without_execution"

    _write_output(output_json_path, result)
    return result


def _build_result(
    final_status: str,
    previous_statuses: dict[str, str | None],
    errors: list[str],
    warnings: list[str],
    policy_violations: list[str],
    secret_leak_findings: list[str],
    extra: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "phase": "8-9H",
        "phase_name": "post diagnostic reauthorization gate",
        "phase_status": "DESIGN_ONLY_NO_EXECUTION",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "design_only": True,
        "retry_consumed": True,
        "retry_allowed": False,
        "retry_limit": 0,
        "freeze_required": True,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
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
        "executor_action_allowed": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "previous_statuses": previous_statuses,
        "errors": errors,
        "warnings": warnings,
        "policy_violations": policy_violations,
        "secret_leak_findings": secret_leak_findings,
        "checked_at": _now_iso(),
        "final_status": final_status,
    }
    result.update(extra)
    return result


def _write_output(output_json_path: Path, result: dict[str, Any]) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    result = validate_phase8_9h_post_diagnostic_reauthorization_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "POST_DIAGNOSTIC_REAUTHORIZATION_GATE_READY_NO_EXECUTION",
        "REQUEST_FIX_NO_EXECUTION",
        "REJECTED_NO_EXECUTION",
        "ABORTED_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
