#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_9_first_one_item_wordpress_draft_create_rerun_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_8_final_credentialed_live_preflight_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_9_first_one_item_wordpress_draft_create_rerun_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_9_first_one_item_wordpress_draft_create_rerun_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def run_first_one_item_draft_create_rerun(
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

    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")
    if policy.get("update_allowed") is not False:
        safety_violations.append("update_allowed must be false")
    if policy.get("delete_allowed") is not False:
        safety_violations.append("delete_allowed must be false")
    if policy.get("bulk_execution") is not False:
        safety_violations.append("bulk_execution must be false")
    if policy.get("target_item_count") != 1:
        safety_violations.append("target_item_count must be 1")

    for key in ["auto_post", "auto_update", "auto_delete", "auto_export"]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    sop = policy.get("secret_output_policy", {})
    for key in ["print_values", "write_values_to_logs", "print_lengths", "print_prefix_suffix", "hash_values"]:
        if sop.get(key) is not False:
            safety_violations.append(f"secret_output_policy.{key} must be false")

    wp_request = policy.get("wordpress_request", {})
    if wp_request.get("status") != "draft":
        safety_violations.append("wordpress_request.status must be draft")
    if wp_request.get("max_posts") != 1:
        safety_violations.append("wordpress_request.max_posts must be 1")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    phase88_status = None
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        st = payload.get("status") or payload.get("overall_status")
        phase88_status = st
        evidence_summary.append({"path": rel, "exists": True, "status": st})

    status = "ABORT"
    wordpress_api_call_attempted = False
    wordpress_write_executed = False
    post_id = None
    post_status_value = None
    post_link = None
    freeze_required = True

    if safety_violations:
        status = "ABORT"
        freeze_required = True
    elif missing_evidence or phase88_status is None:
        status = "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY"
        freeze_required = False
        warnings.append("phase8_8 evidence missing")
    elif phase88_status != policy.get("required_phase8_8_status"):
        status = "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY"
        freeze_required = False
        warnings.append(f"phase8_8 status must be {policy.get('required_phase8_8_status')} but got {phase88_status}")
    else:
        required_env = policy.get("required_env", [])
        env_values = {key: os.getenv(key, "") for key in required_env}
        missing_env = [key for key, val in env_values.items() if not str(val).strip()]

        if missing_env:
            status = "RERUN_NOT_EXECUTED_MISSING_CREDENTIALS"
            freeze_required = False
            warnings.append(f"missing env: {', '.join(missing_env)}")
        else:
            payload = {
                "title": request.get("title", ""),
                "content": request.get("body", ""),
                "status": wp_request.get("status", "draft"),
            }

            if payload.get("status") != "draft":
                safety_violations.append("payload.status must be draft")

            if safety_violations:
                status = "ABORT"
                freeze_required = True
            else:
                base_url = env_values["WORDPRESS_BASE_URL"].rstrip("/")
                endpoint = wp_request.get("endpoint", "/wp-json/wp/v2/posts")
                url = f"{base_url}{endpoint}"
                wordpress_api_call_attempted = True
                try:
                    resp = requests.post(
                        url,
                        json=payload,
                        auth=(env_values["WORDPRESS_USERNAME"], env_values["WORDPRESS_APP_PASSWORD"]),
                        timeout=30,
                    )
                    if resp.status_code not in {200, 201}:
                        status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                        freeze_required = True
                        errors.append(f"unexpected_status_code: {resp.status_code}")
                    else:
                        data = resp.json()
                        resp_status = str(data.get("status", ""))
                        if resp_status.lower() in {"publish", "published"}:
                            status = "ABORT"
                            freeze_required = True
                            errors.append("response status must not be publish/published")
                        elif not data.get("id"):
                            status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                            freeze_required = True
                            errors.append("response missing post id")
                        elif resp_status != "draft":
                            status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                            freeze_required = True
                            errors.append(f"response status must be draft but got {resp_status}")
                        else:
                            link = data.get("link")
                            guid = data.get("guid")
                            guid_link = guid.get("rendered") if isinstance(guid, dict) else guid
                            final_link = link or guid_link
                            if not final_link:
                                status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                                freeze_required = True
                                errors.append("response missing link/guid")
                            else:
                                status = "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
                                freeze_required = False
                                wordpress_write_executed = True
                                post_id = data.get("id")
                                post_status_value = resp_status
                                post_link = final_link
                except requests.RequestException as exc:
                    status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                    freeze_required = True
                    errors.append(f"requests_exception: {exc}")
                except ValueError:
                    status = "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
                    freeze_required = True
                    errors.append("response json parse failed")

    if safety_violations and status != "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY":
        status = "ABORT"
        freeze_required = True

    result = {
        "phase": "Phase 8-9",
        "status": status,
        "production_status": policy.get("production_status", "LIMITED_DRAFT_CREATE_ONLY"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "ALLOW_ONE_DRAFT_ONLY"),
        "wordpress_api_call_allowed": True,
        "wordpress_api_call_attempted": wordpress_api_call_attempted,
        "wordpress_write_executed": wordpress_write_executed,
        "publish_allowed": False,
        "target_item_count": 1,
        "post_id": post_id,
        "post_status": post_status_value,
        "post_link": post_link,
        "freeze_required": freeze_required,
        "human_review_required": True,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-10 post-rerun verification and controlled draft flow closure report",
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
        "# Phase 8-9 First One-Item WordPress Draft Creation Rerun Report",
        "",
        "## Purpose",
        "- Execute one controlled WordPress draft creation rerun only when all gates are satisfied.",
        "",
        "## Phase 8-8 Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Execution Decision",
            f"- status: {result.get('status')}",
            f"- target_item_count: {result.get('target_item_count')}",
            "",
            "## WordPress API Attempt",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_api_call_attempted: {result.get('wordpress_api_call_attempted')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            "",
            "## Draft Result",
            f"- post_id: {result.get('post_id')}",
            f"- post_status: {result.get('post_status')}",
            f"- post_link: {result.get('post_link')}",
            "",
            "## Safety Flags",
            f"- publish_allowed: {result.get('publish_allowed')}",
            "",
            "## Secret Output Policy",
            f"- secret_values_written: {result.get('secret_values_written')}",
            "",
            "## Freeze Requirement",
            f"- freeze_required: {result.get('freeze_required')}",
            "",
            "## Human Review Requirement",
            f"- human_review_required: {result.get('human_review_required')}",
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
    result = run_first_one_item_draft_create_rerun()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "RERUN_NOT_EXECUTED_MISSING_CREDENTIALS",
        "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY",
        "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
