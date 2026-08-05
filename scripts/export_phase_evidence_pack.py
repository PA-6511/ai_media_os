#!/usr/bin/env python3
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_ROOT = ROOT / "exports" / "phase_evidence"
DEFAULT_SOURCES = {
    "reports_evidence": ROOT / "reports" / "evidence",
    "logs": ROOT / "logs" / "evidence_append.log",
    "schemas": ROOT / "schemas" / "phase_evidence.schema.json",
    "prompts": ROOT / "prompts" / "phase_evidence_compact_v1.txt",
    "docs_checklists": ROOT / "docs" / "checklists" / "phase_evidence_checklist_v1.md",
}
APPEND_LOG_PATH = ROOT / "logs" / "evidence_append.log"


def _relative_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp_token(timestamp_utc: str | None = None) -> str:
    if timestamp_utc is None:
        timestamp_utc = datetime.now(timezone.utc).isoformat()
    normalized = timestamp_utc.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return dt.strftime("%Y%m%d_%H%M%S")


def _ensure_unique_pack_dir(export_root: Path, base_name: str) -> Path:
    candidate = export_root / base_name
    if not candidate.exists():
        return candidate
    suffix = 1
    while True:
        alt = export_root / f"{base_name}_{suffix}"
        if not alt.exists():
            return alt
        suffix += 1


def _copy_path(source: Path, destination: Path) -> list[Path]:
    exported = []
    if source.is_dir():
        shutil.copytree(source, destination)
        for file_path in destination.rglob("*"):
            if file_path.is_file():
                exported.append(file_path)
        return exported

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return [destination]


def _write_readme(pack_dir: Path, summary: dict) -> Path:
    readme = pack_dir / "README.md"
    lines = [
        "# Phase Evidence Export Pack",
        "",
        f"- Generated at: {summary['generated_at_utc']}",
        f"- Status: {summary['status']}",
        "",
        "## Contents",
        "- reports_evidence/",
        "- logs/",
        "- schemas/",
        "- prompts/",
        "- docs_checklists/",
        "",
        "## Notes",
        "- Export is local-only and append-only for logs.",
        "- Existing export packs are never overwritten.",
    ]
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return readme


def _build_manifest(summary: dict, source_paths: list[str], exported_files: list[Path], missing_sources: list[str], export_root: Path) -> dict:
    sha256_manifest = {}
    for file_path in exported_files:
        sha256_manifest[_relative_or_str(file_path, export_root)] = _sha256(file_path)
    return {
        "schema_version": "phase_evidence_export_pack_v1.6",
        "generated_at_utc": summary["generated_at_utc"],
        "status": summary["status"],
        "source_paths": source_paths,
        "exported_files": sorted(sha256_manifest.keys()),
        "missing_sources": missing_sources,
        "sha256_manifest": sha256_manifest,
        "side_effect_policy": {
            "wordpress_write": False,
            "external_send": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "vps_execution": False,
            "production_reflection": False,
        },
    }


def _append_log(event: dict, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def export_phase_evidence_pack(
    export_root: Path | str | None = None,
    sources: dict[str, Path] | None = None,
    timestamp_utc: str | None = None,
    log_path: Path | str | None = None,
) -> dict:
    export_root = Path(export_root or DEFAULT_EXPORT_ROOT)
    sources = sources or DEFAULT_SOURCES
    log_path = Path(log_path or APPEND_LOG_PATH)

    export_root.mkdir(parents=True, exist_ok=True)
    token = _timestamp_token(timestamp_utc)
    pack_dir = _ensure_unique_pack_dir(export_root, f"phase_evidence_export_pack_{token}")
    pack_dir.mkdir(parents=True, exist_ok=False)

    source_paths = [str(path) for path in sources.values()]
    missing_sources = []
    exported_files: list[Path] = []

    for folder_name, source in sources.items():
        if not source.exists():
            missing_sources.append(str(source))
            continue
        destination = pack_dir / folder_name
        exported_files.extend(_copy_path(source, destination))

    generated_at_utc = datetime.now(timezone.utc).isoformat()
    status = "WARN" if missing_sources else "PASS"
    summary = {
        "generated_at_utc": generated_at_utc,
        "status": status,
        "source_count": len(source_paths),
        "exported_count": len(exported_files),
        "missing_count": len(missing_sources),
    }

    readme_path = _write_readme(pack_dir, summary)
    exported_files.append(readme_path)

    manifest = _build_manifest(summary, source_paths, exported_files, missing_sources, export_root)
    manifest_path = pack_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    exported_files.append(manifest_path)

    # refresh manifest hashes after manifest itself exists
    manifest["exported_files"] = sorted({_relative_or_str(path, export_root) for path in exported_files})
    manifest["sha256_manifest"] = {
        rel: _sha256(export_root / rel) if not (export_root / rel).is_dir() else None
        for rel in manifest["exported_files"]
    }
    manifest["sha256_manifest"] = {
        rel: _sha256(export_root / rel) if (export_root / rel).exists() and (export_root / rel).is_file() else None
        for rel in manifest["exported_files"]
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    event = {
        "timestamp_utc": generated_at_utc,
        "event": "phase_evidence_export_pack_generated",
        "status": status,
        "export_pack_path": _relative_or_str(pack_dir, ROOT),
        "source_count": len(source_paths),
        "exported_count": len(exported_files),
        "missing_count": len(missing_sources),
    }
    _append_log(event, log_path)

    return {
        "pack_dir": pack_dir,
        "manifest_path": manifest_path,
        "readme_path": readme_path,
        "status": status,
        "missing_sources": missing_sources,
        "exported_files": exported_files,
        "manifest": manifest,
    }


def main() -> int:
    result = export_phase_evidence_pack()
    print(json.dumps({"pack_dir": str(result["pack_dir"]), "status": result["status"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())