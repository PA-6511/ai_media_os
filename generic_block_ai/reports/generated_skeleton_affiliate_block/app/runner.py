"""Minimal dry-run runner for generated affiliate block skeleton."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


INPUT_SCHEMA_VERSION = "affiliate_input_v1"
OUTPUT_SCHEMA_VERSION = "affiliate_candidate_v1"
REQUIRED_INPUT_FIELDS = [
    "source",
    "title",
    "asin",
    "url",
    "campaign_type",
    "risk_flags",
]


def _normalize_records(input_payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = input_payload.get("records")
    if isinstance(records, list):
        return [r for r in records if isinstance(r, dict)]

    # Backward-compatible fallback (IR7)
    task_candidates = input_payload.get("task_candidates")
    if isinstance(task_candidates, list):
        normalized: list[dict[str, Any]] = []
        for i, item in enumerate(task_candidates):
            if isinstance(item, dict):
                normalized.append(
                    {
                        "source": str(item.get("source", "generated")),
                        "title": str(item.get("title", f"candidate-{i}")),
                        "asin": str(item.get("asin", f"ASIN{i:04d}")),
                        "url": str(item.get("url", "https://example.invalid/item")),
                        "campaign_type": str(item.get("campaign_type", "standard")),
                        "risk_flags": item.get("risk_flags", []),
                    }
                )
        return normalized
    return []


def _validate_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    for field in REQUIRED_INPUT_FIELDS:
        if field not in record:
            return False, f"missing_field:{field}"
    if not isinstance(record.get("risk_flags"), list):
        return False, "invalid_type:risk_flags"
    if not str(record.get("url", "")).startswith(("http://", "https://")):
        return False, "invalid_url"
    return True, None


def _build_candidate(record: dict[str, Any]) -> dict[str, Any]:
    risk_flags = record.get("risk_flags", [])
    blocked_reason = None
    if "adult" in risk_flags:
        blocked_reason = "risk_flag_adult"
    review_required = bool(risk_flags) or blocked_reason is not None

    return {
        "article_candidate": {
            "title": record.get("title"),
            "summary": f"Affiliate draft for {record.get('title', 'untitled')}",
            "source": record.get("source"),
            "asin": record.get("asin"),
            "url": record.get("url"),
            "campaign_type": record.get("campaign_type"),
        },
        "review_required": review_required,
        "affiliate_disclosure": "This content may include affiliate links.",
        "blocked_reason": blocked_reason,
        "risk_flags": risk_flags,
    }


def run_affiliate_block_dryrun(input_payload: dict[str, Any]) -> dict[str, Any]:
    records = _normalize_records(input_payload)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for rec in records:
        ok, reason = _validate_record(rec)
        if ok:
            accepted.append(rec)
        else:
            rejected.append({"record": rec, "reason": reason})

    selected = accepted[:3]
    candidate_outputs = [_build_candidate(rec) for rec in selected]

    return {
        "status": "success",
        "decision": "human_review",
        "mode": "dry_run",
        "operation_mode": "OBSERVE",
        "input_schema": {
            "version": INPUT_SCHEMA_VERSION,
            "required_fields": list(REQUIRED_INPUT_FIELDS),
        },
        "output_schema": {
            "version": OUTPUT_SCHEMA_VERSION,
            "fields": [
                "article_candidate",
                "review_required",
                "affiliate_disclosure",
                "blocked_reason",
                "risk_flags",
            ],
        },
        "summary": (
            f"dry-run processed records={len(records)}, accepted={len(accepted)}, "
            f"selected={len(selected)}, rejected={len(rejected)}"
        ),
        "recommended_candidates": selected,
        "affiliate_candidates": candidate_outputs,
        "rejected_records": rejected,
        "safeguards": {
            "actual_auto_execute": False,
            "actual_auto_approve": False,
            "external_write_executed": False,
            "production_release": False,
        },
        "meta": {
            "generated_runner": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
