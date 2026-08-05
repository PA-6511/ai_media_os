#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_24_operator_go_no_go_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_24_operator_go_no_go.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_24_operator_go_no_go_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_24_operator_go_no_go_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_operator_go_no_go(
    policy_path: Path = DEFAULT_POLICY,
    review_path: Path = DEFAULT_REVIEW,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    review_path = Path(review_path)
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

    if policy.get("operator_decision_is_execution_permission") is not False:
        safety_violations.append("operator_decision_is_execution_permission must be false")
    if policy.get("commands_executed_in_this_phase") is not False:
        safety_violations.append("commands_executed_in_this_phase must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    root = _resolve_root(policy_path)
    snapshot_status = None
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        snapshot_status = payload.get("status") or payload.get("overall_status")
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if snapshot_status == "ABORT":
            safety_violations.append("phase8_23 snapshot status is ABORT")

    if not review_path.exists():
        errors.append(f"missing_human_review: {review_path}")
        result = _build_result("FAIL", errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    review = _load_json(review_path)

    if review.get("secret_values_included") is True:
        safety_violations.append("secret_values_included must be false")
    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for ack in policy.get("required_acknowledgements", []):
        if review.get(ack) is not True:
            safety_violations.append(f"{ack} must be true")

    required_scope = policy.get("approval_scope_required", {})
    scope = review.get("approval_scope", {})
    for key, expected in required_scope.items():
        if scope.get(key) != expected:
            safety_violations.append(f"approval_scope.{key} must be {expected}")

    if safety_violations:
        result = _build_result("ABORT", errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    decision = review.get("decision", "")
    allowed = set(policy.get("allowed_decisions", []))
    if decision not in allowed:
        status = "ABORT"
        safety_violations.append(f"unknown_decision: {decision}")
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("operator requested fix before handoff")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("operator rejected go/no-go review")
    elif decision == "ABORT":
        status = "ABORT"
    elif decision == "OPERATOR_GO_FOR_MANUAL_RERUN_HANDOFF_ONLY":
        if snapshot_status != policy.get("ready_snapshot_status"):
            status = "ABORT"
            safety_violations.append("GO decision is not allowed when snapshot is not ready")
        else:
            status = "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY"
    elif decision == "OPERATOR_NO_GO_CREDENTIALS_MISSING":
        if snapshot_status == policy.get("ready_snapshot_status"):
            status = "OPERATOR_NO_GO_CREDENTIALS_MISSING"
            warnings.append("snapshot ready but operator selected NO_GO")
        else:
            status = "OPERATOR_NO_GO_CREDENTIALS_MISSING"
    else:
        status = "ABORT"

    if safety_violations:
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
        "phase": "Phase 8-24",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "operator_decision_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": policy.get("target_item_count", 1),
        "secret_values_written": False,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-25 final manual rerun handoff package"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-24 Operator GO/NO-GO Decision Report",
        "",
        "## Purpose",
        "Record operator go/no-go decision without execution.",
        "",
        "## Snapshot Evidence",
        "- Phase 8-23 snapshot evidence is required.",
        "",
        "## Operator Decision",
        f"- status: {result.get('status')}",
        "",
        "## Acknowledgements",
        "- All required acknowledgements and scope checks are enforced.",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- operator_decision_is_execution_permission: {result.get('operator_decision_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ]
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_operator_go_no_go()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY",
        "OPERATOR_NO_GO_CREDENTIALS_MISSING",
        "WARN",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
