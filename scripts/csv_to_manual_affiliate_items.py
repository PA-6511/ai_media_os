#!/usr/bin/env python3
"""Convert manual affiliate CSV into Phase 8-50 manual items JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.csv.example"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase8_50b_manual_items.from_csv.json"

REQUIRED_HEADERS = {
    "asin",
    "title",
    "author",
    "volume",
    "release_date",
    "manual_affiliate_url",
    "notes",
}


def _normalize_asin(value: str) -> str:
    return value.strip().upper()


def _build_item(row: Dict[str, str]) -> Dict[str, Any]:
    asin = _normalize_asin(row["asin"])
    return {
        "asin": asin,
        "canonical_item_id": f"amazon_jp:{asin}",
        "title": row["title"].strip(),
        "author": row["author"].strip(),
        "volume": row["volume"].strip(),
        "release_date": row["release_date"].strip(),
        "manual_affiliate_url": row["manual_affiliate_url"].strip(),
        "notes": row["notes"].strip(),
        "phase": "Phase 8-50-MANUAL",
        "source_mode": "manual",
        "migration_status": "manual_active",
        "api_verified": False,
        "human_review_status": "pending",
        "wordpress_status": "not_created",
    }


def convert_csv_to_data(input_path: Path) -> Dict[str, Any]:
    if not input_path.exists():
        raise ValueError(f"input_file_not_found: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_HEADERS - fieldnames)
        if missing:
            raise ValueError(f"missing_required_headers: {missing}")

        items: List[Dict[str, Any]] = []
        for index, row in enumerate(reader):
            if not row:
                continue
            if not any((row.get(h) or "").strip() for h in REQUIRED_HEADERS):
                continue
            try:
                items.append(_build_item(row))
            except KeyError as exc:
                raise ValueError(f"row_{index}_missing_field: {exc}")

    if not items:
        raise ValueError("no_items_found_in_csv")

    return {
        "phase": "Phase 8-50-MANUAL",
        "execution_mode": "DRY_RUN_ONLY",
        "amazon_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "publish_allowed": False,
        "approval_token_consumed": False,
        "production_status": "NO_GO",
        "source": {
            "type": "csv",
            "path": str(input_path),
        },
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert CSV to manual affiliate JSON")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input CSV path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    args = parser.parse_args()

    try:
        data = convert_csv_to_data(Path(args.input))
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "phase": "Phase 8-50B",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "amazon_api_call_allowed": False,
                    "wordpress_write_allowed": False,
                    "item_count": len(data["items"]),
                    "output": str(output_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "phase": "Phase 8-50B",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
