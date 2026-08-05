#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"

POLICY_JSON = CONFIG_DIR / "wordpress_draft_validation_policy.json"
PRICE_TERMS = ["円", "税込", "無料", "半額", "%OFF", "割引率", "最安", "確定価格"]
DISCOUNT_TERMS = ["セール確定", "割引確定", "%OFF", "半額", "割引率", "最安", "確定価格"]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_any(text: str, terms: List[str]) -> bool:
    return any(t in text for t in terms)


def _safety_flags_no_go(item: Dict[str, Any]) -> bool:
    return (
        item.get("production_status") == "NO_GO"
        and item.get("external_api_called") is False
        and item.get("external_network_called") is False
        and item.get("wordpress_write_executed") is False
        and item.get("creators_api_called") is False
        and item.get("amazon_scraping_called") is False
        and item.get("publish_executed") is False
        and item.get("update_executed") is False
        and item.get("delete_executed") is False
        and item.get("export_executed") is False
    )


def _validate_item(item: Dict[str, Any]) -> Dict[str, Any]:
    wp = item.get("wordpress_draft_candidate", {})
    body = wp.get("post_body_candidate", {}) if isinstance(wp, dict) else {}
    link = body.get("link_candidate", {}) if isinstance(body, dict) else {}

    post_title = str(wp.get("post_title", ""))
    excerpt = str(wp.get("post_excerpt", ""))
    intro = str(body.get("intro", ""))
    pr = str(body.get("pr_disclosure", ""))
    sns = str(item.get("sns_post_candidate", ""))
    text_blob = "\n".join([post_title, excerpt, intro, pr, sns])

    checks = {
        "post_format_valid": (
            isinstance(wp, dict)
            and wp.get("post_type") == "post"
            and wp.get("post_status") == "draft_candidate_only"
            and bool(post_title.strip())
        ),
        "pr_disclosure_present": ("PR" in pr) or ("PRを含みます" in pr),
        "link_candidate_present": isinstance(link, dict) and bool(link) and link.get("final_human_confirmation_required") is True,
        "body_required_fields_present": bool(intro.strip()) and bool(pr.strip()) and isinstance(link, dict) and bool(link),
        "no_price_claim": not _contains_any(text_blob, PRICE_TERMS),
        "no_discount_claim": not _contains_any(text_blob, DISCOUNT_TERMS),
        "safety_flags_no_go": _safety_flags_no_go(item),
    }

    blocking = [k for k, v in checks.items() if not v]
    if not checks["safety_flags_no_go"]:
        severity = "HIGH"
    elif not checks["post_format_valid"] or not checks["link_candidate_present"]:
        severity = "HIGH"
    elif not checks["pr_disclosure_present"] or not checks["body_required_fields_present"]:
        severity = "MEDIUM"
    elif not checks["no_price_claim"] or not checks["no_discount_claim"]:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "draft_handoff_id": item.get("draft_handoff_id", ""),
        "candidate_id": item.get("candidate_id", ""),
        "title": item.get("title", ""),
        "priority_score": item.get("priority_score", 0),
        "post_title": post_title,
        "validation_checks": checks,
        "blocking_reasons": blocking,
        "validation_severity": severity,
        "human_review_status": item.get("human_review_status", "NOT_REVIEWED"),
        "suggested_actions": [
            "format/pr/link checks and final human review"
            if not blocking
            else "fix blocking reasons before any publish decision"
        ],
    }


