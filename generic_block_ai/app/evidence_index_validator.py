"""
evidence_index_validator.py  –  Phase 3.5-16

evidence index JSON の安全制約を検証します。
外部転送・自動 export・証跡削除は一切行いません。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_FORBIDDEN_ACTIONS = {
    "auto_upload_to_external",
    "overwrite_existing_evidence",
    "delete_evidence",
    "export_without_approval",
}
FORBIDDEN_ENTRY_STATUSES = {"deleted", "overwritten"}


@dataclass
class ValidationResult:
    result: str  # "PASS" | "WARN" | "FAIL"
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_evidence_index(data: dict[str, Any]) -> ValidationResult:
    """
    evidence index dict を検証し ValidationResult を返す。
    外部 I/O・自動 export・証跡削除は行わない。
    """
    failed: list[str] = []
    warns: list[str] = []

    meta = data.get("index_metadata", {})
    export_policy = data.get("export_policy", {})
    entries = data.get("entries", [])

    # --- REJECT conditions ---
    if meta.get("mode") != "dry_run":
        failed.append("index_metadata.mode must be dry_run")

    if meta.get("operation_mode") != "OBSERVE":
        failed.append("index_metadata.operation_mode must be OBSERVE")

    if meta.get("auto_export_allowed") is not False:
        failed.append("index_metadata.auto_export_allowed must be false")

    if meta.get("requires_human_approval") is not True:
        failed.append("index_metadata.requires_human_approval must be true")

    if export_policy.get("auto_export") is not False:
        failed.append("export_policy.auto_export must be false")

    if meta.get("mode") in {"live", "production", "execute"}:
        failed.append(f"index_metadata.mode '{meta.get('mode')}' is forbidden")

    if meta.get("operation_mode") in {"EXECUTE", "WRITE", "PUBLISH"}:
        failed.append(f"index_metadata.operation_mode '{meta.get('operation_mode')}' is forbidden")

    # entries に forbidden status が存在する場合は FAIL
    for i, entry in enumerate(entries):
        entry_status = entry.get("status", "")
        if entry_status in FORBIDDEN_ENTRY_STATUSES:
            failed.append(f"entries[{i}].status '{entry_status}' is forbidden")

    # --- WARN conditions ---
    allowed_destinations = export_policy.get("allowed_destinations", [])
    if allowed_destinations:
        warns.append(
            f"export_policy.allowed_destinations is non-empty ({allowed_destinations}) — prior approval required"
        )

    forbidden_actions = set(export_policy.get("forbidden_actions", []))
    missing = REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions
    if missing:
        warns.append(f"export_policy.forbidden_actions is missing required entries: {sorted(missing)}")

    if failed:
        return ValidationResult(result="FAIL", failed_checks=failed, warnings=warns)
    if warns:
        return ValidationResult(result="WARN", failed_checks=failed, warnings=warns)
    return ValidationResult(result="PASS")
