#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
LOG_DIR = BLOCK_DIR / "logs"

POLICY_JSON = CONFIG_DIR / "human_review_handoff_policy.json"

PRICE_CLAIM_TERMS = ["円", "税込", "無料", "半額", "%OFF", "割引率", "最安", "確定価格"]
DISCOUNT_CLAIM_TERMS = ["セール確定", "割引率", "%OFF", "半額", "確定価格"]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _safety_flags_no_go(payload: Dict[str, Any]) -> bool:
    return (
        payload.get("production_status") == "NO_GO"
        and payload.get("external_api_called") is False
        and payload.get("external_network_called") is False
        and payload.get("wordpress_write_executed") is False
        and payload.get("creators_api_called") is False
        and payload.get("amazon_scraping_called") is False
        and payload.get("publish_executed") is False
        and payload.get("update_executed") is False
        and payload.get("delete_executed") is False
        and payload.get("export_executed") is False
    )


def _compute_checks(payload: Dict[str, Any]) -> Dict[str, bool]:
    pr_disclosure = str(payload.get("pr_disclosure", ""))
    sns_text = str(payload.get("sns_post_candidate", ""))
    article_title = str(payload.get("article_title", ""))
    short_intro = str(payload.get("short_intro", ""))
    recommended_reader = str(payload.get("recommended_reader", ""))

    link_candidate = payload.get("amazon_link_candidate") or {}
    link_present = isinstance(link_candidate, dict) and bool(link_candidate)
    link_confirm = bool(link_candidate.get("final_human_confirmation_required") is True)

    check_text = "\n".join([article_title, short_intro, sns_text, pr_disclosure, recommended_reader])

    return {
        "pr_disclosure_present": ("PR" in pr_disclosure) or ("PRを含みます" in pr_disclosure),
        "link_candidate_present": link_present and link_confirm,
        "sns_post_candidate_present": bool(sns_text.strip()) and (("PR" in sns_text) or ("PRを含みます" in sns_text)),
        "human_review_required": payload.get("human_review_required") is True,
        "no_price_claim": not _contains_any(check_text, PRICE_CLAIM_TERMS),
        "no_discount_claim": not _contains_any(check_text, DISCOUNT_CLAIM_TERMS),
        "safety_flags_no_go": _safety_flags_no_go(payload),
    }


def _fix_priority(review_bucket: str, checks: Dict[str, bool], missing_title: bool, missing_article_title: bool) -> str:
    if not checks["safety_flags_no_go"]:
        return "HIGH"
    if (not checks["pr_disclosure_present"]) or (not checks["link_candidate_present"]):
        return "HIGH"
    if (not checks["sns_post_candidate_present"]) or review_bucket == "needs_asin_confirmation":
        return "MEDIUM"
    if missing_title or missing_article_title:
        return "MEDIUM"
    return "LOW"


def _suggest_actions(blocking: List[str], review_bucket: str) -> List[str]:
    actions: List[str] = []
    mapping = {
        "safety_flags_no_go": "安全フラグ違反を修正して再生成してください。",
        "pr_disclosure_present": "PR表記を追記してください。",
        "link_candidate_present": "リンク候補と human confirmation フラグを補完してください。",
        "sns_post_candidate_present": "SNS文候補を追記し、PR表記を含めてください。",
        "human_review_required": "human_review_required を true に戻してください。",
        "no_price_claim": "価格・割引率の断定表現を削除してください。",
        "no_discount_claim": "セール確定表現を削除し、候補表現に修正してください。",
        "missing_title": "タイトルを補完してください。",
        "missing_article_title": "article_title を再生成してください。",
    }
    for reason in blocking:
        if reason in mapping:
            actions.append(mapping[reason])

    if review_bucket == "needs_asin_confirmation":
        actions.append("ASIN候補または検索キーワードを人手確認してください。")

    if not actions:
        actions.append("人間レビューで最終確認してください。")
    return actions


def _classify(
    review_bucket: str,
    checks: Dict[str, bool],
    adopt_buckets: set[str],
    needs_fix_buckets: set[str],
    excluded_buckets: set[str],
    missing_title: bool,
    missing_article_title: bool,
) -> str:
    if not checks["safety_flags_no_go"]:
        return "excluded_candidate"
    if review_bucket in excluded_buckets:
        return "excluded_candidate"
    if missing_title or missing_article_title:
        return "excluded_candidate"

    all_ok = all(checks.values())
    if review_bucket in adopt_buckets and all_ok:
        return "adopt_candidate"

    if review_bucket in needs_fix_buckets:
        return "needs_fix_candidate"

    if not all_ok:
        return "needs_fix_candidate"

    return "adopt_candidate"


