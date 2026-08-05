#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BLOCK_DIR = Path(__file__).resolve().parents[1]
NORMALIZED_JSON = BLOCK_DIR / "logs/normalized_sale_candidates.json"
OUTPUT_JSON = BLOCK_DIR / "logs/sale_review_queue.json"


def _overall_from_input(input_status: str, item_count: int) -> str:
    if input_status == "FAIL":
        return "FAIL"
    if item_count == 0:
        return "WARN"
    if input_status == "WARN":
        return "WARN"
    return "PASS"


def generate_review_queue(
    normalized_json: Path = NORMALIZED_JSON,
    output_json: Path = OUTPUT_JSON,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "item_count": 0,
        "review_required_count": 0,
        "asin_candidate_count": 0,
        "search_candidate_count": 0,
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "queue": {
            "ready_for_manual_review": [],
            "asin_link_candidates": [],
            "search_link_candidates": [],
            "high_priority_candidates": [],
            "blocked_or_invalid_candidates": [],
        },
    }

    try:
        normalized = json.loads(normalized_json.read_text(encoding="utf-8"))
        candidates = normalized.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("normalized candidates must be a list")

        ready_for_manual_review: List[Dict[str, Any]] = []
        asin_link_candidates: List[Dict[str, Any]] = []
        search_link_candidates: List[Dict[str, Any]] = []
        high_priority_candidates: List[Dict[str, Any]] = []
        blocked_or_invalid_candidates: List[Dict[str, Any]] = []

        for item in candidates:
            candidate = {
                "candidate_id": item.get("candidate_id", ""),
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "asin": item.get("asin", ""),
                "link_strategy": item.get("link_strategy", "amazon_search_link_candidate"),
                "review_required": bool(item.get("review_required", False)),
                "review_reasons": item.get("review_reasons", []),
                "confidence": item.get("confidence"),
            }

            if candidate["review_required"]:
                ready_for_manual_review.append(candidate)

            if candidate["link_strategy"] == "amazon_product_link_candidate":
                asin_link_candidates.append(candidate)
            else:
                search_link_candidates.append(candidate)

            confidence = candidate.get("confidence")
            if isinstance(confidence, (int, float)) and confidence >= 0.85:
                high_priority_candidates.append(candidate)

            reasons = set(candidate.get("review_reasons", []))
            if "missing_title" in reasons or "missing_author" in reasons:
                blocked_or_invalid_candidates.append(candidate)

        payload["item_count"] = len(candidates)
        payload["review_required_count"] = len(ready_for_manual_review)
        payload["asin_candidate_count"] = len(asin_link_candidates)
        payload["search_candidate_count"] = len(search_link_candidates)
        payload["queue"] = {
            "ready_for_manual_review": ready_for_manual_review,
            "asin_link_candidates": asin_link_candidates,
            "search_link_candidates": search_link_candidates,
            "high_priority_candidates": high_priority_candidates,
            "blocked_or_invalid_candidates": blocked_or_invalid_candidates,
        }

        payload["status"] = _overall_from_input(
            str(normalized.get("status", "FAIL")),
            len(candidates),
        )

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    result = generate_review_queue()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
