#!/usr/bin/env python3
"""SFB-13: CSV Import Diff Report Enhancement (NO_GO / DRY_RUN only)."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/sfb_13_csv_import_diff_report_enhancement_policy.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(raw: str) -> tuple[float, bool]:
    s = (raw or "").strip()
    if s == "":
        return 0.0, True
    try:
        return float(s), False
    except ValueError:
        return 0.0, True


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _record_key(row: dict[str, str]) -> str:
    asin = _normalize(row.get("asin", ""))
    if asin:
        return f"asin::{asin}"
    isbn = _normalize(row.get("isbn", ""))
    if isbn:
        return f"isbn::{isbn}"
    title = _normalize(row.get("title", ""))
    author = _normalize(row.get("author", ""))
    return f"title_author::{title}::{author}"


def _duplicate_counter(rows: list[dict[str, str]]) -> Counter[str]:
    c: Counter[str] = Counter()
    for row in rows:
        c[_record_key(row)] += 1
    return c


def _review_bucket(row: dict[str, str], is_duplicate: bool, low_threshold: float) -> str:
    if is_duplicate:
        return "duplicate_review"

    title = (row.get("title") or "").strip()
    author = (row.get("author") or "").strip()
    if not title or not author:
        return "blocked_or_invalid"

    conf, conf_invalid = _to_float(row.get("confidence", ""))
    if conf_invalid:
        return "blocked_or_invalid"
    if conf < low_threshold:
        return "needs_fix"

    asin = (row.get("asin") or "").strip()
    if not asin:
        return "needs_asin_confirmation"

    return "adopt"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _attach_bucket(
    rows: list[dict[str, str]], duplicate_map: Counter[str], low_threshold: float
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _record_key(row)
        dup = duplicate_map.get(key, 0) > 1
        bucket = _review_bucket(row, dup, low_threshold)
        conf, conf_invalid = _to_float(row.get("confidence", ""))
        out.append(
            {
                "key": key,
                "row": row,
                "asin_present": bool((row.get("asin") or "").strip()),
                "confidence_value": conf,
                "confidence_invalid": conf_invalid,
                "review_bucket": bucket,
            }
        )
    return out


def _index_by_key(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["key"]
        if key not in idx:
            idx[key] = item
    return idx


def _diff_updates(
    before_map: dict[str, dict[str, Any]],
    after_map: dict[str, dict[str, Any]],
    compare_columns: list[str],
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    shared_keys = sorted(set(before_map.keys()) & set(after_map.keys()))
    for key in shared_keys:
        before = before_map[key]
        after = after_map[key]

        changed_fields: dict[str, dict[str, Any]] = {}
        for col in compare_columns:
            b = before["row"].get(col, "")
            a = after["row"].get(col, "")
            if b != a:
                changed_fields[col] = {"before": b, "after": a}

        if before["asin_present"] != after["asin_present"]:
            changed_fields["asin_present"] = {
                "before": before["asin_present"],
                "after": after["asin_present"],
            }

        if before["confidence_value"] != after["confidence_value"] or before["confidence_invalid"] != after["confidence_invalid"]:
            changed_fields["confidence"] = {
                "before": before["row"].get("confidence", ""),
                "after": after["row"].get("confidence", ""),
            }

        if before["review_bucket"] != after["review_bucket"]:
            changed_fields["review_bucket"] = {
                "before": before["review_bucket"],
                "after": after["review_bucket"],
            }

        if changed_fields:
            updates.append({"key": key, "changes": changed_fields})

    return updates


def _summarize(
    before_items: list[dict[str, Any]],
    after_items: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    before_dup: Counter[str],
    after_dup: Counter[str],
    adopt_buckets: set[str],
    max_samples: int,
) -> dict[str, Any]:
    before_map = _index_by_key(before_items)
    after_map = _index_by_key(after_items)

    before_keys = set(before_map.keys())
    after_keys = set(after_map.keys())

    added_keys = sorted(after_keys - before_keys)
    removed_keys = sorted(before_keys - after_keys)

    duplicate_keys_before = sorted([k for k, v in before_dup.items() if v > 1])
    duplicate_keys_after = sorted([k for k, v in after_dup.items() if v > 1])

    before_asin_present = sum(1 for i in before_items if i["asin_present"])
    after_asin_present = sum(1 for i in after_items if i["asin_present"])

    before_adopt = sum(1 for i in before_items if i["review_bucket"] in adopt_buckets)
    after_adopt = sum(1 for i in after_items if i["review_bucket"] in adopt_buckets)

    bucket_counter_before = Counter([i["review_bucket"] for i in before_items])
    bucket_counter_after = Counter([i["review_bucket"] for i in after_items])

    return {
        "added_candidates": {
            "count": len(added_keys),
            "samples": added_keys[:max_samples],
        },
        "removed_candidates": {
            "count": len(removed_keys),
            "samples": removed_keys[:max_samples],
        },
        "updated_candidates": {
            "count": len(updates),
            "samples": updates[:max_samples],
        },
        "duplicate_candidates": {
            "before_count": len(duplicate_keys_before),
            "after_count": len(duplicate_keys_after),
            "introduced": sorted(set(duplicate_keys_after) - set(duplicate_keys_before))[:max_samples],
            "resolved": sorted(set(duplicate_keys_before) - set(duplicate_keys_after))[:max_samples],
        },
        "asin_presence_change": {
            "before_asin_present": before_asin_present,
            "after_asin_present": after_asin_present,
            "delta": after_asin_present - before_asin_present,
        },
        "confidence_change": {
            "updated_confidence_rows": sum(1 for u in updates if "confidence" in u["changes"]),
        },
        "review_bucket_change": {
            "updated_review_bucket_rows": sum(1 for u in updates if "review_bucket" in u["changes"]),
            "before_distribution": dict(bucket_counter_before),
            "after_distribution": dict(bucket_counter_after),
        },
        "adopt_candidate_count_change": {
            "before": before_adopt,
            "after": after_adopt,
            "delta": after_adopt - before_adopt,
        },
    }


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    diff = result["diff"]
    lines = [
        "# SFB-13 CSV Import Diff Report",
        "",
        f"- status: {result['status']}",
        f"- phase: {result['phase']}",
        f"- mode: {result['mode']}",
        f"- production_status: {result['production_status']}",
        "",
        "## Summary",
        f"- added_candidates: {diff['added_candidates']['count']}",
        f"- removed_candidates: {diff['removed_candidates']['count']}",
        f"- updated_candidates: {diff['updated_candidates']['count']}",
        f"- duplicate_before: {diff['duplicate_candidates']['before_count']}",
        f"- duplicate_after: {diff['duplicate_candidates']['after_count']}",
        f"- asin_present_delta: {diff['asin_presence_change']['delta']}",
        f"- confidence_updated_rows: {diff['confidence_change']['updated_confidence_rows']}",
        f"- review_bucket_updated_rows: {diff['review_bucket_change']['updated_review_bucket_rows']}",
        f"- adopt_candidate_delta: {diff['adopt_candidate_count_change']['delta']}",
        "",
        "## Safety",
        f"- wordpress_write_executed: {str(result['wordpress_write_executed']).lower()}",
        f"- external_api_called: {str(result['external_api_called']).lower()}",
        f"- external_network_called: {str(result['external_network_called']).lower()}",
        f"- approval_token_consumed: {str(result['approval_token_consumed']).lower()}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(policy_path: Path) -> dict[str, Any]:
    policy = _read_json(policy_path)

    before_csv = ROOT / policy["input_paths"]["before_csv"]
    after_csv = ROOT / policy["input_paths"]["after_csv"]
    out_json = ROOT / policy["output_paths"]["report_json"]
    out_md = ROOT / policy["output_paths"]["report_md"]
    compare_columns = list(policy.get("compare_columns", []))
    low_threshold = float(policy.get("confidence_thresholds", {}).get("low", 0.7))
    adopt_buckets = set(policy.get("adopt_review_buckets", ["adopt"]))
    max_samples = int(policy.get("max_detail_samples", 20))

    result: dict[str, Any] = {
        "phase": "SFB-13",
        "phase_name": "CSV Import Diff Report Enhancement",
        "checked_at": _now_iso(),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "external_api_called": False,
        "external_network_called": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "human_approval_consumed": False,
        "status": "SFB13_CSV_IMPORT_DIFF_REPORT_READY",
        "inputs": {
            "before_csv": str(before_csv),
            "after_csv": str(after_csv),
            "policy_path": str(policy_path),
        },
        "fail_list": [],
        "warn_list": [],
        "diff": {},
    }

    if not before_csv.exists() or not after_csv.exists():
        result["status"] = "SFB13_CSV_IMPORT_DIFF_REPORT_BLOCKED"
        if not before_csv.exists():
            result["fail_list"].append(f"before_csv_missing: {before_csv}")
        if not after_csv.exists():
            result["fail_list"].append(f"after_csv_missing: {after_csv}")
    else:
        before_rows = _load_csv_rows(before_csv)
        after_rows = _load_csv_rows(after_csv)

        before_dup = _duplicate_counter(before_rows)
        after_dup = _duplicate_counter(after_rows)

        before_items = _attach_bucket(before_rows, before_dup, low_threshold)
        after_items = _attach_bucket(after_rows, after_dup, low_threshold)

        before_map = _index_by_key(before_items)
        after_map = _index_by_key(after_items)
        updates = _diff_updates(before_map, after_map, compare_columns)

        result["diff"] = _summarize(
            before_items=before_items,
            after_items=after_items,
            updates=updates,
            before_dup=before_dup,
            after_dup=after_dup,
            adopt_buckets=adopt_buckets,
            max_samples=max_samples,
        )

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(result, out_md)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="policy json path")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = ROOT / policy_path

    result = generate(policy_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "SFB13_CSV_IMPORT_DIFF_REPORT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