def _build_handoff_item(
    idx: int,
    payload: Dict[str, Any],
    policy: Dict[str, Any],
) -> Tuple[Dict[str, Any], str]:
    review_bucket = str(payload.get("review_bucket", "")).strip()
    title = str(payload.get("title", "")).strip()
    article_title = str(payload.get("article_title", "")).strip()

    checks = _compute_checks(payload)
    required_checks = list(policy.get("required_checks", []))
    blocking = [name for name in required_checks if not checks.get(name, False)]

    missing_title = title == ""
    missing_article_title = article_title == ""
    if missing_title:
        blocking.append("missing_title")
    if missing_article_title:
        blocking.append("missing_article_title")

    adopt_buckets = set(policy.get("adopt_review_buckets", []))
    needs_fix_buckets = set(policy.get("needs_fix_review_buckets", []))
    excluded_buckets = set(policy.get("excluded_review_buckets", []))

    handoff_bucket = _classify(
        review_bucket=review_bucket,
        checks=checks,
        adopt_buckets=adopt_buckets,
        needs_fix_buckets=needs_fix_buckets,
        excluded_buckets=excluded_buckets,
        missing_title=missing_title,
        missing_article_title=missing_article_title,
    )

    fix_priority = _fix_priority(review_bucket, checks, missing_title, missing_article_title)
    suggested_actions = _suggest_actions(blocking, review_bucket)

    item = {
        "handoff_id": f"sfb4-handoff-{idx:03d}",
        "payload_id": payload.get("payload_id", ""),
        "candidate_id": payload.get("candidate_id", ""),
        "title": title,
        "author": payload.get("author", ""),
        "source": payload.get("source", ""),
        "review_bucket": review_bucket,
        "priority_score": payload.get("priority_score", 0),
        "article_title": article_title,
        "short_intro": payload.get("short_intro", ""),
        "recommended_reader": payload.get("recommended_reader", ""),
        "pr_disclosure": payload.get("pr_disclosure", ""),
        "amazon_link_candidate": payload.get("amazon_link_candidate", {}),
        "sns_post_candidate": payload.get("sns_post_candidate", ""),
        "human_review_status": policy.get("handoff_status_default", "NOT_REVIEWED"),
        "handoff_bucket": handoff_bucket,
        "fix_priority": fix_priority,
        "review_checks": checks,
        "review_notes": "human review required before any publish decision",
        "blocking_reasons": blocking,
        "suggested_human_actions": suggested_actions,
    }
    return item, handoff_bucket


