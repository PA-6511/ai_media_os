#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"

POLICY_JSON = CONFIG_DIR / "wordpress_draft_handoff_policy.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_safe(item: Dict[str, Any]) -> bool:
    return (
        item.get("production_status", "NO_GO") == "NO_GO"
        and bool(item.get("external_api_called", False)) is False
        and bool(item.get("external_network_called", False)) is False
        and bool(item.get("wordpress_write_executed", False)) is False
        and bool(item.get("creators_api_called", False)) is False
        and bool(item.get("amazon_scraping_called", False)) is False
        and bool(item.get("publish_executed", False)) is False
        and bool(item.get("update_executed", False)) is False
        and bool(item.get("delete_executed", False)) is False
        and bool(item.get("export_executed", False)) is False
    )


def _build_slug(title: str) -> str:
    keep = []
    for ch in title.lower().strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_"}:
            keep.append("-")
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "untitled-sale-candidate"


def generate_wordpress_draft_handoff(policy_json: Path = POLICY_JSON) -> Dict[str, Any]:
    policy = _read_json(policy_json)

    input_path = BLOCK_DIR / str(policy.get("input_handoff_log", "logs/sale_human_review_handoff.json"))
    output_json = BLOCK_DIR / str(policy.get("output_json", "logs/wordpress_draft_handoff.json"))
    output_md = BLOCK_DIR / str(policy.get("output_markdown", "logs/wordpress_draft_handoff.md"))

    result: Dict[str, Any] = {
        "status": "FAIL",
        "phase": "SFB-5",
        "block_name": "sale_flash_block",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "input_handoff_status": "FAIL",
        "input_handoff_item_count": 0,
        "selected_candidate_count": 0,
        "draft_payload_count": 0,
        "skipped_candidate_count": 0,
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
        "draft_candidates": [],
        "skipped_candidates": [],
        "next_recommended_phase": "SFB-6: WordPress DRY_RUN payload validation / final human gate",
    }

    if not input_path.exists():
        result["error"] = f"missing input handoff log: {input_path}"
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md.write_text("# WordPress Draft Handoff\n\ninput handoff log is missing.\n", encoding="utf-8")
        return result

    handoff = _read_json(input_path)
    adopt_candidates = list(handoff.get("adopt_candidates", []))
    max_candidates = int(policy.get("max_candidates_per_run", 5))

    result["input_handoff_status"] = str(handoff.get("status", "FAIL"))
    result["input_handoff_item_count"] = int(handoff.get("handoff_item_count", 0))

    selected: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for item in adopt_candidates:
        safe = _is_safe(item)
        title = str(item.get("title", "")).strip()
        article_title = str(item.get("article_title", "")).strip()

        if not safe:
            skipped.append(
                {
                    "candidate_id": item.get("candidate_id", ""),
                    "title": title,
                    "skip_reason": "safety_flag_violation",
                }
            )
            continue

        if not title or not article_title:
            skipped.append(
                {
                    "candidate_id": item.get("candidate_id", ""),
                    "title": title,
                    "skip_reason": "missing_title_or_article_title",
                }
            )
            continue

        selected.append(item)

    selected = sorted(selected, key=lambda x: (-int(x.get("priority_score", 0)), str(x.get("title", "")).lower()))[:max_candidates]

    draft_candidates: List[Dict[str, Any]] = []
    for idx, item in enumerate(selected, start=1):
        title = str(item.get("title", "")).strip()
        article_title = str(item.get("article_title", "")).strip()
        short_intro = str(item.get("short_intro", "")).strip()
        pr = str(item.get("pr_disclosure", "")).strip()
        link_candidate = item.get("amazon_link_candidate", {})
        sns = str(item.get("sns_post_candidate", "")).strip()

        excerpt = short_intro
        if pr:
            excerpt = f"{short_intro}\n\n{pr}".strip()

        draft_candidates.append(
            {
                "draft_handoff_id": f"sfb5-draft-{idx:03d}",
                "source_handoff_id": item.get("handoff_id", ""),
                "candidate_id": item.get("candidate_id", ""),
                "title": title,
                "priority_score": int(item.get("priority_score", 0)),
                "review_bucket": item.get("review_bucket", ""),
                "wordpress_draft_candidate": {
                    "post_type": "post",
                    "post_status": "draft_candidate_only",
                    "post_title": article_title,
                    "post_slug_candidate": _build_slug(title),
                    "post_excerpt": excerpt,
                    "post_body_candidate": {
                        "intro": short_intro,
                        "pr_disclosure": pr,
                        "link_candidate": link_candidate,
                        "recommended_reader": item.get("recommended_reader", ""),
                    },
                    "taxonomy_candidate": {
                        "category_candidates": ["sale-flash", "ebook-candidate"],
                        "tag_candidates": [title],
                    },
                },
                "sns_post_candidate": sns,
                "human_review_status": "NOT_REVIEWED",
                "handoff_notes": "wordpress draft candidate generated in DRY_RUN only",
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
        )

    result["selected_candidate_count"] = len(selected)
    result["draft_payload_count"] = len(draft_candidates)
    result["skipped_candidate_count"] = len(skipped)
    result["draft_candidates"] = draft_candidates
    result["skipped_candidates"] = skipped

    if result["input_handoff_status"] == "FAIL":
        status = "FAIL"
    elif any(s.get("skip_reason") == "safety_flag_violation" for s in skipped):
        status = "FAIL"
    elif len(draft_candidates) == 0:
        status = "WARN"
    else:
        status = "PASS"

    result["status"] = status

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# WordPress Draft Handoff",
        "",
        "## Summary",
        f"- status: {result['status']}",
        "- phase: SFB-5",
        f"- input_handoff_status: {result['input_handoff_status']}",
        f"- selected_candidate_count: {result['selected_candidate_count']}",
        f"- draft_payload_count: {result['draft_payload_count']}",
        f"- skipped_candidate_count: {result['skipped_candidate_count']}",
        "",
        "## Safety Gates",
        "- production_status: NO_GO",
        f"- external_api_called: {result['external_api_called']}",
        f"- external_network_called: {result['external_network_called']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- creators_api_called: {result['creators_api_called']}",
        f"- amazon_scraping_called: {result['amazon_scraping_called']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- update_executed: {result['update_executed']}",
        f"- delete_executed: {result['delete_executed']}",
        f"- export_executed: {result['export_executed']}",
        f"- human_approval_consumed: {result['human_approval_consumed']}",
        f"- final_publish_decision_allowed: {result['final_publish_decision_allowed']}",
        "",
        "## Draft Candidates",
        "| draft_handoff_id | title | priority_score | post_title | post_status | human_review_status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for item in draft_candidates:
        wp = item.get("wordpress_draft_candidate", {})
        md_lines.append(
            "| "
            + f"{item.get('draft_handoff_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{item.get('priority_score', 0)} | "
            + f"{wp.get('post_title', '')} | "
            + f"{wp.get('post_status', '')} | "
            + f"{item.get('human_review_status', '')} |"
        )

    if not draft_candidates:
        md_lines.append("| - | - | - | - | - | - |")

    md_lines.extend([
        "",
        "## Skipped Candidates",
        "| candidate_id | title | skip_reason |",
        "| --- | --- | --- |",
    ])

    for item in skipped:
        md_lines.append(
            "| "
            + f"{item.get('candidate_id', '')} | "
            + f"{item.get('title', '')} | "
            + f"{item.get('skip_reason', '')} |"
        )

    if not skipped:
        md_lines.append("| - | - | none |")

    md_lines.extend([
        "",
        "## Next Phase",
        f"- next_recommended_phase: {result['next_recommended_phase']}",
    ])

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_wordpress_draft_handoff()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
