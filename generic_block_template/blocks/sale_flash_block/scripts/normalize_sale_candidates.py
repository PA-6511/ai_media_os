#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BLOCK_DIR = Path(__file__).resolve().parents[1]
FIXTURE_CSV = BLOCK_DIR / "fixtures/sample_sale_candidates.csv"
LOG_DIR = BLOCK_DIR / "logs"
OUTPUT_JSON = LOG_DIR / "normalized_sale_candidates.json"

REQUIRED_COLUMNS = {
    "source",
    "title",
    "author",
    "isbn",
    "asin",
    "campaign",
    "sale_status",
    "confidence",
    "note",
}


def _parse_confidence(raw: str) -> Tuple[Any, List[str]]:
    reasons: List[str] = []
    value = (raw or "").strip()
    if value == "":
        reasons.append("missing_confidence")
        return value, reasons
    try:
        parsed = float(value)
    except ValueError:
        reasons.append("invalid_confidence")
        return value, reasons

    if parsed < 0.6:
        reasons.append("low_confidence")
    return parsed, reasons


def normalize_candidates(input_csv: Path = FIXTURE_CSV, output_json: Path = OUTPUT_JSON) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "input_csv": str(input_csv),
        "item_count": 0,
        "candidates": [],
    }

    try:
        with input_csv.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = set(reader.fieldnames or [])
            missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
            if missing_columns:
                raise ValueError(f"missing required columns: {', '.join(missing_columns)}")

            normalized: List[Dict[str, Any]] = []
            for idx, row in enumerate(reader, start=1):
                title = (row.get("title") or "").strip()
                author = (row.get("author") or "").strip()
                asin = (row.get("asin") or "").strip()

                review_reasons: List[str] = []
                if not title:
                    review_reasons.append("missing_title")
                if not author:
                    review_reasons.append("missing_author")

                confidence, confidence_reasons = _parse_confidence(row.get("confidence") or "")
                review_reasons.extend(confidence_reasons)

                review_required = len(review_reasons) > 0
                link_strategy = "amazon_product_link_candidate" if asin else "amazon_search_link_candidate"

                normalized.append(
                    {
                        "candidate_id": f"sfb-cand-{idx:03d}",
                        "source": (row.get("source") or "").strip(),
                        "title": title,
                        "author": author,
                        "isbn": (row.get("isbn") or "").strip(),
                        "asin": asin,
                        "campaign": (row.get("campaign") or "").strip(),
                        "sale_status": (row.get("sale_status") or "").strip(),
                        "confidence": confidence,
                        "note": (row.get("note") or "").strip(),
                        "normalized_status": "REVIEW_REQUIRED" if review_required else "PASS",
                        "review_required": review_required,
                        "review_reasons": review_reasons,
                        "link_strategy": link_strategy,
                    }
                )

            payload["item_count"] = len(normalized)
            payload["candidates"] = normalized
            payload["status"] = "WARN" if len(normalized) == 0 else "PASS"

    except Exception as exc:
        payload["status"] = "FAIL"
        payload["error"] = str(exc)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    result = normalize_candidates()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
