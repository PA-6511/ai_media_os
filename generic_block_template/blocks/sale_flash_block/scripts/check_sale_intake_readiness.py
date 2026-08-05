#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BLOCK_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BLOCK_DIR / "config"
FIXTURE_CSV = BLOCK_DIR / "fixtures/sample_sale_candidates.csv"
LOG_DIR = BLOCK_DIR / "logs"
OUTPUT_JSON = LOG_DIR / "sale_intake_readiness.json"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_readiness(output_json: Path = OUTPUT_JSON) -> Dict[str, Any]:
    intake_policy_path = CONFIG_DIR / "intake_policy.json"
    source_registry_path = CONFIG_DIR / "source_registry.json"
    migration_policy_path = CONFIG_DIR / "migration_policy.json"
    normalized_path = LOG_DIR / "normalized_sale_candidates.json"
    review_queue_path = LOG_DIR / "sale_review_queue.json"

    checks: Dict[str, bool] = {
        "intake_policy_exists": intake_policy_path.exists(),
        "source_registry_exists": source_registry_path.exists(),
        "migration_policy_exists": migration_policy_path.exists(),
        "sample_fixture_exists": FIXTURE_CSV.exists(),
        "normalized_sale_candidates_exists": normalized_path.exists(),
        "sale_review_queue_exists": review_queue_path.exists(),
        "production_status_is_no_go": False,
        "external_api_called_is_false": False,
        "external_network_called_is_false": False,
        "wordpress_write_executed_is_false": False,
        "creators_api_allowed_is_false": False,
        "amazon_scraping_allowed_is_false": False,
    }

    status = "PASS"
    errors = []

    try:
        intake_policy = _read_json(intake_policy_path) if intake_policy_path.exists() else {}
        source_registry = _read_json(source_registry_path) if source_registry_path.exists() else {}
        migration_policy = _read_json(migration_policy_path) if migration_policy_path.exists() else {}
        normalized = _read_json(normalized_path) if normalized_path.exists() else {}
        queue = _read_json(review_queue_path) if review_queue_path.exists() else {}

        checks["production_status_is_no_go"] = (
            intake_policy.get("production_status") == "NO_GO"
            and normalized.get("production_status") == "NO_GO"
            and queue.get("production_status") == "NO_GO"
        )
        checks["external_api_called_is_false"] = (
            normalized.get("external_api_called") is False
            and queue.get("external_api_called") is False
        )
        checks["external_network_called_is_false"] = (
            normalized.get("external_network_called") is False
            and queue.get("external_network_called") is False
        )
        checks["wordpress_write_executed_is_false"] = (
            normalized.get("wordpress_write_executed") is False
            and queue.get("wordpress_write_executed") is False
        )
        checks["creators_api_allowed_is_false"] = intake_policy.get("creators_api_allowed") is False
        checks["amazon_scraping_allowed_is_false"] = intake_policy.get("amazon_scraping_allowed") is False

        creators_placeholder = source_registry.get("adapters", {}).get("creators_api_placeholder", {})
        if creators_placeholder.get("enabled") is not False:
            checks["creators_api_allowed_is_false"] = False

        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            status = "FAIL"
            errors.extend([f"failed check: {name}" for name in failed])

    except Exception as exc:
        status = "FAIL"
        errors.append(str(exc))

    payload: Dict[str, Any] = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_status": "NO_GO",
        "external_api_called": False,
        "external_network_called": False,
        "wordpress_write_executed": False,
        "checks": checks,
        "errors": errors,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    result = check_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
