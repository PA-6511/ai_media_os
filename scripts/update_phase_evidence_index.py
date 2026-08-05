#!/usr/bin/env python3
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "reports" / "evidence"
INDEX_PATH = EVIDENCE_ROOT / "index.json"
APPEND_LOG_PATH = ROOT / "logs" / "evidence_append.log"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(evidence_root: Path) -> Path:
    if len(evidence_root.parents) >= 2:
        return evidence_root.parents[1]
    return evidence_root.parent


def _relative_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _empty_index(reason: str) -> dict:
    return {
        "schema_version": "phase_evidence_index_v1.1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WARN",
        "reason": reason,
        "entries": [],
    }


def _collect_entry(evidence_dir: Path, completion_report: Path, project_root: Path) -> dict:
    completion = _load_json(completion_report)
    phase = completion.get("phase", "UNKNOWN")
    component = completion.get("component", evidence_dir.name)
    status = completion.get("status", "UNKNOWN")
    approval_state = completion.get("approval_state", "UNKNOWN")
    try:
        evidence_dir_value = str(evidence_dir.relative_to(project_root))
    except ValueError:
        evidence_dir_value = str(evidence_dir)
    try:
        completion_report_value = str(completion_report.relative_to(project_root))
    except ValueError:
        completion_report_value = str(completion_report)
    return {
        "phase": phase,
        "component": component,
        "status": status,
        "evidence_dir": evidence_dir_value,
        "completion_report": completion_report_value,
        "approval_state": approval_state,
        "sha256": _sha256(completion_report),
    }


def update_phase_evidence_index(evidence_root: Path | str | None = None) -> dict:
    evidence_root = Path(evidence_root or EVIDENCE_ROOT)
    project_root = _project_root(evidence_root)
    if not evidence_root.exists():
        return _empty_index(f"evidence root not found: {evidence_root}")

    entries = []
    warnings = []

    for child in sorted(evidence_root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        completion_report = child / "completion_report.json"
        if not completion_report.exists():
            warnings.append(f"skipped {child.name}: missing completion_report.json")
            continue
        try:
            entry = _collect_entry(child, completion_report, project_root)
        except json.JSONDecodeError:
            warnings.append(f"skipped {child.name}: completion_report.json is invalid JSON")
            continue
        entries.append(entry)

    status = "PASS" if entries else "WARN"
    reason = "index updated from evidence directories" if entries else "no phase evidence entries found"
    if warnings and status == "PASS":
        status = "WARN"
        reason = "; ".join(warnings)
    elif warnings:
        reason = "; ".join(warnings)

    index = {
        "schema_version": "phase_evidence_index_v1.1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "reason": reason,
        "entries": entries,
    }
    return index


def run_update(evidence_root: Path | str | None = None, output_path: Path | str | None = None) -> dict:
    evidence_root = Path(evidence_root or EVIDENCE_ROOT)
    project_root = _project_root(evidence_root)
    index = update_phase_evidence_index(evidence_root=evidence_root)
    output_path = Path(output_path or INDEX_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    log_path = APPEND_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    warnings_count = 0
    if index.get("status") == "WARN":
        reason = index.get("reason", "")
        warnings_count = 0 if not reason else len([part for part in str(reason).split("; ") if part])
    event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": "evidence_index_updated",
        "status": index.get("status", "UNKNOWN"),
        "entries_count": len(index.get("entries", [])),
        "warnings_count": warnings_count,
        "index_path": _relative_or_str(output_path, project_root),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return index


def main() -> int:
    evidence_root = Path(sys.argv[1]) if len(sys.argv) > 1 else EVIDENCE_ROOT
    index = run_update(evidence_root=evidence_root)
    print(json.dumps(index, ensure_ascii=False, indent=2))
    return 0 if index.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())