#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_9r_401_retry_authorization_gate_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_9r_401_retry_authorization_gate_request.example.json"
DEFAULT_HUMAN_REVIEW = ROOT / "exchange/human_review/phase8_9r_401_retry_authorization_gate.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_9r_401_retry_authorization_gate_result.json"


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


def _scan_strings(value: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _scan_strings(item, markers, findings, f"{path}.{key}")
        return

    if isinstance(value, list):
        for idx, item in enumerate(value):
            _scan_strings(item, markers, findings, f"{path}[{idx}]")
        return

    if isinstance(value, str) and _contains_sensitive_marker(value, markers):
        findings.append(f"forbidden_output_marker:{path}")


def validate_phase8_9r_401_retry_authorization_gate(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    human_review_path: Path = DEFAULT_HUMAN_REVIEW,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    human_review_path = Path(human_review_path)
    output_json_path = Path(output_json_path)

    errors: list[str] = []
    warnings: list[str] = []
    policy_violations: list[str] = []
    secret_leak_findings: list[str] = []

    required_files = [
        ("policy", policy_path),
        ("request", request_path),
        ("human_review", human_review_path),
    ]
    missing_files = [name for name, path in required_files if not path.exists()]
    if missing_files:
        result = _build_result(
            final_status="ABORT_POLICY_VIOLATION",
            reason="missing_required_file",
            policy_violations=[f"missing_file:{name}" for name in missing_files],
            secret_leak_findings=[],
            errors=errors,
            warnings=warnings,
            extra={},
        )
        _write_output(output_json_path, result)
        return result

    policy = _load_json(policy_path)
    request = _load_json(request_path)
    human = _load_json(human_review_path)
    root = _resolve_root(policy_path)

    for flag in policy.get("required_false_flags", []):
        if policy.get(flag) is not False:
            policy_violations.append(f"policy.{flag} must be false")

    for flag in [
        "execution_allowed",
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "wordpress_draft_creation_allowed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
    ]:
        if request.get(flag) is not False:
            policy_violations.append(f"request.{flag} must be false")

    if request.get("execution") != "DRY_RUN":
        policy_violations.append("request.execution must be DRY_RUN")
    if request.get("production_status") != "NO_GO":
        policy_violations.append("request.production_status must be NO_GO")
    if request.get("retry_allowed") is not True:
        policy_violations.append("request.retry_allowed must be true")
    if int(request.get("retry_limit", 0)) != 1:
        policy_violations.append("request.retry_limit must be 1")
    if int(request.get("target_item_count", 0)) != 1:
        policy_violations.append("request.target_item_count must be 1")

    if request.get("base_url_is_public_site_url") is not True:
        policy_violations.append("request.base_url_is_public_site_url must be true")
    if request.get("username_is_login_username") is not True:
        policy_violations.append("request.username_is_login_username must be true")
    if request.get("app_password_is_wordpress_application_password") is not True:
        policy_violations.append("request.app_password_is_wordpress_application_password must be true")
    if request.get("user_has_editor_or_higher_role") is not True:
        policy_violations.append("request.user_has_editor_or_higher_role must be true")
    if request.get("rest_api_and_application_password_not_restricted") is not True:
        policy_violations.append("request.rest_api_and_application_password_not_restricted must be true")
    if request.get("secret_values_included") is not False:
        policy_violations.append("request.secret_values_included must be false")

    if human.get("human_approval_required") is not True:
        policy_violations.append("human.human_approval_required must be true")
    if human.get("human_approved") is not True:
        policy_violations.append("human.human_approved must be true")
    if human.get("retry_allowed") is not True:
        policy_violations.append("human.retry_allowed must be true")
    if int(human.get("retry_limit", 0)) != 1:
        policy_violations.append("human.retry_limit must be 1")
    if int(human.get("target_item_count", 0)) != 1:
        policy_violations.append("human.target_item_count must be 1")
    if human.get("secret_values_included") is not False:
        policy_violations.append("human.secret_values_included must be false")

    decision = str(human.get("decision", "")).strip()
    approval_scope = str(human.get("approval_scope", "")).strip()
    allowed_decisions = set(human.get("allowed_decisions", []))
    if decision not in allowed_decisions:
        policy_violations.append("human decision is outside allowed_decisions")
    if approval_scope != "NEXT_PHASE_SINGLE_DRAFT_CREATE_ONLY_NO_EXECUTION_IN_THIS_PHASE":
        policy_violations.append("human.approval_scope must be NEXT_PHASE_SINGLE_DRAFT_CREATE_ONLY_NO_EXECUTION_IN_THIS_PHASE")

    previous_evidence_path = root / policy.get("required_previous_evidence", [""])[0]
    previous_result: dict[str, Any] | None = None
    previous_status = None
    previous_401_confirmed = False
    previous_freeze_required = False
    previous_api_call_attempted = False
    previous_write_executed = False

    if not previous_evidence_path.exists():
        policy_violations.append(f"missing_previous_evidence: {previous_evidence_path.relative_to(root)}")
    else:
        previous_result = _load_json(previous_evidence_path)
        previous_status = previous_result.get("status")
        previous_freeze_required = previous_result.get("freeze_required") is True
        previous_api_call_attempted = previous_result.get("wordpress_api_call_attempted") is True
        previous_write_executed = previous_result.get("wordpress_write_executed") is True
        errors_list = previous_result.get("errors", [])
        previous_401_confirmed = any(
            isinstance(item, str) and policy.get("required_previous_error_snippet") in item
            for item in errors_list
        )

        if previous_status != policy.get("required_previous_status"):
            policy_violations.append(f"previous.status must be {policy.get('required_previous_status')}")
        if not previous_401_confirmed:
            policy_violations.append("previous errors must include the 401 snippet")
        if previous_result.get("production_status") != "LIMITED_DRAFT_CREATE_ONLY":
            policy_violations.append("previous.production_status must be LIMITED_DRAFT_CREATE_ONLY")
        if previous_freeze_required is not True:
            policy_violations.append("previous.freeze_required must be true")
        if previous_api_call_attempted is not True:
            policy_violations.append("previous.wordpress_api_call_attempted must be true")
        if previous_write_executed is not False:
            policy_violations.append("previous.wordpress_write_executed must be false")

    markers = list(policy.get("no_secret_leak_detection", {}).get("forbidden_markers", []))
    _scan_strings(request, markers, secret_leak_findings)
    _scan_strings(human, markers, secret_leak_findings)
    if previous_result is not None:
        _scan_strings(previous_result, markers, secret_leak_findings)

    result = _build_result(
        final_status="401_RETRY_AUTHORIZATION_GATE_READY_NO_EXECUTION",
        reason="",
        policy_violations=policy_violations,
        secret_leak_findings=secret_leak_findings,
        errors=errors,
        warnings=warnings,
        extra={
            "previous_status": previous_status,
            "previous_401_confirmed": previous_401_confirmed,
            "previous_freeze_required": previous_freeze_required,
            "previous_api_call_attempted": previous_api_call_attempted,
            "previous_write_executed": previous_write_executed,
            "retry_allowed": True,
            "retry_limit": 1,
            "retry_attempts_already_used": int(request.get("retry_attempts_already_used", 0)),
            "retry_attempts_remaining": int(request.get("retry_attempts_remaining", 1)),
            "human_approval_valid": decision == "APPROVE_401_RETRY_ONCE_ONLY",
            "human_decision": decision,
            "approval_scope": approval_scope,
            "previous_evidence_found": previous_evidence_path.exists(),
        },
    )

    if policy_violations:
        result["final_status"] = "ABORT_POLICY_VIOLATION"
        result["retry_authorized"] = False
        result["next_step"] = "manual_401_cause_review_and_retry_block"
    elif secret_leak_findings:
        result["final_status"] = "ABORT_SECRET_LEAK_RISK"
        result["retry_authorized"] = False
        result["next_step"] = "manual_401_cause_review_and_retry_block"
    elif decision == "REQUEST_FIX":
        result["final_status"] = "REQUEST_FIX_NO_EXECUTION"
        result["retry_authorized"] = False
        result["next_step"] = "manual_401_cause_review_and_retry_block"
    elif decision == "REJECT":
        result["final_status"] = "REJECTED_NO_EXECUTION"
        result["retry_authorized"] = False
        result["next_step"] = "stop_without_execution"
    elif decision == "ABORT":
        result["final_status"] = "ABORTED_NO_EXECUTION"
        result["retry_authorized"] = False
        result["next_step"] = "stop_without_execution"
    else:
        result["retry_authorized"] = True
        result["next_step"] = policy.get(
            "allowed_next_step_if_ready",
            "phase8_9_retry_or_manual_hold_after_human_approval",
        )

    _write_output(output_json_path, result)
    return result


def _build_result(
    final_status: str,
    reason: str,
    policy_violations: list[str],
    secret_leak_findings: list[str],
    errors: list[str],
    warnings: list[str],
    extra: dict[str, Any],
) -> dict[str, Any]:
    result = {
        "phase": "8-9R",
        "phase_name": "401 retry authorization gate",
        "phase_status": "DESIGN_ONLY_NO_EXECUTION",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "mode": "401_RETRY_AUTHORIZATION_GATE",
        "human_approval_required": True,
        "retry_allowed": True,
        "retry_limit": 1,
        "retry_scope": "WORDPRESS_DRAFT_CREATE_ONLY",
        "retry_authorized": False,
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
        "reason": reason,
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
    result = validate_phase8_9r_401_retry_authorization_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "401_RETRY_AUTHORIZATION_GATE_READY_NO_EXECUTION",
        "REQUEST_FIX_NO_EXECUTION",
        "REJECTED_NO_EXECUTION",
        "ABORTED_NO_EXECUTION",
    }
    return 0 if result.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())