#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
LOG_DIR = BLOCK_DIR / "logs"

POLICY_JSON = CONFIG_DIR / "article_payload_policy.json"
QUALITY_GATE_JSON = LOG_DIR / "sale_review_quality_gate.json"
NORMALIZED_JSON = LOG_DIR / "normalized_sale_candidates.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return -1.0


def _sort_key(item: Dict[str, Any]) -> Tuple[float, float, str]:
    confidence = _parse_confidence(item.get("confidence"))
    return (
        -float(item.get("priority_score", 0)),
        -confidence,
        str(item.get("title", "")).lower(),
    )


def _build_intro(title: str) -> str:
    return (
        f"{title} は、セール候補として確認したい注目作品です。"
        "価格や販売状況はリンク先で確認してください。"
    )


def _recommended_reader(title: str, campaign: str, note: str) -> str:
    text = " ".join([title.lower(), campaign.lower(), note.lower()])
    if "flash" in text or "sale" in text:
        return "短時間でセール候補をチェックしたい人におすすめです。"
    if "news" in text or "digest" in text:
        return "出版社の告知ベースで作品を追いたい人におすすめです。"
    if "editor" in text or "pick" in text:
        return "編集部ピック系の作品を優先して見たい人におすすめです。"
    return "電子書籍のセール候補を効率よく探したい人におすすめです。"


def _article_title(title: str, campaign: str) -> str:
    if campaign:
        return f"【{campaign}】{title} をチェック"
    return f"【セール候補】{title} をチェック"


def _amazon_link_candidate(title: str, author: str, asin: str) -> Dict[str, Any]:
    if asin:
        return {
            "link_type": "amazon_product_link_candidate",
            "asin": asin,
            "url": f"https://www.amazon.co.jp/dp/{asin}",
            "final_human_confirmation_required": True,
        }
    search_terms = " ".join([part for part in [title, author] if part]).strip()
    return {
        "link_type": "amazon_search_link_candidate",
        "search_terms": search_terms,
        "url": "https://www.amazon.co.jp/s?k=" + search_terms.replace(" ", "+"),
        "final_human_confirmation_required": True,
    }


def _sns_text(title: str) -> str:
    return (
        f"PRを含みます。『{title}』をセール候補としてチェック。"
        "価格・販売状況はリンク先で確認してください。"
    )


