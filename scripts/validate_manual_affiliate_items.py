#!/usr/bin/env python3
"""Validate Phase 8-50 manual affiliate items."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.example.json"
DEFAULT_POLICY = ROOT / "manual_affiliate_builder" / "schema_policy.json"

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file_not_found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_json: {path}: {exc}")


def is_amazon_jp_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False

    host = parsed.netloc.lower()
    return parsed.scheme in {"http", "https"} and (
        host == "www.amazon.co.jp"
        or host == "amazon.co.jp"
        or host.endswith(".amazon.co.jp")
    )


def validate(data: Dict[str, Any], policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if data.get("phase") != "Phase 8-50-MANUAL":
        errors.append("top_level.phase must be Phase 8-50-MANUAL")

    if data.get("execution_mode") != "DRY_RUN_ONLY":
        errors.append("top_level.execution_mode must be DRY_RUN_ONLY")

    if data.get("amazon_api_call_allowed") is not False:
        errors.append("top_level.amazon_api_call_allowed must be false")

    if data.get("wordpress_write_allowed") is not False:
        errors.append("top_level.wordpress_write_allowed must be false")

    if data.get("production_status") != "NO_GO":
        errors.append("top_level.production_status must be NO_GO")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty list")
        return False, errors

    required_fields = policy.get("required_item_fields", [])
    allowed_source_modes = set(policy.get("allowed_source_modes", []))
    allowed_migration_statuses = set(policy.get("allowed_migration_statuses", []))

    seen_asins = set()

    for index, item in enumerate(items):
        prefix = f"items[{index}]"

        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        for field in required_fields:
            if field not in item:
                errors.append(f"{prefix}.{field} is required")
            elif isinstance(item[field], str) and not item[field].strip():
                errors.append(f"{prefix}.{field} must not be empty")

        asin = item.get("asin")
        if isinstance(asin, str):
            asin = asin.strip().upper()
            if not ASIN_RE.match(asin):
                errors.append(f"{prefix}.asin must be 10 uppercase alphanumeric characters")
            if asin in seen_asins:
                errors.append(f"{prefix}.asin is duplicated: {asin}")
            seen_asins.add(asin)

            expected_canonical = f"amazon_jp:{asin}"
            if item.get("canonical_item_id") != expected_canonical:
                errors.append(f"{prefix}.canonical_item_id must be {expected_canonical}")

        source_mode = item.get("source_mode")
        if source_mode not in allowed_source_modes:
            errors.append(f"{prefix}.source_mode must be one of {sorted(allowed_source_modes)}")

        migration_status = item.get("migration_status")
        if migration_status not in allowed_migration_statuses:
            errors.append(
                f"{prefix}.migration_status must be one of {sorted(allowed_migration_statuses)}"
            )

        url = item.get("manual_affiliate_url")
        if isinstance(url, str):
            if not is_amazon_jp_url(url):
                errors.append(f"{prefix}.manual_affiliate_url must be an amazon.co.jp URL")
            if "tag=" not in url:
                errors.append(f"{prefix}.manual_affiliate_url should include affiliate tag parameter")

        api_verified = item.get("api_verified")
        if api_verified is not False:
            errors.append(f"{prefix}.api_verified must be false in Phase 8-50")

    return len(errors) == 0, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Phase 8-50 manual affiliate item master."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to manual affiliate items JSON.",
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY),
        help="Path to schema policy JSON.",
    )
    args = parser.parse_args()

    try:
        data = load_json(Path(args.input))
        policy = load_json(Path(args.policy))
        ok, errors = validate(data, policy)
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "phase": "Phase 8-50-MANUAL",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    result = {
        "status": "PASS" if ok else "FAIL",
        "phase": "Phase 8-50-MANUAL",
        "execution_mode": "DRY_RUN_ONLY",
        "amazon_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "production_status": "NO_GO",
        "errors": errors,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
