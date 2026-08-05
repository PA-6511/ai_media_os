#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_16_credential_operator_confirmation_policy.json"
DEFAULT_HUMAN_REVIEW = ROOT / "exchange/human_review/phase8_16_credential_operator_confirmation.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_16_credential_operator_confirmation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_16_credential_operator_confirmation_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_credential_operator_confirmation(
    policy_path: Path = DEFAULT_POLICY,
    human_review_path: Path = DEFAULT_HUMAN_REVIEW,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    human_review_path = Path(human_review_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("confirmation_is_execution_permission") is not False:
        safety_violations.append("confirmation_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous_ops = policy.get("dangerous_operations", {})
    for op_name, op_value in dangerous_ops.items():
        if op_value is not False:
            safety_violations.append(f"dangerous_operations.{op_name} must be false")

    root = _resolve_root(policy_path)
    required_statuses = policy.get("required_statuses", {})
    allowed_phase8_15 = set(policy.get("allowed_phase8_15_statuses", []))

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        if "phase8_11" in rel:
            expected = required_statuses.get("phase8_11")
            if expected is not None and status != expected:
                safety_violations.append(f"phase8_11 status must be {expected!r} but got {status!r}")
        if "phase8_12" in rel:
            expected = required_statuses.get("phase8_12")
            if expected is not None and status != expected:
                safety_violations.append(f"phase8_12 status must be {expected!r} but got {status!r}")
        if "phase8_15" in rel and status not in allowed_phase8_15:
            safety_violations.append(f"phase8_15 status {status!r} is not allowed")

    if not human_review_path.exists():
        errors.append(f"missing_human_review: {human_review_path}")
        result = _build_result("FAIL", errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    review = _load_json(human_review_path)

    if review.get("secret_values_included") is True:
        safety_violations.append("secret_values_included must be false")

    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for ack in policy.get("required_acknowledgements", []):
        if review.get(ack) is not True:
            safety_violations.append(f"{ack} must be true")

    approval_scope = review.get("approval_scope", {})
    if approval_scope.get("credential_confirmation_only") is not True:
        safety_violations.append("approval_scope.credential_confirmation_only must be true")
    if approval_scope.get("draft_create_only") is not False:
        safety_violations.append("approval_scope.draft_create_only must be false")
    for key in ["publish", "update", "delete", "bulk", "external_export"]:
        if approval_scope.get(key) is not False:
            safety_violations.append(f"approval_scope.{key} must be false")

    if safety_violations:
        result = _build_result("ABORT", errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    decision = review.get("decision", "")
    allowed_decisions = set(policy.get("allowed_decisions", []))
    if decision not in allowed_decisions:
        safety_violations.append(f"unknown_decision: {decision}")
        status = "ABORT"
    elif decision == "CONFIRM_CREDENTIALS_PROVISIONED_OUTSIDE_REPO":
        status = "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT"
    elif decision == "CONFIRM_CREDENTIALS_NOT_READY":
        status = "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT"
    elif decision == "REQUEST_FIX":
        warnings.append("operator requested fix before credential confirmation")
        status = "WARN"
    elif decision == "REJECT":
        errors.append("operator rejected credential operator confirmation")
        status = "FAIL"
    else:
        status = "ABORT"

    result = _build_result(status, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-16",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "confirmation_is_execution_permission": False,
        "target_item_count": 1,
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-17 environment-only credential presence smoke check",
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
        "# Phase 8-16 Credential Operator Confirmation Report",
        "",
        "## Purpose",
        "Record operator confirmation for credential provisioning outside the repository.",
        "",
        "## Prior Evidence",
        "- Phase 8-11 / 8-12 / 8-15 are validated before this decision.",
        "",
        "## Operator Decision",
        f"- status: {result.get('status')}",
        "",
        "## Acknowledgements",
        "- Required acknowledgements are enforced as true.",
        "",
        "## Secret Safety",
        "- secret values are not written or printed.",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Safety Flags",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- confirmation_is_execution_permission: {result.get('confirmation_is_execution_permission')}",
        f"- target_item_count: {result.get('target_item_count')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_credential_operator_confirmation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT",
        "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT",
        "WARN",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())