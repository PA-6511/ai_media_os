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
AUDIT_REPORT_PATH = EVIDENCE_ROOT / "approval_audit_report.json"
DASHBOARD_PATH = EVIDENCE_ROOT / "dashboard.md"

UNRESOLVED_STATES = {"PENDING", "REQUEST_FIX", "REJECTED", "ABORTED", "UNKNOWN"}


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


def _load_audit_report(report_path: Path) -> dict:
    if not report_path.exists():
        return {
            "schema_version": "phase_approval_audit_report_v1.5",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "WARN",
            "summary": {
                "total_count": 0,
                "approved_count": 0,
                "pending_count": 0,
                "request_fix_count": 0,
                "rejected_count": 0,
                "aborted_count": 0,
                "unknown_count": 0,
                "unresolved_count": 0,
            },
            "entries": [],
            "unresolved_entries": [],
            "source_index": "UNKNOWN",
            "source_approval_history": "UNKNOWN",
        }
    payload = _load_json(report_path)
    if not isinstance(payload, dict):
        raise ValueError("approval_audit_report.json must be a JSON object")
    return payload


def _latest_history_map(entries: list[dict]) -> dict[tuple[str, str, str], dict]:
    latest = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = (
            entry.get("phase", "UNKNOWN"),
            entry.get("component", "UNKNOWN"),
            entry.get("evidence_dir", "UNKNOWN"),
        )
        latest[key] = entry
    return latest


def _normalize_state(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    state = str(value)
    return state if state in {"APPROVED", "PENDING", "REQUEST_FIX", "REJECTED", "ABORTED", "UNKNOWN"} else "UNKNOWN"


def _row_decision(status: str, approval_state: str) -> str:
    if status == "ABORT" or approval_state == "ABORTED":
        return "ABORT"
    if status == "FAIL":
        return "FAIL"
    if approval_state == "APPROVED":
        return "PASS"
    return "WARN"


def _row_updated_at(index_entry: dict, history_entry: dict | None, audit_generated_at: str) -> str:
    candidates = []
    if history_entry and history_entry.get("timestamp_utc"):
        candidates.append(str(history_entry["timestamp_utc"]))
    if index_entry.get("updated_at_utc"):
        candidates.append(str(index_entry["updated_at_utc"]))
    if index_entry.get("approval_updated_at_utc"):
        candidates.append(str(index_entry["approval_updated_at_utc"]))
    candidates.append(audit_generated_at)
    return max(candidates)


def _build_rows(index: dict, history: dict, audit_report: dict) -> tuple[list[dict], dict]:
    summary = audit_report.get("summary", {}) if isinstance(audit_report.get("summary"), dict) else {}
    latest_history = _latest_history_map(history.get("entries", []))
    rows = []
    for index_entry in index["entries"]:
        if not isinstance(index_entry, dict):
            continue
        phase = index_entry.get("phase", "UNKNOWN")
        component = index_entry.get("component", "UNKNOWN")
        evidence_dir = index_entry.get("evidence_dir", "UNKNOWN")
        history_entry = latest_history.get((phase, component, evidence_dir))
        approval_state = _normalize_state(history_entry.get("approval_state") if history_entry else index_entry.get("approval_state"))
        status = str(index_entry.get("status", "UNKNOWN"))
        unresolved = 0 if approval_state == "APPROVED" else 1
        if approval_state == "APPROVED":
            unresolved = 0
        elif approval_state in UNRESOLVED_STATES:
            unresolved = 1
        else:
            unresolved = 1
        rows.append(
            {
                "phase": phase,
                "component": component,
                "status": status,
                "approval_state": approval_state,
                "source": history_entry.get("source", "index.json") if history_entry else "index.json",
                "unresolved": unresolved,
                "updated_at_utc": _row_updated_at(index_entry, history_entry, str(audit_report.get("generated_at_utc", datetime.now(timezone.utc).isoformat()))),
                "decision": _row_decision(status, approval_state),
            }
        )
    if not rows:
        summary = {
            "total_count": 0,
            "approved_count": 0,
            "pending_count": 0,
            "request_fix_count": 0,
            "rejected_count": 0,
            "aborted_count": 0,
            "unknown_count": 0,
            "unresolved_count": 0,
        }
    return rows, summary


def _render_dashboard(rows: list[dict], summary: dict, status: str, audit_report: dict, generated_at_utc: str) -> str:
    lines = [
        "# Phase Evidence Dashboard",
        "",
        f"- Generated at: {generated_at_utc}",
        f"- Status: {status}",
        f"- Source index: {audit_report.get('source_index', 'UNKNOWN')}",
        f"- Source approval history: {audit_report.get('source_approval_history', 'UNKNOWN')}",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "| Phase | Component | Status | Approval State | Unresolved | Updated At (UTC) | Decision |",
        "|-------|-----------|--------|----------------|------------|------------------|----------|",
    ])
    for row in rows:
        lines.append(
            f"| {row['phase']} | {row['component']} | {row['status']} | {row['approval_state']} | {row['unresolved']} | {row['updated_at_utc']} | {row['decision']} |"
        )
    if not rows:
        lines.append("| - | - | - | - | 0 | - | PASS |")
    lines.append("")
    return "\n".join(lines)


def generate_phase_dashboard(
    index_path: Path | str | None = None,
    history_path: Path | str | None = None,
    audit_report_path: Path | str | None = None,
    dashboard_path: Path | str | None = None,
) -> dict:
    index_path = Path(index_path or INDEX_PATH)
    history_path = Path(history_path or HISTORY_PATH)
    audit_report_path = Path(audit_report_path or AUDIT_REPORT_PATH)
    dashboard_path = Path(dashboard_path or DASHBOARD_PATH)

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

    try:
        audit_report = _load_audit_report(audit_report_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"approval_audit_report.json JSON syntax error: {exc}") from exc

    rows, summary = _build_rows(index, history, audit_report)
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    unresolved_count = summary.get("unresolved_count", 0)
    status = "PASS" if unresolved_count == 0 else "WARN"

    dashboard = _render_dashboard(rows, summary, status, audit_report, generated_at_utc)
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(dashboard, encoding="utf-8")

    return {
        "schema_version": "phase_evidence_dashboard_v1.7",
        "generated_at_utc": generated_at_utc,
        "status": status,
        "summary": summary,
        "rows": rows,
        "dashboard_path": dashboard_path,
        "source_index": _relative_or_str(index_path, _project_root(index_path)),
        "source_approval_history": _relative_or_str(history_path, _project_root(index_path)),
        "source_audit_report": _relative_or_str(audit_report_path, _project_root(index_path)),
    }


def main() -> int:
    index_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INDEX_PATH
    result = generate_phase_dashboard(index_path=index_path)
    print(json.dumps({"dashboard_path": str(result["dashboard_path"]), "status": result["status"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())