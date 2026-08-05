#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_32_provisioned_declaration_overlay_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_32_provisioned_declaration_overlay.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_32_provisioned_declaration_overlay_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_32_provisioned_declaration_overlay_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_provisioned_declaration_overlay(
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
    evidence_summary: list[dict[str, Any]] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    for flag in [
        "overlay_is_execution_permission",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"{flag} must be false")

    root = _resolve_root(policy_path)
    phase8_31_status = None
    phase8_30_status = None

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            safety_violations.append(f"missing_evidence: {rel}")
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue

        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if "phase8_31" in rel:
            phase8_31_status = status
        if "phase8_30" in rel:
            phase8_30_status = status

    if phase8_31_status != policy.get("required_phase8_31_status"):
        safety_violations.append(
            f"phase8_31 status must be {policy.get('required_phase8_31_status')!r} but got {phase8_31_status!r}"
        )

    if phase8_30_status not in set(policy.get("allowed_phase8_30_statuses", [])):
        safety_violations.append(f"phase8_30 status not allowed: {phase8_30_status}")

    if not review_path.exists():
        errors.append(f"missing_human_review: {review_path}")
        result = _build_result("FAIL", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    review = _load_json(review_path)
    decision = review.get("decision", "")

    if review.get("secret_values_included") is True:
        safety_violations.append("secret_values_included must be false")
    if review.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for ack in policy.get("required_acknowledgements", []):
        if review.get(ack) is not True:
            safety_violations.append(f"{ack} must be true")

    scope = review.get("approval_scope", {})
    for key, expected in policy.get("approval_scope_required", {}).items():
        if scope.get(key) != expected:
            safety_violations.append(f"approval_scope.{key} must be {expected}")

    if safety_violations:
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    allowed = set(policy.get("allowed_decisions", []))
    if decision not in allowed:
        safety_violations.append(f"unknown_decision: {decision}")
        status = "ABORT"
    elif decision == "OVERLAY_DECLARE_CREDENTIALS_PROVISIONED_OUTSIDE_REPO":
        status = "OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT"
    elif decision == "OVERLAY_DECLARE_CREDENTIALS_STILL_NOT_READY":
        status = "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT"
    elif decision == "REQUEST_FIX":
        status = "WARN"
        warnings.append("operator requested fix")
    elif decision == "REJECT":
        status = "FAIL"
        errors.append("operator rejected overlay")
    else:
        status = "ABORT"

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 8-32",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "overlay_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get("allowed_next_step", "Phase 8-33 post-provision environment recheck without secret output"),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-32 Provisioned Declaration Overlay Report",
        "",
        "## Purpose",
        "Record overlay declaration without modifying prior evidence and without execution.",
        "",
        "## Prior Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend([
        "",
        "## Overlay Decision",
        f"- status: {result.get('status')}",
        "",
        "## Acknowledgements",
        "- Required acknowledgements and scope checks are enforced.",
        "",
        "## Secret Safety",
        "- Secret values are never output; only status and boolean-safe evidence is recorded.",
        "",
        "## Evidence Immutability",
        "- Overlay review does not modify prior phase evidence.",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- overlay_is_execution_permission: {result.get('overlay_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- phase8_6_to_8_10_executed: {result.get('phase8_6_to_8_10_executed')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = validate_provisioned_declaration_overlay()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
        "WARN",
        "FAIL",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
