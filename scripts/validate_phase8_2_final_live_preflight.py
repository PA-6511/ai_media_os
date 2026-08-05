#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_2_final_live_preflight_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_2_final_live_preflight_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_2_final_live_preflight_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_2_final_live_preflight_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _is_safe_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return False
    return bool(parsed.netloc)


def validate_final_live_preflight(
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

    for key in [
        "preflight_is_execution_permission",
        "wordpress_api_call_allowed",
        "wordpress_api_call_allowed_in_phase8_2",
        "wordpress_write_executed",
        "publish_allowed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
    ]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    if request.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")
    if request.get("approval_token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approval_token must be APPROVE_DRAFT_CREATE_ONLY")

    body = str(request.get("body", ""))
    if not body.strip():
        errors.append("body must not be empty")
    if "PR" not in body and "広告" not in body:
        errors.append("body must include PR notation")

    for idx, item in enumerate(request.get("affiliate_links", [])):
        url = str(item.get("url", ""))
        if not _is_safe_https(url):
            safety_violations.append(f"affiliate_links[{idx}].url must be safe https")

    for idx, item in enumerate(request.get("cta", [])):
        url = str(item.get("url", ""))
        if not _is_safe_https(url):
            safety_violations.append(f"cta[{idx}].url must be safe https")

    flags = request.get("safety_flags", {})
    for key in [
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
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
    evidence_map: dict[str, Any] = {}
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if "phase7_14" in rel:
            evidence_map["phase7_14"] = status
        elif "phase8_1" in rel:
            evidence_map["phase8_1"] = status

    required_statuses = policy.get("required_statuses", {})
    if missing_evidence:
        safety_violations.append("required evidence missing")
    else:
        for key in ["phase7_14", "phase8_1"]:
            actual = evidence_map.get(key)
            expected = required_statuses.get(key)
            if actual != expected:
                safety_violations.append(f"{key} status must be {expected} but got {actual}")
            if actual in {"ABORT", "FAIL"}:
                safety_violations.append(f"{key} evidence status is unsafe: {actual}")

    if safety_violations:
        status = "ABORT"
    elif errors:
        status = "FAIL"
    else:
        status = "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE"

    result = {
        "phase": "Phase 8-2",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "preflight_is_execution_permission": False,
        "phase8_3_may_execute_if_this_passes": True,
        "target_item_count": request.get("target_item_count"),
        "approval_token": request.get("approval_token"),
        "evidence_summary": evidence_summary,
        "candidate_summary": {
            "candidate_id": request.get("candidate_id"),
            "title": request.get("title"),
            "category": request.get("category"),
        },
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-3 first one-item WordPress draft creation execution only if human explicitly approves",
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
        "# Phase 8-2 Final Live-Preflight Report",
        "",
        "## Purpose",
        "- Final readiness check for a single controlled draft creation while keeping this phase NO_GO.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Candidate Summary",
            f"- candidate_id: {result.get('candidate_summary', {}).get('candidate_id')}",
            f"- title: {result.get('candidate_summary', {}).get('title')}",
            f"- category: {result.get('candidate_summary', {}).get('category')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            "",
            "## Final Preflight Decision",
            f"- status: {result.get('status')}",
            "",
            "## Phase 8-3 Conditions",
            "- explicit human approval file must stay valid",
            "- target_item_count must stay 1",
            "- publish/update/delete/bulk/export must stay disabled",
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
    result = validate_final_live_preflight()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
