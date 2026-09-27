from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from analytics.x_core_advisory.contract import (
    REPORT_TYPES,
    XCoreAdvisoryContractError,
    strict_load_json,
    validate_advisory_snapshot,
    validate_manifest,
)
from analytics.x_core_advisory.store import DEFAULT_EXPORT_ROOT


class XAnalyticsAdvisoryReader:
    """Core-side read-only consumer; freshness is recalculated per read."""

    def __init__(self, root: Path = DEFAULT_EXPORT_ROOT) -> None:
        self.root = root.resolve()
        self.manifest_path = self.root / "manifest.json"

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise XCoreAdvisoryContractError(
                "manifest snapshot path escapes export root"
            ) from exc
        return candidate

    def _manifest(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if (self.root / "DISABLED").exists():
            return None, {
                "status": "DISABLED",
                "reason": "runtime_disable_marker_present",
                "path": str(self.root / "DISABLED"),
            }
        if not self.manifest_path.is_file():
            return None, {
                "status": "MISSING",
                "reason": "manifest_not_generated",
                "path": str(self.manifest_path),
            }
        try:
            manifest = strict_load_json(self.manifest_path)
            validate_manifest(manifest)
            return manifest, None
        except XCoreAdvisoryContractError as exc:
            return None, {
                "status": "CORRUPT",
                "reason": "manifest_invalid",
                "detail": str(exc),
                "path": str(self.manifest_path),
            }

    def _read_reference(
        self,
        reference: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        try:
            path = self._safe_path(str(reference.get("path", "")))
        except XCoreAdvisoryContractError as exc:
            return {"status": "CORRUPT", "reason": "unsafe_snapshot_path", "detail": str(exc)}
        if not path.is_file():
            return {
                "status": "MISSING",
                "reason": "snapshot_file_missing",
                "snapshot_id": reference.get("snapshot_id"),
            }
        content = path.read_bytes()
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != reference.get("sha256"):
            return {
                "status": "CORRUPT",
                "reason": "snapshot_sha256_mismatch",
                "snapshot_id": reference.get("snapshot_id"),
            }
        try:
            snapshot = strict_load_json(path)
            validate_advisory_snapshot(snapshot)
        except XCoreAdvisoryContractError as exc:
            return {
                "status": "CORRUPT",
                "reason": "snapshot_schema_invalid",
                "detail": str(exc),
                "snapshot_id": reference.get("snapshot_id"),
            }
        if snapshot.get("snapshot_id") != reference.get("snapshot_id"):
            return {
                "status": "CORRUPT",
                "reason": "snapshot_identity_mismatch",
                "snapshot_id": reference.get("snapshot_id"),
            }
        if snapshot.get("report_type") != reference.get("report_type"):
            return {
                "status": "CORRUPT",
                "reason": "snapshot_report_type_mismatch",
                "snapshot_id": reference.get("snapshot_id"),
            }
        freshness = snapshot["freshness"]
        as_of = datetime.fromisoformat(str(snapshot["as_of"]).replace("Z", "+00:00"))
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age_seconds = max(0, int((current - as_of.astimezone(timezone.utc)).total_seconds()))
        max_age_seconds = int(freshness.get("max_age_seconds", 0))
        status = "OK" if age_seconds <= max_age_seconds else "STALE"
        return {
            "status": status,
            "reason": None if status == "OK" else "snapshot_stale",
            "snapshot_id": snapshot["snapshot_id"],
            "report_type": snapshot["report_type"],
            "freshness": {
                **freshness,
                "status": status.lower(),
                "age_seconds": age_seconds,
                "checked_at": current.isoformat(),
            },
            "snapshot": snapshot,
        }

    def get_latest(
        self, report_type: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        if report_type not in REPORT_TYPES:
            return {"status": "INVALID_REQUEST", "reason": "unsupported_report_type"}
        manifest, error = self._manifest()
        if error is not None:
            return error
        assert manifest is not None
        reference = manifest["latest"].get(report_type)
        if reference is None:
            return {
                "status": "MISSING",
                "reason": f"latest_{report_type}_not_generated",
            }
        return self._read_reference(reference, now=now)

    def get_snapshot(
        self, snapshot_id: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        manifest, error = self._manifest()
        if error is not None:
            return error
        assert manifest is not None
        for reference in manifest["snapshots"]:
            if reference.get("snapshot_id") == snapshot_id:
                return self._read_reference(reference, now=now)
        return {
            "status": "MISSING",
            "reason": "snapshot_id_not_found",
            "snapshot_id": snapshot_id,
        }

    def get_latest_x_kpi_summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        return self.get_latest("x_kpi_summary", now=now)

    def get_latest_weekly(self, *, now: datetime | None = None) -> dict[str, Any]:
        return self.get_latest("weekly", now=now)

    def get_latest_monthly(self, *, now: datetime | None = None) -> dict[str, Any]:
        return self.get_latest("monthly", now=now)