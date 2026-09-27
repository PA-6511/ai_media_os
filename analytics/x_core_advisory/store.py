from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from analytics.x_core_advisory.contract import (
    MANIFEST_SCHEMA_VERSION,
    REPORT_TYPES,
    XCoreAdvisoryContractError,
    strict_load_json,
    validate_advisory_snapshot,
    validate_manifest,
)


DEFAULT_EXPORT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "exchange"
    / "core_advisory"
    / "x_analytics"
)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


class XCoreAdvisoryStore:
    def __init__(self, root: Path = DEFAULT_EXPORT_ROOT) -> None:
        self.root = root.resolve()
        self.snapshot_dir = self.root / "snapshots"
        self.manifest_path = self.root / "manifest.json"

    def _new_manifest(self, generated_at: str) -> dict[str, Any]:
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "generated_at": generated_at,
            "advisory_only": True,
            "latest": {name: None for name in sorted(REPORT_TYPES)},
            "snapshots": [],
        }

    def _load_manifest(self, generated_at: str) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return self._new_manifest(generated_at)
        manifest = strict_load_json(self.manifest_path)
        validate_manifest(manifest)
        return manifest

    def publish(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        if (self.root / "DISABLED").exists():
            raise XCoreAdvisoryContractError(
                "X Core advisory export is disabled by runtime marker"
            )
        validate_advisory_snapshot(snapshot)
        snapshot_id = str(snapshot["snapshot_id"])
        report_type = str(snapshot["report_type"])
        content = canonical_json_bytes(snapshot)
        digest = _sha256_bytes(content)
        snapshot_path = self.snapshot_dir / f"{snapshot_id}.json"

        if snapshot_path.exists():
            if snapshot_path.read_bytes() != content:
                raise XCoreAdvisoryContractError(
                    "snapshot ID collision with different content"
                )
        else:
            atomic_write_bytes(snapshot_path, content)

        persisted = strict_load_json(snapshot_path)
        validate_advisory_snapshot(persisted)
        if _sha256_bytes(snapshot_path.read_bytes()) != digest:
            raise XCoreAdvisoryContractError(
                "persisted snapshot digest verification failed"
            )

        reference = {
            "snapshot_id": snapshot_id,
            "report_id": str(snapshot["report_id"]),
            "report_type": report_type,
            "path": f"snapshots/{snapshot_id}.json",
            "sha256": digest,
            "generated_at": str(snapshot["generated_at"]),
            "as_of": str(snapshot["as_of"]),
            "status": "VALID",
        }
        manifest = self._load_manifest(str(snapshot["generated_at"]))
        history = [
            row
            for row in manifest["snapshots"]
            if row.get("snapshot_id") != snapshot_id
        ]
        history.append(reference)
        history.sort(
            key=lambda row: (
                str(row.get("generated_at", "")),
                str(row.get("snapshot_id", "")),
            )
        )
        manifest["snapshots"] = history
        current_latest = manifest["latest"].get(report_type)
        if (
            current_latest is None
            or (
                str(reference["generated_at"]),
                str(reference["snapshot_id"]),
            )
            >= (
                str(current_latest.get("generated_at", "")),
                str(current_latest.get("snapshot_id", "")),
            )
        ):
            manifest["latest"][report_type] = reference
        manifest["generated_at"] = max(
            str(manifest.get("generated_at", "")),
            str(snapshot["generated_at"]),
        )
        validate_manifest(manifest)
        atomic_write_bytes(self.manifest_path, canonical_json_bytes(manifest))
        validate_manifest(strict_load_json(self.manifest_path))
        return {
            "snapshot_id": snapshot_id,
            "report_type": report_type,
            "snapshot_path": str(snapshot_path),
            "manifest_path": str(self.manifest_path),
            "sha256": digest,
            "latest_updated": True,
        }