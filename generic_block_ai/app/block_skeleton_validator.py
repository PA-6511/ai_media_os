"""
block_skeleton_validator.py — IR5-T3

build_block_skeleton() の出力を検証します。
外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .block_template_builder import BUILDER_SCHEMA_VERSION
from .block_template_spec import (
    AFFILIATE_ALLOWED_PRODUCT_SOURCES,
    AFFILIATE_REQUIRED_DISCLAIMER,
    ALLOWED_CATEGORIES,
    ALLOWED_RISK_LEVELS,
    _BASE_FORBIDDEN_ACTIONS,
)

REQUIRED_FILE_PATHS = {
    "block_manifest.json",
    "config/policy.json",
    "app/__init__.py",
    "app/schemas.py",
    "app/runner.py",
    "README.md",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_manifest.py",
    "tests/test_schemas.py",
    "tests/test_runner.py",
}


@dataclass
class SkeletonValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _parse_manifest(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    for f in files:
        if f.get("path") == "block_manifest.json":
            try:
                return json.loads(f["content"])
            except Exception:
                return None
    return None


def _parse_policy(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    for f in files:
        if f.get("path") == "config/policy.json":
            try:
                return json.loads(f["content"])
            except Exception:
                return None
    return None


def validate_block_skeleton(skeleton: dict[str, Any]) -> SkeletonValidationResult:
    failed: list[str] = []
    warns: list[str] = []

    # --- _meta ---
    meta = skeleton.get("_meta", {})
    if meta.get("schema_version") != BUILDER_SCHEMA_VERSION:
        failed.append(f"_meta.schema_version must be {BUILDER_SCHEMA_VERSION}")
    if meta.get("status") != "OK":
        failed.append(f"_meta.status must be OK (got {meta.get('status')!r})")

    # --- safeguards ---
    safeguards = skeleton.get("safeguards", {})
    if safeguards.get("external_write_executed") is not False:
        failed.append("safeguards.external_write_executed must be false")
    if safeguards.get("actual_auto_execute") is not False:
        failed.append("safeguards.actual_auto_execute must be false")
    if safeguards.get("mode") != "dry_run":
        failed.append("safeguards.mode must be dry_run")
    if safeguards.get("operation_mode") != "OBSERVE":
        failed.append("safeguards.operation_mode must be OBSERVE")

    # --- files presence ---
    files: list[dict[str, Any]] = skeleton.get("files", [])
    present_paths = {str(f.get("path", "")) for f in files}
    for required in REQUIRED_FILE_PATHS:
        if required not in present_paths:
            failed.append(f"required file missing: {required}")

    # --- manifest content ---
    manifest = _parse_manifest(files)
    if manifest is None:
        failed.append("block_manifest.json is missing or invalid JSON")
    else:
        if manifest.get("mode") != "dry_run":
            failed.append("manifest.mode must be dry_run")
        if manifest.get("operation_mode") != "OBSERVE":
            failed.append("manifest.operation_mode must be OBSERVE")
        approval = manifest.get("approval_policy", {})
        if approval.get("requires_human_approval") is not True:
            failed.append("manifest.approval_policy.requires_human_approval must be true")
        if approval.get("auto_execute_allowed") is not False:
            failed.append("manifest.approval_policy.auto_execute_allowed must be false")
        if manifest.get("risk_level") not in ALLOWED_RISK_LEVELS:
            failed.append(f"manifest.risk_level must be one of {sorted(ALLOWED_RISK_LEVELS)}")
        if manifest.get("category") not in ALLOWED_CATEGORIES:
            warns.append(f"manifest.category {manifest.get('category')!r} is not in ALLOWED_CATEGORIES")
        for base_action in _BASE_FORBIDDEN_ACTIONS:
            if base_action not in manifest.get("forbidden_actions", []):
                failed.append(f"manifest.forbidden_actions must include {base_action!r}")

    # --- policy content ---
    policy = _parse_policy(files)
    if policy is None:
        failed.append("config/policy.json is missing or invalid JSON")
    else:
        if policy.get("observe_only") is not True:
            failed.append("policy.observe_only must be true")
        if "forbidden_actions" not in policy:
            failed.append("policy.forbidden_actions is required")
        if "quality_metrics" not in policy:
            warns.append("policy.quality_metrics is not set")
        if "review_decision" not in policy:
            warns.append("policy.review_decision is not set")
        pm = policy.get("policy_metadata", {})
        if not pm.get("version"):
            warns.append("policy.policy_metadata.version is not set")

    # --- affiliate-specific hardening checks ---
    category = manifest.get("category") if manifest else None
    if category == "affiliate":
        if manifest is None:
            failed.append("affiliate manifest checks require valid block_manifest.json")
        else:
            affiliate_safety = manifest.get("affiliate_safety", {})
            if affiliate_safety.get("require_disclosure") is not True:
                failed.append("manifest.affiliate_safety.require_disclosure must be true")
            if affiliate_safety.get("allow_external_checkout") is not False:
                failed.append("manifest.affiliate_safety.allow_external_checkout must be false")
            if affiliate_safety.get("allow_pii_storage") is not False:
                failed.append("manifest.affiliate_safety.allow_pii_storage must be false")
            if affiliate_safety.get("disclosure_text") != AFFILIATE_REQUIRED_DISCLAIMER:
                failed.append("manifest.affiliate_safety.disclosure_text is invalid")
            allowed_sources = affiliate_safety.get("allowed_product_sources", [])
            if sorted(allowed_sources) != sorted(AFFILIATE_ALLOWED_PRODUCT_SOURCES):
                failed.append("manifest.affiliate_safety.allowed_product_sources is invalid")

        if policy is None:
            failed.append("affiliate policy checks require valid config/policy.json")
        else:
            guardrails = policy.get("affiliate_guardrails", {})
            if guardrails.get("allow_external_checkout") is not False:
                failed.append("policy.affiliate_guardrails.allow_external_checkout must be false")
            if guardrails.get("allow_pii_storage") is not False:
                failed.append("policy.affiliate_guardrails.allow_pii_storage must be false")
            if guardrails.get("allow_direct_purchase") is not False:
                failed.append("policy.affiliate_guardrails.allow_direct_purchase must be false")
            if guardrails.get("required_disclosure_text") != AFFILIATE_REQUIRED_DISCLAIMER:
                failed.append("policy.affiliate_guardrails.required_disclosure_text is invalid")
            if guardrails.get("require_manual_review_before_publish") is not True:
                failed.append(
                    "policy.affiliate_guardrails.require_manual_review_before_publish must be true"
                )

    if failed:
        return SkeletonValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return SkeletonValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return SkeletonValidationResult(result="PASS")
