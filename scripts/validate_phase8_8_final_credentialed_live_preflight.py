#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_8_final_credentialed_live_preflight_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_8_final_credentialed_live_preflight_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_8_final_credentialed_live_preflight_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_8_final_credentialed_live_preflight_result.md"


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
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def validate_final_credentialed_live_preflight(
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
        "wordpress_write_executed",
        "publish_allowed",
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

    for idx, item in enumerate(request.get("affiliate_links", [])):
        url = str(item.get("url", ""))
        if not _is_safe_https(url):
            safety_violations.append(f"affiliate_links[{idx}].url must be safe https")

    for idx, item in enumerate(request.get("cta", [])):
        url = str(item.get("url", ""))
        if not _is_safe_https(url):
            safety_violations.append(f"cta[{idx}].url must be safe https")

    body = str(request.get("body", ""))
    if not body.strip():
        errors.append("body must not be empty")
    if "PR" not in body and "広告" not in body:
        errors.append("body must include PR notation")

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
        st = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": st})
        if "phase8_2" in rel:
            evidence_map["phase8_2"] = st
        elif "phase8_6" in rel:
            evidence_map["phase8_6"] = st
        elif "phase8_7" in rel:
            evidence_map["phase8_7"] = st

    credentials_not_ready = False
    if missing_evidence:
        safety_violations.append("required evidence missing")
    else:
        required_statuses = policy.get("required_statuses", {})
        for key in ["phase8_2", "phase8_7"]:
            actual = evidence_map.get(key)
            expected = required_statuses.get(key)
            if actual != expected:
                safety_violations.append(f"{key} status must be {expected} but got {actual}")

        cred_actual = evidence_map.get("phase8_6")
        cred_required = policy.get("required_credential_status")
        if cred_actual != cred_required:
            if cred_actual == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT":
                credentials_not_ready = True
            else:
                safety_violations.append(
                    f"phase8_6 credential status must be {cred_required} but got {cred_actual}"
                )

    if safety_violations:
        status = "ABORT"
    elif credentials_not_ready:
        status = "NOT_READY_CREDENTIALS_MISSING"
        warnings.append("credentials not ready; set WORDPRESS_BASE_URL, WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD and rerun Phase 8-6")
    elif errors:
        status = "FAIL"
    else:
        status = "CREDENTIAL_PREFLIGHT_PASS_READY_FOR_PHASE8_9"

    result = {
        "phase": "Phase 8-8",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "preflight_is_execution_permission": False,
        "phase8_9_may_execute_if_this_passes": True,
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
            "Phase 8-9 first one-item WordPress draft creation rerun, only if all gates pass",
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
        "# Phase 8-8 Final Credentialed Live-Preflight Report",
        "",
        "## Purpose",
        "- Final readiness check integrating credential status and rerun review. No API call in this phase.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(["", "## Credential Readiness"])
    for item in result.get("evidence_summary", []):
        if "phase8_6" in str(item.get("path", "")):
            lines.append(f"- credential status: {item.get('status')}")

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
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- preflight_is_execution_permission: {result.get('preflight_is_execution_permission')}",
            "",
            "## Final Preflight Decision",
            f"- status: {result.get('status')}",
            "",
            "## Phase 8-9 Conditions",
            "- Phase 8-8 status must be CREDENTIAL_PREFLIGHT_PASS_READY_FOR_PHASE8_9",
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
    result = validate_final_credentialed_live_preflight()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "CREDENTIAL_PREFLIGHT_PASS_READY_FOR_PHASE8_9",
        "NOT_READY_CREDENTIALS_MISSING",
        "FAIL",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
