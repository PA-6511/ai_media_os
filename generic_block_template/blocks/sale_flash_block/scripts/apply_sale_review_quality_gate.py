#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
LOG_DIR = BLOCK_DIR / "logs"

POLICY_JSON = CONFIG_DIR / "quality_gate_policy.json"
QUEUE_JSON = LOG_DIR / "sale_review_queue.json"
OUTPUT_JSON = LOG_DIR / "sale_review_quality_gate.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_confidence(value: Any) -> Tuple[float, bool]:
    if isinstance(value, (int, float)):
        return float(value), False
    try:
        return float(str(value)), False
    except (TypeError, ValueError):
        return 0.0, True


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _build_duplicate_keys(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in candidates:
        title = _normalize_text(item.get("title")).lower()
        author = _normalize_text(item.get("author")).lower()
        if not title and not author:
            continue
        key = f"{title}::{author}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _priority_score(
    source: str,
    asin_present: bool,
    confidence: float,
    source_trust: Dict[str, float],
    low_confidence: bool,
    invalid_confidence: bool,
    missing_title: bool,
    missing_author: bool,
    is_duplicate: bool,
) -> int:
    trust = float(source_trust.get(source, source_trust.get("default", 0.5)))
    score = 0.0
    score += 40.0 if asin_present else 15.0
    score += max(0.0, min(confidence, 1.0)) * 40.0
    score += max(0.0, min(trust, 1.0)) * 20.0

    if low_confidence:
        score -= 20.0
    if invalid_confidence:
        score -= 60.0
    if missing_title or missing_author:
        score -= 50.0
    if is_duplicate:
        score -= 30.0

    return int(max(0.0, min(score, 100.0)))


def _bucket_for(
    is_duplicate: bool,
    missing_title: bool,
    missing_author: bool,
    invalid_confidence: bool,
    low_confidence: bool,
    asin_present: bool,
) -> str:
    if is_duplicate:
        return "duplicate_review"
    if missing_title or missing_author or invalid_confidence:
        return "blocked_or_invalid"
    if low_confidence:
        return "needs_metadata_fix"
    if not asin_present:
        return "needs_asin_confirmation"
    return "ready_high_priority"


def _ordered_candidates(candidates: List[Dict[str, Any]], bucket_order: List[str]) -> List[Dict[str, Any]]:
    bucket_rank = {name: idx for idx, name in enumerate(bucket_order)}

    def sort_key(item: Dict[str, Any]):
        confidence = item.get("confidence")
        conf_value, _ = _parse_confidence(confidence)
        return (
            bucket_rank.get(item.get("review_bucket", "blocked_or_invalid"), 999),
            -int(item.get("priority_score", 0)),
            -conf_value,
            _normalize_text(item.get("title")).lower(),
        )

    return sorted(candidates, key=sort_key)


def apply_quality_gate(
    policy_json: Path = POLICY_JSON,
    queue_json: Path = QUEUE_JSON,
    output_json: Path = OUTPUT_JSON,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "SFB-2",
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "creators_api_called": False,
        "amazon_scraping_called": False,
        "item_count": 0,
        "bucket_counts": {},
        "bucket_order": [],
        "quality_queue": [],
    }

    try:
        policy = _read_json(policy_json)
        queue = _read_json(queue_json)
        queue_payload = queue.get("queue", {})

        base_candidates: List[Dict[str, Any]] = []
        by_id: Dict[str, Dict[str, Any]] = {}
        for item in queue_payload.get("asin_link_candidates", []):
            candidate_id = _normalize_text(item.get("candidate_id"))
            if candidate_id:
                by_id[candidate_id] = dict(item)
        for item in queue_payload.get("search_link_candidates", []):
            candidate_id = _normalize_text(item.get("candidate_id"))
            if candidate_id and candidate_id not in by_id:
                by_id[candidate_id] = dict(item)

        base_candidates.extend(by_id.values())
        duplicate_keys = _build_duplicate_keys(base_candidates)

        low_threshold = float(policy.get("confidence_thresholds", {}).get("low", 0.7))
        source_trust = policy.get("source_trust", {})
        bucket_order = list(policy.get("bucket_order", []))
        if not bucket_order:
            bucket_order = [
                "ready_high_priority",
                "needs_asin_confirmation",
                "needs_metadata_fix",
                "duplicate_review",
                "blocked_or_invalid",
            ]

        enriched: List[Dict[str, Any]] = []
        for item in base_candidates:
            title = _normalize_text(item.get("title"))
            author = _normalize_text(item.get("author"))
            asin = _normalize_text(item.get("asin"))
            source = _normalize_text(item.get("source"))

            confidence_raw = item.get("confidence")
            confidence_value, invalid_confidence = _parse_confidence(confidence_raw)

            missing_title = title == ""
            missing_author = author == ""
            asin_present = asin != ""
            low_confidence = (not invalid_confidence) and (confidence_value < low_threshold)

            duplicate_key = f"{title.lower()}::{author.lower()}" if (title or author) else ""
            is_duplicate = bool(duplicate_key and duplicate_keys.get(duplicate_key, 0) > 1)

            bucket = _bucket_for(
                is_duplicate=is_duplicate,
                missing_title=missing_title,
                missing_author=missing_author,
                invalid_confidence=invalid_confidence,
                low_confidence=low_confidence,
                asin_present=asin_present,
            )

            score = _priority_score(
                source=source,
                asin_present=asin_present,
                confidence=confidence_value,
                source_trust=source_trust,
                low_confidence=low_confidence,
                invalid_confidence=invalid_confidence,
                missing_title=missing_title,
                missing_author=missing_author,
                is_duplicate=is_duplicate,
            )

            enriched.append(
                {
                    "candidate_id": _normalize_text(item.get("candidate_id")),
                    "source": source,
                    "title": title,
                    "author": author,
                    "asin": asin,
                    "asin_present": asin_present,
                    "asin_missing": not asin_present,
                    "duplicate_key": duplicate_key,
                    "duplicate_detected": is_duplicate,
                    "missing_title": missing_title,
                    "missing_author": missing_author,
                    "invalid_confidence": invalid_confidence,
                    "low_confidence": low_confidence,
                    "confidence": confidence_raw,
                    "source_trust": float(source_trust.get(source, source_trust.get("default", 0.5))),
                    "priority_score": score,
                    "review_bucket": bucket,
                    "quality_gate_status": "PASS" if bucket != "blocked_or_invalid" else "WARN",
                    "review_required": bool(item.get("review_required", False)),
                    "review_reasons": item.get("review_reasons", []),
                }
            )

        ordered = _ordered_candidates(enriched, bucket_order)
        bucket_counts: Dict[str, int] = {name: 0 for name in bucket_order}
        for item in ordered:
            bucket = item.get("review_bucket", "blocked_or_invalid")
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        queue_status = str(queue.get("status", "FAIL"))
        if queue_status == "FAIL":
            status = "FAIL"
        elif len(ordered) == 0:
            status = "WARN"
        else:
            status = "PASS"

        payload.update(
            {
                "status": status,
                "item_count": len(ordered),
                "bucket_counts": bucket_counts,
                "bucket_order": bucket_order,
                "quality_queue": ordered,
                "source": {
                    "policy": str(policy_json),
                    "queue": str(queue_json),
                },
            }
        )

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    result = apply_quality_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
