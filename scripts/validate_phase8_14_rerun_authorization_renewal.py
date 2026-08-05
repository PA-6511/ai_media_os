#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_14_rerun_authorization_renewal_policy.json"
DEFAULT_HUMAN_REVIEW = ROOT / "exchange/human_review/phase8_14_rerun_authorization_renewal.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_14_rerun_authorization_renewal_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_14_rerun_authorization_renewal_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_rerun_authorization_renewal(
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
        status = "ABORT"
        result = _build_result(status, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    # Safety flags
    if policy.get("authorization_is_execution_permission") is not False:
        safety_violations.append("authorization_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    root = _resolve_root(policy_path)

    # Load evidence (phase8_13)
    phase813_status: str | None = None
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        if "phase8_13" in rel:
            phase813_status = payload.get("status") or payload.get("overall_status")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Check credentials readiness
    required_ready = policy.get("required_credential_ready_status", "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT")
    allowed_not_ready = policy.get("allowed_if_not_ready_status", "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")

    if phase813_status == allowed_not_ready:
        status = "RERUN_AUTHORIZATION_NOT_READY_CREDENTIALS_MISSING"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    if phase813_status != required_ready:
        safety_violations.append(
            f"phase8_13 must be {required_ready!r} or {allowed_not_ready!r}, got {phase813_status!r}"
        )
        status = "ABORT"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Load human review
    if not human_review_path.exists():
        errors.append(f"missing_human_review: {human_review_path}")
        status = "FAIL"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    review = _load_json(human_review_path)

    # Check forbidden decisions
    decision = review.get("decision", "")
    forbidden_decisions = policy.get("forbidden_decisions", [])
    if decision in forbidden_decisions:
        safety_violations.append(f"forbidden_decision: {decision}")
        status = "ABORT"
        result = _build_result(status, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Check decision value
    allowed_decisions = policy.get("allowed_decisions", [])
    if decision == "ABORT":
        status = "ABORT"
    elif decision == "REJECT":
        errors.append("human operator rejected the authorization renewal")
        status = "FAIL"
    elif decision == "REQUEST_FIX":
        warnings.append("human operator requested a fix before renewal")
        status = "WARN"
    elif decision == "ACKNOWLEDGE_RERUN_AUTHORIZATION_RENEWAL_ONLY":
        # Check acknowledgements
        missing_acks = []
        for ack in policy.get("required_acknowledgements", []):
            if not review.get(ack):
                missing_acks.append(ack)
        if missing_acks:
            for ack in missing_acks:
                errors.append(f"missing_acknowledgement: {ack}")
            status = "FAIL"
        else:
            # Check approval_scope
            required_scope = policy.get("approval_scope_required", {})
            review_scope = review.get("approval_scope", {})
            scope_ok = True
            for k, v in required_scope.items():
                if review_scope.get(k) != v:
                    errors.append(f"approval_scope.{k} must be {v}")
                    scope_ok = False
            status = "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY" if scope_ok else "FAIL"
    elif decision not in allowed_decisions:
        safety_violations.append(f"unknown_decision: {decision}")
        status = "ABORT"
    else:
        errors.append(f"unhandled_decision: {decision}")
        status = "FAIL"

    result = _build_result(status, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    errors: list,
    warnings: list,
    safety_violations: list,
    policy: dict,
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-14",
        "status": status,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "authorization_is_execution_permission": False,
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-15 rerun handoff report for Phase 8-6 to Phase 8-10 re-execution",
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
        "# Phase 8-14 Rerun Authorization Renewal Report",
        "",
        "## Purpose",
        "Record the human operator's explicit acknowledgement for re-run authorization.",
        "This is NOT execution permission.",
        "",
        "## Judgment",
        f"- status: {result.get('status')}",
        f"- authorization_is_execution_permission: {result.get('authorization_is_execution_permission')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_rerun_authorization_renewal()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY",
        "RERUN_AUTHORIZATION_NOT_READY_CREDENTIALS_MISSING",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