def _build_excluded_from_skipped(idx: int, skipped: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    reason = str(skipped.get("skip_reason", "excluded_from_payload")).strip() or "excluded_from_payload"
    return {
        "handoff_id": f"sfb4-skip-{idx:03d}",
        "payload_id": "",
        "candidate_id": skipped.get("candidate_id", ""),
        "title": skipped.get("title", ""),
        "author": "",
        "source": "",
        "review_bucket": skipped.get("review_bucket", ""),
        "priority_score": 0,
        "article_title": "",
        "short_intro": "",
        "recommended_reader": "",
        "pr_disclosure": "",
        "amazon_link_candidate": {},
        "sns_post_candidate": "",
        "human_review_status": policy.get("handoff_status_default", "NOT_REVIEWED"),
        "handoff_bucket": "excluded_candidate",
        "fix_priority": "HIGH",
        "review_checks": {
            "pr_disclosure_present": False,
            "link_candidate_present": False,
            "sns_post_candidate_present": False,
            "human_review_required": True,
            "no_price_claim": True,
            "no_discount_claim": True,
            "safety_flags_no_go": True,
        },
        "review_notes": "excluded from article payload stage",
        "blocking_reasons": [reason],
        "suggested_human_actions": ["候補を再収集または入力補完してください。"],
    }


def generate_handoff(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    input_path = BLOCK_DIR / str(policy.get("input_article_payload_log", "logs/sale_article_payloads.json"))
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/sale_human_review_handoff.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/sale_human_review_handoff.md"))

    result: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-4",
        "block_name": "sale_flash_block",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "input_article_payload_status": "FAIL",
        "input_article_payload_count": 0,
        "handoff_item_count": 0,
        "adopt_candidate_count": 0,
        "needs_fix_candidate_count": 0,
        "excluded_candidate_count": 0,
        "top_review_targets": [],
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
        "adopt_candidates": [],
        "needs_fix_candidates": [],
        "excluded_candidates": [],
        "next_recommended_phase": "SFB-5: Human-reviewed article candidate selection / WordPress DRY_RUN handoff",
    }

    if not input_path.exists():
        result["error"] = f"missing input article payload log: {input_path}"
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md.write_text("# Sale Human Review Handoff\n\ninput article payload log is missing.\n", encoding="utf-8")
        return result

    input_payload = _read_json(input_path)
    payloads = list(input_payload.get("payloads", []))
    skipped = list(input_payload.get("skipped_candidates", []))

    result["input_article_payload_status"] = str(input_payload.get("status", "FAIL"))
    result["input_article_payload_count"] = int(input_payload.get("article_payload_count", 0))

    adopt_candidates: List[Dict[str, Any]] = []
    needs_fix_candidates: List[Dict[str, Any]] = []
    excluded_candidates: List[Dict[str, Any]] = []

    for idx, payload in enumerate(payloads, start=1):
        item, bucket = _build_handoff_item(idx, payload, policy)
        if bucket == "adopt_candidate":
            adopt_candidates.append(item)
        elif bucket == "needs_fix_candidate":
            needs_fix_candidates.append(item)
        else:
            excluded_candidates.append(item)

    skip_base = len(payloads)
    for offset, item in enumerate(skipped, start=1):
        excluded_candidates.append(_build_excluded_from_skipped(skip_base + offset, item, policy))

    total = len(adopt_candidates) + len(needs_fix_candidates) + len(excluded_candidates)
    result["handoff_item_count"] = total
    result["adopt_candidate_count"] = len(adopt_candidates)
    result["needs_fix_candidate_count"] = len(needs_fix_candidates)
    result["excluded_candidate_count"] = len(excluded_candidates)

    review_targets = sorted(
        adopt_candidates + needs_fix_candidates,
        key=lambda x: (-int(x.get("priority_score", 0)), x.get("title", "")),
    )
    result["top_review_targets"] = [
        {
            "handoff_id": item.get("handoff_id", ""),
            "title": item.get("title", ""),
            "handoff_bucket": item.get("handoff_bucket", ""),
            "priority_score": item.get("priority_score", 0),
        }
        for item in review_targets[:5]
    ]

    result["adopt_candidates"] = adopt_candidates
    result["needs_fix_candidates"] = needs_fix_candidates
    result["excluded_candidates"] = excluded_candidates

    safety_violation = any(not item.get("review_checks", {}).get("safety_flags_no_go", False) for item in (adopt_candidates + needs_fix_candidates + excluded_candidates))

    if result["input_article_payload_status"] == "FAIL":
        status = "FAIL"
    elif safety_violation:
        status = "FAIL"
    elif total == 0:
        status = "WARN"
    elif len(adopt_candidates) == 0 and len(needs_fix_candidates) > 0:
        status = "WARN"
    else:
        status = "PASS"

    result["status"] = status

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Sale Human Review Handoff",
        "",
        "## Summary",
        f"- status: {result['status']}",
        "- phase: SFB-4",
        f"- input_article_payload_status: {result['input_article_payload_status']}",
        f"- handoff_item_count: {result['handoff_item_count']}",
        f"- adopt_candidate_count: {result['adopt_candidate_count']}",
        f"- needs_fix_candidate_count: {result['needs_fix_candidate_count']}",
        f"- excluded_candidate_count: {result['excluded_candidate_count']}",
        "",
        "## Safety Gates",
        "- production_status: NO_GO",
        f"- external_api_called: {result['external_api_called']}",
        f"- external_network_called: {result['external_network_called']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- creators_api_called: {result['creators_api_called']}",
        f"- amazon_scraping_called: {result['amazon_scraping_called']}",
        f"- human_approval_consumed: {result['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {result['final_publish_decision_allowed']}",
        "",
        "## Adopt Candidates",
        "| handoff_id | title | priority_score | link_type | sns_ok | pr_ok | action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in adopt_candidates:
        checks = item.get("review_checks", {})
        md_lines.append(
            "| "
            + f"{item.get('handoff_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{item.get('priority_score', 0)} | "
            + f"{item.get('amazon_link_candidate', {}).get('link_type', '')} | "
            + f"{checks.get('sns_post_candidate_present', False)} | "
            + f"{checks.get('pr_disclosure_present', False)} | "
            + "human finalize check |"
        )
    if not adopt_candidates:
        md_lines.append("| - | - | - | - | - | - | no adopt candidates |")

    md_lines.extend([
        "",
        "## Needs Fix Candidates",
        "| handoff_id | title | fix_priority | blocking_reasons | suggested_actions |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in needs_fix_candidates:
        md_lines.append(
            "| "
            + f"{item.get('handoff_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{item.get('fix_priority', '')} | "
            + f"{'; '.join(item.get('blocking_reasons', []))} | "
            + f"{'; '.join(item.get('suggested_human_actions', []))} |"
        )
    if not needs_fix_candidates:
        md_lines.append("| - | - | - | - | none |")

    md_lines.extend([
        "",
        "## Excluded Candidates",
        "| handoff_id | title | reasons |",
        "| --- | --- | --- |",
    ])
    for item in excluded_candidates:
        md_lines.append(
            "| "
            + f"{item.get('handoff_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{'; '.join(item.get('blocking_reasons', []))} |"
        )
    if not excluded_candidates:
        md_lines.append("| - | - | none |")

    md_lines.extend([
        "",
        "## Review Checklist",
        "- pr_disclosure_present",
        "- link_candidate_present",
        "- sns_post_candidate_present",
        "- human_review_required",
        "- no_price_claim",
        "- no_discount_claim",
        "- safety_flags_no_go",
        "",
        "## Next Phase",
        f"- next_recommended_phase: {result['next_recommended_phase']}",
    ])

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_handoff()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
