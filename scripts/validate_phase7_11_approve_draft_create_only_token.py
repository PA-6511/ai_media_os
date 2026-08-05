#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_11_approve_draft_create_only_token_validation_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase7_11_approve_draft_create_only_token_validation_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_11_approve_draft_create_only_token_validation_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_11_approve_draft_create_only_token_validation_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_token(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    request = _load_json(request_path) if request_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not request_path.exists():
        safety_violations.append(f"missing_request: {request_path}")

    if policy.get("token_validation_is_activation") is not False:
        safety_violations.append("token_validation_is_activation must be false")
    if policy.get("approve_draft_create_only_currently_allowed") is not False:
        safety_violations.append("approve_draft_create_only_currently_allowed must be false")
    if policy.get("unlock_in_this_phase") is not False:
        safety_violations.append("unlock_in_this_phase must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    if request.get("token_activation_requested") is True:
        safety_violations.append("token_activation_requested must be false")
    if request.get("token_execution_requested") is True:
        safety_violations.append("token_execution_requested must be false")

    rules = policy.get("token_rules", {})
    if request.get("token_name") != rules.get("token_name"):
        safety_violations.append("token_name mismatch")
    if request.get("target_item_count") != rules.get("requires_target_item_count"):
        safety_violations.append("target_item_count must be 1")

    flags = request.get("safety_flags", {})
    for key in [
        "wordpress_write_executed",
        "wordpress_api_call_allowed",
        "publish_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]:
        if flags.get(key) is not False:
            safety_violations.append(f"safety_flags.{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    evidence_missing = False
    evidence_status = None
    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            evidence_missing = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        evidence_status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": evidence_status})

    if safety_violations:
        status = "ABORT"
    elif evidence_status in {"ABORT", "FAIL"}:
        status = "ABORT"
    elif evidence_missing:
        status = "TOKEN_NOT_READY"
    elif evidence_status != policy.get("required_phase7_10_status"):
        status = "TOKEN_NOT_READY"
        warnings.append(f"phase7_10 status mismatch: {evidence_status}")
    elif request.get("final_preflight_required") is not True:
        status = "TOKEN_NOT_READY"
        warnings.append("final_preflight_required must be true")
    elif request.get("freeze_path_exists") is not True:
        status = "TOKEN_NOT_READY"
        warnings.append("freeze_path_exists must be true")
    else:
        status = "TOKEN_READY_BUT_LOCKED"

    result = {
        "phase": "Phase 7-11",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "token_validation_is_activation": False,
        "target_item_count": request.get("target_item_count"),
        "token_name": request.get("token_name"),
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-12 one-item controlled draft creation execution plan DRY_RUN",
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
        "# Phase 7-11 APPROVE_DRAFT_CREATE_ONLY Token Validation Report",
        "",
        "## Purpose",
        "- Finalize token validation conditions while keeping token locked.",
        "",
        "## Token Rules",
        f"- token_name: {result.get('token_name')}",
        f"- token_validation_is_activation: {result.get('token_validation_is_activation')}",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            "",
            "## Validation Decision",
            f"- status: {result.get('status')}",
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
    result = validate_token()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"TOKEN_READY_BUT_LOCKED", "TOKEN_NOT_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
