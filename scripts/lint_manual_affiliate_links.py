#!/usr/bin/env python3
"""Lint manual affiliate item links and identifiers for Phase 8-50B."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.example.json"
DEFAULT_MIGRATION_POLICY = ROOT / "manual_affiliate_builder" / "migration_policy.json"

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
URL_ASIN_RE = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_amazon_jp(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return parsed.scheme in {"http", "https"} and (
        host == "amazon.co.jp" or host == "www.amazon.co.jp" or host.endswith(".amazon.co.jp")
    )


def _extract_url_asin(url: str) -> str | None:
    match = URL_ASIN_RE.search(url)
    if not match:
        return None
    return match.group(1).upper()


def lint_items(data: Dict[str, Any], migration_policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return False, ["items must be a non-empty list"]

    allowed_migration_statuses = set(migration_policy.get("allowed_migration_statuses", []))

    seen_asin = set()
    seen_url = set()

    for i, item in enumerate(items):
        prefix = f"items[{i}]"
        asin = str(item.get("asin", "")).strip().upper()
        canonical = str(item.get("canonical_item_id", "")).strip()
        url = str(item.get("manual_affiliate_url", "")).strip()

        if not ASIN_RE.match(asin):
            errors.append(f"{prefix}.asin must be 10 uppercase alphanumeric characters")

        expected_canonical = f"amazon_jp:{asin}"
        if canonical != expected_canonical:
            errors.append(f"{prefix}.canonical_item_id must be {expected_canonical}")

        if not _is_amazon_jp(url):
            errors.append(f"{prefix}.manual_affiliate_url must be amazon.co.jp domain")

        parsed = urlparse(url)
        tags = parse_qs(parsed.query).get("tag", [])
        if not tags or not str(tags[0]).strip():
            errors.append(f"{prefix}.manual_affiliate_url must include non-empty tag parameter")

        url_asin = _extract_url_asin(url)
        if url_asin and url_asin != asin:
            errors.append(f"{prefix}.asin mismatch between item and URL path ASIN")

        if asin in seen_asin:
            errors.append(f"{prefix}.asin duplicated: {asin}")
        seen_asin.add(asin)

        if url in seen_url:
            errors.append(f"{prefix}.manual_affiliate_url duplicated")
        seen_url.add(url)

        if item.get("source_mode") != "manual":
            errors.append(f"{prefix}.source_mode must be manual")

        migration_status = item.get("migration_status")
        if migration_status not in allowed_migration_statuses:
            errors.append(
                f"{prefix}.migration_status must be one of {sorted(allowed_migration_statuses)}"
            )

        if item.get("api_verified") is not False:
            errors.append(f"{prefix}.api_verified must be false in Phase 8-50B")

    return len(errors) == 0, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint manual affiliate links and identifiers")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input manual item JSON")
    parser.add_argument(
        "--migration-policy",
        default=str(DEFAULT_MIGRATION_POLICY),
        help="Migration policy JSON",
    )
    args = parser.parse_args()

    try:
        data = load_json(Path(args.input))
        migration_policy = load_json(Path(args.migration_policy))
        ok, errors = lint_items(data, migration_policy)
        print(
            json.dumps(
                {
                    "status": "PASS" if ok else "FAIL",
                    "phase": "Phase 8-50B",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "amazon_api_call_allowed": False,
                    "wordpress_write_allowed": False,
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if ok else 1
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
