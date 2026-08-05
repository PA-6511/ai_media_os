"""
affiliate_practical_schema.py — IR8

affiliate_block の実データ風 DRY_RUN 用スキーマ定義とバリデータ。
外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

from dataclasses import dataclass, field
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

REQUIRED_OUTPUT_FIELDS = [
    "article_candidate",
    "review_required",
    "affiliate_disclosure",
    "blocked_reason",
    "risk_flags",
]

ALLOWED_BLOCKED_REASONS = {
    None,
    "UNKNOWN",
    "POLICY_VIOLATION",
    "LEGAL_RESTRICTED",
    "HIGH_RISK_SCORE",
    "MISSING_DISCLOSURE",
    "INVALID_URL",
}

RISK_FLAG_WEIGHTS = {
    "price_volatility": 15,
    "stock_unstable": 20,
    "promotion_expiring": 20,
    "content_quality_low": 35,
    "compliance_risk": 60,
    "legal_risk": 90,
    "policy_violation": 100,
}

HARD_ABORT_FLAGS = {"policy_violation", "legal_risk"}


@dataclass
class SchemaValidationResult:
    result: str  # PASS | WARN | FAIL
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CandidateQualityGateResult:
    status: str  # PASS | WARN | FAIL | ABORT
    summary: dict[str, Any]
    items: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_affiliate_input_records(records: list[dict[str, Any]]) -> SchemaValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            failed.append(f"records[{i}] must be an object")
            continue
        for field in REQUIRED_INPUT_FIELDS:
            if field not in rec:
                failed.append(f"records[{i}].{field} is required")
        if "risk_flags" in rec and not isinstance(rec.get("risk_flags"), list):
            failed.append(f"records[{i}].risk_flags must be a list")
        url = str(rec.get("url", ""))
        if url and not url.startswith(("http://", "https://")):
            failed.append(f"records[{i}].url must start with http:// or https://")
        asin = str(rec.get("asin", ""))
        if asin and len(asin.strip()) < 4:
            warns.append(f"records[{i}].asin looks too short")

    if failed:
        return SchemaValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return SchemaValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return SchemaValidationResult(result="PASS")


def validate_affiliate_candidate_outputs(candidates: list[dict[str, Any]]) -> SchemaValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    for i, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            failed.append(f"candidates[{i}] must be an object")
            continue
        for field in REQUIRED_OUTPUT_FIELDS:
            if field not in cand:
                failed.append(f"candidates[{i}].{field} is required")
        article_candidate = cand.get("article_candidate")
        if article_candidate is not None and not isinstance(article_candidate, dict):
            failed.append(f"candidates[{i}].article_candidate must be an object")
        if "review_required" in cand and not isinstance(cand.get("review_required"), bool):
            failed.append(f"candidates[{i}].review_required must be bool")
        if "risk_flags" in cand and not isinstance(cand.get("risk_flags"), list):
            failed.append(f"candidates[{i}].risk_flags must be list")
        disclosure = str(cand.get("affiliate_disclosure", ""))
        if disclosure and "affiliate" not in disclosure.lower():
            warns.append(f"candidates[{i}].affiliate_disclosure may be insufficient")

    if failed:
        return SchemaValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return SchemaValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return SchemaValidationResult(result="PASS")


def evaluate_affiliate_candidate_quality(candidates: list[dict[str, Any]]) -> CandidateQualityGateResult:
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "ABORT": 0}

    for idx, candidate in enumerate(candidates):
        risk_flags_raw = candidate.get("risk_flags", []) if isinstance(candidate, dict) else []
        risk_flags = risk_flags_raw if isinstance(risk_flags_raw, list) else []
        review_required = bool(candidate.get("review_required", False)) if isinstance(candidate, dict) else True
        disclosure = str(candidate.get("affiliate_disclosure", "")) if isinstance(candidate, dict) else ""
        blocked_reason = candidate.get("blocked_reason") if isinstance(candidate, dict) else None

        if blocked_reason not in ALLOWED_BLOCKED_REASONS:
            warnings.append(f"candidates[{idx}].blocked_reason is unknown: {blocked_reason!r}")
            blocked_reason = "UNKNOWN"

        score = 100
        total_risk_weight = 0
        for flag in risk_flags:
            weight = RISK_FLAG_WEIGHTS.get(str(flag), 25)
            total_risk_weight += weight
            if str(flag) not in RISK_FLAG_WEIGHTS:
                warnings.append(f"candidates[{idx}] unknown risk_flag={flag!r}; default weight=25")
        score -= total_risk_weight

        if review_required:
            score -= 15
        if disclosure and "affiliate" not in disclosure.lower():
            score -= 25
            if blocked_reason in {None, "UNKNOWN"}:
                blocked_reason = "MISSING_DISCLOSURE"

        if blocked_reason not in {None, "UNKNOWN"}:
            score -= 40

        if any(str(flag) in HARD_ABORT_FLAGS for flag in risk_flags):
            blocked_reason = "POLICY_VIOLATION" if "policy_violation" in risk_flags else "LEGAL_RESTRICTED"

        score = max(0, min(100, score))

        if blocked_reason in {"POLICY_VIOLATION", "LEGAL_RESTRICTED"}:
            decision = "ABORT"
        elif blocked_reason == "HIGH_RISK_SCORE" or score < 40:
            decision = "FAIL"
        elif score < 75 or review_required or blocked_reason not in {None, "UNKNOWN"}:
            decision = "WARN"
        else:
            decision = "PASS"

        counts[decision] += 1
        items.append(
            {
                "index": idx,
                "quality_score": score,
                "risk_weight_total": total_risk_weight,
                "risk_flags": risk_flags,
                "review_required": review_required,
                "blocked_reason": blocked_reason,
                "decision": decision,
            }
        )

    if counts["ABORT"] > 0:
        overall = "ABORT"
    elif counts["FAIL"] > 0:
        overall = "FAIL"
    elif counts["WARN"] > 0:
        overall = "WARN"
    else:
        overall = "PASS"

    summary = {
        "overall_status": overall,
        "candidate_count": len(items),
        "pass_count": counts["PASS"],
        "warn_count": counts["WARN"],
        "fail_count": counts["FAIL"],
        "abort_count": counts["ABORT"],
    }
    return CandidateQualityGateResult(status=overall, summary=summary, items=items, warnings=warnings)
