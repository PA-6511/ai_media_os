#!/usr/bin/env python3
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "reports" / "evidence"
INDEX_PATH = EVIDENCE_ROOT / "index.json"
HISTORY_PATH = EVIDENCE_ROOT / "approval_history.json"
REPORT_JSON_PATH = EVIDENCE_ROOT / "approval_audit_report.json"
REPORT_MD_PATH = EVIDENCE_ROOT / "approval_audit_report.md"
APPEND_LOG_PATH = ROOT / "logs" / "evidence_append.log"

UNRESOLVED_STATES = {"PENDING", "REQUEST_FIX", "REJECTED", "ABORTED", "UNKNOWN"}
ALLOWED_STATES = {"APPROVED", "PENDING", "REQUEST_FIX", "REJECTED", "ABORTED", "UNKNOWN"}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(path: Path) -> Path:
    if len(path.parents) >= 3:
        return path.parents[2]
    return path.parent


def _relative_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _load_index(index_path: Path) -> dict:
    payload = _load_json(index_path)
    if not isinstance(payload, dict):
        raise ValueError("index.json must be a JSON object")
    if not isinstance(payload.get("entries"), list):
        raise ValueError("index.entries must be a list")
    return payload


def _load_history(history_path: Path) -> dict:
    if not history_path.exists():
        return {"schema_version": "phase_approval_history_v1.4", "updated_at_utc": datetime.now(timezone.utc).isoformat(), "entries": []}
    payload = _load_json(history_path)
    if not isinstance(payload, dict):
        raise ValueError("approval_history.json must be a JSON object")
    if not isinstance(payload.get("entries"), list):
        raise ValueError("approval_history.entries must be a list")
    return payload


def _latest_history_map(entries: list[dict]) -> dict[tuple[str, str, str], dict]:
    latest = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = (entry.get("phase", "UNKNOWN"), entry.get("component", "UNKNOWN"), entry.get("evidence_dir", "UNKNOWN"))
        latest[key] = entry
    return latest


def _normalize_state(value: object) -> str:
    if value in ALLOWED_STATES:
        return str(value)
    return "UNKNOWN"


def _classify_state(state: str) -> str:
    if state == "APPROVED":
        return "resolved"
    if state in UNRESOLVED_STATES:
        return "unresolved"
    return "unresolved"


def _summary_template() -> dict:
    return {
        "total_count": 0,
        "approved_count": 0,
        "pending_count": 0,
        "request_fix_count": 0,
        "rejected_count": 0,
        "aborted_count": 0,
        "unknown_count": 0,
        "unresolved_count": 0,
    }


def _increment_summary(summary: dict, state: str) -> None:
    summary["total_count"] += 1
    if state == "APPROVED":
        summary["approved_count"] += 1
    elif state == "PENDING":
        summary["pending_count"] += 1
        summary["unresolved_count"] += 1
    elif state == "REQUEST_FIX":
        summary["request_fix_count"] += 1
        summary["unresolved_count"] += 1
    elif state == "REJECTED":
        summary["rejected_count"] += 1
        summary["unresolved_count"] += 1
    elif state == "ABORTED":
        summary["aborted_count"] += 1
        summary["unresolved_count"] += 1
    else:
        summary["unknown_count"] += 1
        summary["unresolved_count"] += 1


def _state_source(history_entry: dict | None, index_entry: dict) -> tuple[str, str]:
    if history_entry is not None:
        return _normalize_state(history_entry.get("approval_state")), "approval_history.json"
    if index_entry.get("approval_state") is not None:
        return _normalize_state(index_entry.get("approval_state")), "index.json"
    return "UNKNOWN", "UNKNOWN"


def _build_entries(index: dict, history: dict, project_root: Path) -> tuple[list[dict], list[dict], dict]:
    summary = _summary_template()
    entries = []
    unresolved_entries = []
    latest_history = _latest_history_map(history.get("entries", []))

    for index_entry in index["entries"]:
        if not isinstance(index_entry, dict):
            continue
        phase = index_entry.get("phase", "UNKNOWN")
        component = index_entry.get("component", "UNKNOWN")
        evidence_dir = index_entry.get("evidence_dir", "UNKNOWN")
        completion_report = index_entry.get("completion_report", "UNKNOWN")
        history_entry = latest_history.get((phase, component, evidence_dir))
        approval_state, source = _state_source(history_entry, index_entry)
        status = _classify_state(approval_state)
        entry = {
            "phase": phase,
            "component": component,
            "evidence_dir": evidence_dir,
            "approval_state": approval_state,
            "source": source,
            "status": status,
            "completion_report": completion_report,
        }
        entries.append(entry)
        _increment_summary(summary, approval_state)
        if status == "unresolved":
            unresolved_entries.append(entry)

    return entries, unresolved_entries, summary


def _markdown_report(report: dict) -> str:
    lines = [
        "# Phase Approval Audit Report",
        "",
        f"- Schema: {report['schema_version']}",
        f"- Generated at: {report['generated_at_utc']}",
        f"- Status: {report['status']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Entries"])
    for entry in report["entries"]:
        lines.append(
            f"- {entry['phase']} / {entry['component']} / {entry['approval_state']} / {entry['source']} / {entry['status']}"
        )
    lines.append("")
    return "\n".join(lines)


def generate_phase_approval_audit_report(
    index_path: Path | str | None = None,
    history_path: Path | str | None = None,
    report_json_path: Path | str | None = None,
    report_md_path: Path | str | None = None,
    log_path: Path | str | None = None,
) -> dict:
    index_path = Path(index_path or INDEX_PATH)
    history_path = Path(history_path or HISTORY_PATH)
    report_json_path = Path(report_json_path or REPORT_JSON_PATH)
    report_md_path = Path(report_md_path or REPORT_MD_PATH)
    log_path = Path(log_path or APPEND_LOG_PATH)

    if not index_path.exists():
        raise FileNotFoundError(f"index.json not found: {index_path}")

    try:
        index = _load_index(index_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"index.json JSON syntax error: {exc}") from exc

    try:
        history = _load_history(history_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"approval_history.json JSON syntax error: {exc}") from exc

    project_root = _project_root(index_path)
    entries, unresolved_entries, summary = _build_entries(index, history, project_root)
    status = "PASS" if summary["unresolved_count"] == 0 else "WARN"

    report = {
        "schema_version": "phase_approval_audit_report_v1.5",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": summary,
        "entries": entries,
        "unresolved_entries": unresolved_entries,
        "source_index": _relative_or_str(index_path, project_root),
        "source_approval_history": _relative_or_str(history_path, project_root),
    }

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_markdown_report(report), encoding="utf-8")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "event": "approval_audit_report_generated",
                    "status": status,
                    "entries_count": len(entries),
                    "warnings_count": summary["unresolved_count"],
                    "report_path": _relative_or_str(report_json_path, project_root),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return report


def main() -> int:
    index_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INDEX_PATH
    history_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HISTORY_PATH
    result = generate_phase_approval_audit_report(index_path=index_path, history_path=history_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())