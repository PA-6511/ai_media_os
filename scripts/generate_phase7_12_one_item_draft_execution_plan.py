#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_12_one_item_draft_execution_plan_policy.json"
DEFAULT_INPUT = ROOT / "exchange/examples/phase7_12_one_item_draft_execution_plan_input.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_12_one_item_draft_execution_plan_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_12_one_item_draft_execution_plan_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _is_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def generate_plan(
    policy_path: Path = DEFAULT_POLICY,
    input_path: Path = DEFAULT_INPUT,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    input_path = Path(input_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    plan_input = _load_json(input_path) if input_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not input_path.exists():
        errors.append(f"missing_input: {input_path}")

    for key in [
        "execution_plan_is_execution_permission",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "wordpress_api_call_allowed",
        "payload_write_allowed",
        "wordpress_write_executed",
        "publish_allowed",
    ]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    if plan_input.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    flags = plan_input.get("safety_flags", {})
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

    for idx, item in enumerate(plan_input.get("affiliate_links", [])):
        if not _is_https(str(item.get("url", ""))):
            safety_violations.append(f"affiliate_links[{idx}].url must be https")
    for idx, item in enumerate(plan_input.get("cta", [])):
        if not _is_https(str(item.get("url", ""))):
            safety_violations.append(f"cta[{idx}].url must be https")

    body = str(plan_input.get("body", ""))
    if not body.strip():
        errors.append("body is required")
    if "PR" not in body and "広告" not in body:
        errors.append("body must include PR/広告 notation")

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
    elif evidence_status == "ABORT":
        status = "ABORT"
    elif evidence_missing:
        status = "FAIL"
    elif evidence_status != policy.get("required_phase7_11_status"):
        status = "FAIL"
        warnings.append(f"phase7_11 status mismatch: {evidence_status}")
    elif errors:
        status = "FAIL"
    else:
        status = "EXECUTION_PLAN_READY_BUT_NO_GO"

    planned_payload = {}
    if status == "EXECUTION_PLAN_READY_BUT_NO_GO" and policy.get("payload_generation_allowed") is True:
        planned_payload = {
            "candidate_id": plan_input.get("candidate_id"),
            "title": plan_input.get("title"),
            "content": plan_input.get("body"),
            "status": "draft_candidate_plan_only",
            "category": plan_input.get("category"),
            "tags": plan_input.get("tags", []),
            "affiliate_links": plan_input.get("affiliate_links", []),
            "cta": plan_input.get("cta", []),
        }

    result = {
        "phase": "Phase 7-12",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "execution_plan_is_execution_permission": False,
        "target_item_count": plan_input.get("target_item_count"),
        "planned_wordpress_payload": planned_payload,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "blocked_operations": [
            "wordpress_rest_post",
            "wordpress_rest_put",
            "wordpress_rest_patch",
            "wordpress_rest_delete",
            "wordpress_publish",
            "wordpress_update",
            "wordpress_delete",
        ],
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-13 first controlled WordPress draft creation operator runbook",
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
        "# Phase 7-12 One-Item Draft Execution Plan Report",
        "",
        "## Purpose",
        "- Prepare one-item execution plan in DRY_RUN while keeping NO_GO.",
        "",
        "## Token Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")
    lines.extend(
        [
            "",
            "## Planned Payload",
            f"- status: {result.get('planned_wordpress_payload', {}).get('status')}",
            f"- title: {result.get('planned_wordpress_payload', {}).get('title')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            "",
            "## Blocked Operations",
        ]
    )
    for op in result.get("blocked_operations", []):
        lines.append(f"- {op}")
    lines.extend(
        [
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
    result = generate_plan()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"EXECUTION_PLAN_READY_BUT_NO_GO", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
