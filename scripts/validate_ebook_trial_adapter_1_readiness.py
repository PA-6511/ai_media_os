#!/usr/bin/env python3
"""EBOOK-TRIAL-ADAPTER-1: One Item Trial Preflight Adapter (Readiness-Only).

This validator converts ebook_affiliate_block-like proposal payloads into
preflight readiness checks without enabling execution.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "exchange/examples/ebook_trial_adapter_1_request.example.json"
OUTPUT = ROOT / "exchange/logs/ebook_trial_adapter_1_readiness_result.json"


REQUIRED_BOOL_FLAGS = [
    "target_item_selected",
    "target_item_schema_valid",
    "target_item_duplicate_check_passed",
    "affiliate_disclosure_present",
    "pr_label_present",
    "cta_policy_checked",
    "category_tag_policy_checked",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _extract_flag(candidate: dict[str, Any], key: str) -> bool:
    if key in candidate:
        return _as_bool(candidate.get(key))
    metadata = candidate.get("metadata")
    if isinstance(metadata, dict) and key in metadata:
        return _as_bool(metadata.get(key))
    return False


def validate(
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "phase": "EBOOK-TRIAL-ADAPTER-1",
        "phase_name": "One Item Trial Preflight Adapter Readiness",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "executed_external_changes": 0,
        "checked_at": _now_iso(),
        "warn_list": [],
        "fail_list": [],
        "gap_items": [],
        "ready_items": [],
    }

    try:
        req = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_1_ABORT_INPUT_LOAD_ERROR_NO_EXECUTION",
            "fail_list": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    proposals = req.get("proposals", [])
    if not isinstance(proposals, list):
        proposals = []

    if not proposals:
        result = {
            **base,
            "status": "EBOOK_TRIAL_ADAPTER_1_BLOCKED_NO_CANDIDATE_NO_EXECUTION",
            "candidate_count": 0,
            "fail_list": ["no_candidate"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    candidate = proposals[0] if isinstance(proposals[0], dict) else {}
    selected_title = str(candidate.get("title") or "")

    missing: list[str] = []
    for field in ("title", "target", "reason", "priority"):
        if field not in candidate:
            missing.append(field)

    readiness_flags: dict[str, bool] = {}
    for flag in REQUIRED_BOOL_FLAGS:
        readiness_flags[flag] = _extract_flag(candidate, flag)
        if not readiness_flags[flag]:
            missing.append(flag)

    status = "EBOOK_TRIAL_ADAPTER_1_READY_FOR_PREFLIGHT_CONTRACT_NO_EXECUTION"
    if missing:
        status = "EBOOK_TRIAL_ADAPTER_1_GAP_FOUND_BLOCKED_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "candidate_count": len(proposals),
        "selected_candidate_title": selected_title,
        "ready_items": [k for k, v in readiness_flags.items() if v],
        "gap_items": missing,
        "target_item_selected": readiness_flags["target_item_selected"],
        "target_item_schema_valid": readiness_flags["target_item_schema_valid"],
        "target_item_duplicate_check_passed": readiness_flags["target_item_duplicate_check_passed"],
        "affiliate_disclosure_present": readiness_flags["affiliate_disclosure_present"],
        "pr_label_present": readiness_flags["pr_label_present"],
        "cta_policy_checked": readiness_flags["cta_policy_checked"],
        "category_tag_policy_checked": readiness_flags["category_tag_policy_checked"],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="EBOOK-TRIAL-ADAPTER-1 readiness validator")
    parser.add_argument("--request", default=str(REQUEST), help="Input request json path")
    parser.add_argument("--output", default=str(OUTPUT), help="Output result json path")
    args = parser.parse_args()

    result = validate(request_path=Path(args.request), output_path=Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