def generate_article_payloads(
    policy_json: Path = POLICY_JSON,
    quality_gate_json: Path = QUALITY_GATE_JSON,
    normalized_json: Path = NORMALIZED_JSON,
) -> Dict[str, Any]:
    policy = _read_json(policy_json)
    output_json = BLOCK_DIR / policy.get("output_json", "logs/sale_article_payloads.json")
    output_markdown = BLOCK_DIR / policy.get("output_markdown", "logs/sale_article_payloads.md")

    result: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-3",
        "block_name": "sale_flash_block",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "article_payload_count": 0,
        "skipped_candidate_count": 0,
        "max_payloads_per_run": int(policy.get("max_payloads_per_run", 10)),
        "input_quality_gate_status": "FAIL",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "creators_api_called": False,
        "amazon_scraping_called": False,
        "publish_executed": False,
        "update_executed": False,
        "delete_executed": False,
        "export_executed": False,
        "payloads": [],
        "skipped_candidates": [],
        "next_recommended_phase": "SFB-4: Article payload quality report / human review handoff",
    }

    if not quality_gate_json.exists():
        result["error"] = f"missing quality gate log: {quality_gate_json}"
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_markdown.write_text("# Sale Article Payloads\n\nquality gate log is missing.\n", encoding="utf-8")
        return result

    quality_gate = _read_json(quality_gate_json)
    normalized = _read_json(normalized_json) if normalized_json.exists() else {"candidates": []}
    normalized_map = {
        str(item.get("candidate_id", "")): item for item in normalized.get("candidates", [])
    }

    allowed_buckets = set(policy.get("allowed_review_buckets", []))
    excluded_buckets = set(policy.get("excluded_review_buckets", []))
    max_items = int(policy.get("max_payloads_per_run", 10))
    input_status = str(quality_gate.get("status", "FAIL"))
    result["input_quality_gate_status"] = input_status

    candidates = list(quality_gate.get("quality_queue", []))
    eligible: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for item in candidates:
        candidate_id = str(item.get("candidate_id", ""))
        title = str(item.get("title", "")).strip()
        bucket = str(item.get("review_bucket", "")).strip()

        if bucket in excluded_buckets:
            skipped.append(
                {
                    "candidate_id": candidate_id,
                    "title": title,
                    "review_bucket": bucket,
                    "skip_reason": "excluded_bucket",
                }
            )
            continue

        if bucket not in allowed_buckets:
            skipped.append(
                {
                    "candidate_id": candidate_id,
                    "title": title,
                    "review_bucket": bucket,
                    "skip_reason": "not_allowed_bucket",
                }
            )
            continue

        if not title:
            skipped.append(
                {
                    "candidate_id": candidate_id,
                    "title": title,
                    "review_bucket": bucket,
                    "skip_reason": "missing_title",
                }
            )
            continue

        eligible.append(item)

    eligible.sort(key=_sort_key)
    selected = eligible[:max_items]

    payloads: List[Dict[str, Any]] = []
    for idx, item in enumerate(selected, start=1):
        candidate_id = str(item.get("candidate_id", "")).strip()
        normalized_item = normalized_map.get(candidate_id, {})

        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip()
        asin = str(item.get("asin", "")).strip()
        campaign = str(normalized_item.get("campaign", "")).strip()
        isbn = str(normalized_item.get("isbn", "")).strip()
        sale_status = str(normalized_item.get("sale_status", "")).strip()
        note = str(normalized_item.get("note", "")).strip()

        payload = {
            "payload_id": f"sfb3-payload-{idx:03d}",
            "candidate_id": candidate_id,
            "source": str(item.get("source", "")).strip(),
            "title": title,
            "author": author,
            "asin": asin,
            "isbn": isbn,
            "campaign": campaign,
            "sale_status": sale_status,
            "confidence": item.get("confidence"),
            "review_bucket": str(item.get("review_bucket", "")).strip(),
            "priority_score": int(item.get("priority_score", 0)),
            "article_title": _article_title(title, campaign),
            "short_intro": _build_intro(title),
            "recommended_reader": _recommended_reader(title, campaign, note),
            "pr_disclosure": "PRを含みます。リンク先の価格・販売状況は変更される場合があります。",
            "amazon_link_candidate": _amazon_link_candidate(title, author, asin),
            "sns_post_candidate": _sns_text(title),
            "human_review_required": bool(policy.get("human_review_required", True)),
            "production_status": "NO_GO",
            "external_api_called": False,
            "external_network_called": False,
            "wordpress_write_executed": False,
            "creators_api_called": False,
            "amazon_scraping_called": False,
            "publish_executed": False,
            "update_executed": False,
            "delete_executed": False,
            "export_executed": False,
        }
        payloads.append(payload)

    if input_status == "FAIL":
        status = "FAIL"
    elif len(payloads) == 0:
        status = "WARN"
    else:
        status = "PASS"

    result["status"] = status
    result["article_payload_count"] = len(payloads)
    result["skipped_candidate_count"] = len(skipped)
    result["payloads"] = payloads
    result["skipped_candidates"] = skipped

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Sale Article Payloads",
        "",
        "## Summary",
        f"- status: {result['status']}",
        "- phase: SFB-3",
        f"- article_payload_count: {result['article_payload_count']}",
        f"- skipped_candidate_count: {result['skipped_candidate_count']}",
        f"- input_quality_gate_status: {result['input_quality_gate_status']}",
        "",
        "## Safety Gates",
        "- production_status: NO_GO",
        f"- external_api_called: {result['external_api_called']}",
        f"- external_network_called: {result['external_network_called']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- creators_api_called: {result['creators_api_called']}",
        f"- amazon_scraping_called: {result['amazon_scraping_called']}",
        "",
        "## Article Payloads",
        "| payload_id | title | review_bucket | priority_score | link_type | human_review_required |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for payload in payloads:
        md_lines.append(
            "| "
            + f"{payload.get('payload_id', '')} | "
            + f"{payload.get('title', '')} | "
            + f"{payload.get('review_bucket', '')} | "
            + f"{payload.get('priority_score', 0)} | "
            + f"{payload.get('amazon_link_candidate', {}).get('link_type', '')} | "
            + f"{payload.get('human_review_required', True)} |"
        )

    md_lines.extend(["", "## Skipped Candidates"])
    if not skipped:
        md_lines.append("- none")
    else:
        md_lines.append("| candidate_id | title | review_bucket | skip_reason |")
        md_lines.append("| --- | --- | --- | --- |")
        for item in skipped:
            md_lines.append(
                "| "
                + f"{item.get('candidate_id', '')} | "
                + f"{item.get('title', '')} | "
                + f"{item.get('review_bucket', '')} | "
                + f"{item.get('skip_reason', '')} |"
            )

    md_lines.extend([
        "",
        "## Next Phase",
        f"- next_recommended_phase: {result['next_recommended_phase']}",
    ])

    output_markdown.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_article_payloads()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