def validate_wordpress_draft_payloads(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    input_path = BLOCK_DIR / str(policy.get("input_wordpress_draft_handoff_log", "logs/wordpress_draft_handoff.json"))
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/wordpress_draft_payload_validation.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/wordpress_draft_payload_validation.md"))

    result: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-6",
        "block_name": "sale_flash_block",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "input_wordpress_draft_handoff_status": "FAIL",
        "input_draft_payload_count": 0,
        "validated_item_count": 0,
        "valid_item_count": 0,
        "needs_fix_item_count": 0,
        "high_severity_item_count": 0,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "creators_api_called": False,
        "amazon_scraping_called": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "human_approval_consumed": False,
        "final_publish_decision_allowed": bool(policy.get("final_publish_decision_allowed", False)),
        "final_human_gate": {
            "status": "NOT_READY",
            "human_approval_required": bool(policy.get("human_approval_required", True)),
            "human_approval_consumed": False,
            "final_publish_decision_allowed": bool(policy.get("final_publish_decision_allowed", False)),
        },
        "valid_items": [],
        "needs_fix_items": [],
        "next_recommended_phase": "SFB-7: Final human approval package (still NO_GO)"
    }

    if not input_path.exists():
        result["error"] = f"missing input wordpress draft handoff log: {input_path}"
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md.write_text("# WordPress Draft Payload Validation\n\ninput log is missing.\n", encoding="utf-8")
        return result

    input_payload = _read_json(input_path)
    drafts = list(input_payload.get("draft_candidates", []))

    result["input_wordpress_draft_handoff_status"] = str(input_payload.get("status", "FAIL"))
    result["input_draft_payload_count"] = int(input_payload.get("draft_payload_count", len(drafts)))

    validated: List[Dict[str, Any]] = [_validate_item(item) for item in drafts]
    valid_items = [x for x in validated if len(x.get("blocking_reasons", [])) == 0]
    needs_fix_items = [x for x in validated if len(x.get("blocking_reasons", [])) > 0]
    high_severity_count = sum(1 for x in validated if x.get("validation_severity") == "HIGH")

    result["validated_item_count"] = len(validated)
    result["valid_item_count"] = len(valid_items)
    result["needs_fix_item_count"] = len(needs_fix_items)
    result["high_severity_item_count"] = high_severity_count
    result["valid_items"] = valid_items
    result["needs_fix_items"] = needs_fix_items

    if high_severity_count == 0 and len(validated) > 0:
        result["final_human_gate"]["status"] = "READY_FOR_FINAL_HUMAN_GATE"
    else:
        result["final_human_gate"]["status"] = "BLOCKED_NEEDS_FIX"

    if result["input_wordpress_draft_handoff_status"] == "FAIL":
        status = "FAIL"
    elif high_severity_count > 0:
        status = "WARN"
    elif len(validated) == 0:
        status = "WARN"
    else:
        status = "PASS"

    result["status"] = status

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# WordPress Draft Payload Validation",
        "",
        "## Summary",
        f"- status: {result['status']}",
        "- phase: SFB-6",
        f"- input_wordpress_draft_handoff_status: {result['input_wordpress_draft_handoff_status']}",
        f"- validated_item_count: {result['validated_item_count']}",
        f"- valid_item_count: {result['valid_item_count']}",
        f"- needs_fix_item_count: {result['needs_fix_item_count']}",
        f"- high_severity_item_count: {result['high_severity_item_count']}",
        "",
        "## Safety Gates",
        "- production_status: NO_GO",
        f"- external_api_called: {result['external_api_called']}",
        f"- external_network_called: {result['external_network_called']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- update_executed: {result['update_executed']}",
        f"- delete_executed: {result['delete_executed']}",
        f"- export_executed: {result['export_executed']}",
        f"- human_approval_consumed: {result['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {result['final_publish_decision_allowed']}",
        "",
        "## Validation Results",
        "| draft_handoff_id | title | severity | blocking_reasons |",
        "| --- | --- | --- | --- |",
    ]

    for item in validated:
        md_lines.append(
            "| "
            + f"{item.get('draft_handoff_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{item.get('validation_severity', '')} | "
            + f"{'; '.join(item.get('blocking_reasons', [])) or 'none'} |"
        )

    if not validated:
        md_lines.append("| - | - | - | none |")

    md_lines.extend([
        "",
        "## Final Human Gate",
        f"- status: {result['final_human_gate']['status']}",
        f"- human_approval_required: {result['final_human_gate']['human_approval_required']}",
        f"- human_approval_consumed: {result['final_human_gate']['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {result['final_human_gate']['final_publish_decision_allowed']}",
        "",
        "## Next Phase",
        f"- next_recommended_phase: {result['next_recommended_phase']}",
    ])

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = validate_wordpress_draft_payloads()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
