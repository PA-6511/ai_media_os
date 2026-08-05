#!/usr/bin/env python3
import hashlib
import json
import sys
from dataclasses import dataclass
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


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _project_root_from_index(index_path: Path) -> Path:
    if len(index_path.parents) >= 3:
        return index_path.parents[2]
    return index_path.parent


def _result(status: str, reason: str, details: dict | None = None) -> dict:
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase Evidence Standard v1.3",
        "component": "phase_evidence_integrity_validator",
        "mode": "DRY_RUN",
        "status": status,
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": reason,
        "reason": reason,
        "novelty": ["index integrity validation", "append-only log cross-check"],
        "files_changed": [],
        "tests_executed": [],
        "approval_state": "UNKNOWN",
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
        "sha256": "",
    }
    if details is not None:
        payload["details"] = details
    return payload


def _warn(reason: str, details: dict | None = None) -> dict:
    return _result("WARN", reason, details)


def _fail(reason: str, details: dict | None = None) -> dict:
    return _result("FAIL", reason, details)


def _abort(reason: str, details: dict | None = None) -> dict:
    return _result("ABORT", reason, details)


def _read_log_events(log_path: Path) -> tuple[list[dict], list[str] | None]:
    if not log_path.exists():
        return [], [f"append log not found: {log_path}"]

    events = []
    for line_number, raw_line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"append log JSON syntax error at line {line_number}: {exc}") from exc
        events.append(event)
    return events, None


def _evidence_dir_name_from_entry(entry: dict) -> str:
    return Path(entry.get("evidence_dir", "")).name


def validate_phase_evidence_integrity(
    index_path: Path | str | None = None,
    log_path: Path | str | None = None,
) -> dict:
    index_path = Path(index_path or INDEX_PATH)
    log_path = Path(log_path or APPEND_LOG_PATH)

    if not index_path.exists():
        return _fail(f"index.json not found: {index_path}")

    try:
        index = _load_json(index_path)
    except json.JSONDecodeError as exc:
        return _fail(f"index.json JSON syntax error: {exc}")

    if not isinstance(index, dict):
        return _fail("index.json must be a JSON object")

    for key in ["schema_version", "updated_at_utc", "entries"]:
        if key not in index:
            return _fail(f"index.json missing required key {key}")

    if not isinstance(index["entries"], list):
        return _fail("index.entries must be a list")

    try:
        index_updated_at = _parse_dt(index["updated_at_utc"])
    except Exception as exc:
        return _fail(f"index.updated_at_utc must be ISO 8601: {exc}")

    project_root = _project_root_from_index(index_path)
    evidence_root = index_path.parent
    warnings = []
    file_entry_map: dict[str, dict] = {}
    entry_paths = set()

    for entry in index["entries"]:
        if not isinstance(entry, dict):
            return _fail("index.entries must contain objects")
        for key in ["phase", "component", "status", "evidence_dir", "completion_report", "approval_state", "sha256"]:
            if key not in entry:
                return _fail(f"index entry missing required key {key}")

        completion_report = project_root / entry["completion_report"]
        evidence_dir = project_root / entry["evidence_dir"]
        entry_paths.add(str(completion_report.resolve()))
        file_entry_map[str(completion_report.resolve())] = entry

        if not evidence_dir.exists():
            warnings.append(f"missing evidence directory: {entry['evidence_dir']}")
            continue

        if not completion_report.exists():
            warnings.append(f"missing completion_report.json: {entry['completion_report']}")
            continue

        try:
            completion = _load_json(completion_report)
        except json.JSONDecodeError as exc:
            return _fail(f"completion_report.json JSON syntax error: {entry['completion_report']}: {exc}")

        if not isinstance(completion, dict):
            return _fail(f"completion_report.json must be an object: {entry['completion_report']}")

        for key in ["phase", "component", "status", "approval_state"]:
            expected = entry[key]
            actual = completion.get(key, "UNKNOWN")
            if actual != expected:
                warnings.append(
                    f"{entry['completion_report']} mismatch for {key}: index={expected!r} report={actual!r}"
                )

        actual_sha256 = _sha256(completion_report)
        if actual_sha256 != entry["sha256"]:
            warnings.append(f"sha256 mismatch for {entry['completion_report']}")

    actual_completion_reports = []
    for child in sorted(evidence_root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        completion_report = child / "completion_report.json"
        if completion_report.exists():
            actual_completion_reports.append(str(completion_report.resolve()))
            if str(completion_report.resolve()) not in entry_paths:
                warnings.append(f"completion report not reflected in index: {completion_report.relative_to(project_root)}")
        else:
            warnings.append(f"missing completion_report.json: {child.relative_to(project_root)}")

    try:
        events, log_issue = _read_log_events(log_path)
    except ValueError as exc:
        return _fail(str(exc))

    if log_issue:
        warnings.extend(log_issue)

    update_events = [event for event in events if isinstance(event, dict) and event.get("event") == "evidence_index_updated"]
    if not update_events:
        warnings.append("no evidence_index_updated events found in append log")
        latest_event = None
    else:
        latest_event = update_events[-1]

    expected_entries_count = len(index["entries"])
    expected_warnings_count = len(warnings)

    if latest_event is not None:
        for key in ["timestamp_utc", "status", "entries_count", "warnings_count", "index_path"]:
            if key not in latest_event:
                warnings.append(f"latest append log event missing key {key}")

        if latest_event.get("event") != "evidence_index_updated":
            warnings.append("latest append log event name mismatch")

        if latest_event.get("entries_count") != expected_entries_count:
            warnings.append(
                f"append log entries_count mismatch: log={latest_event.get('entries_count')} index={expected_entries_count}"
            )

        if latest_event.get("warnings_count") != expected_warnings_count:
            warnings.append(
                f"append log warnings_count mismatch: log={latest_event.get('warnings_count')} current={expected_warnings_count}"
            )

        if latest_event.get("index_path") != "reports/evidence/index.json":
            warnings.append(f"append log index_path mismatch: {latest_event.get('index_path')}")

        try:
            log_ts = _parse_dt(latest_event["timestamp_utc"])
            if log_ts < index_updated_at:
                warnings.append("append log timestamp is earlier than index.updated_at_utc")
        except Exception as exc:
            return _fail(f"append log latest event timestamp invalid: {exc}")

    if warnings:
        return _warn(
            "; ".join(warnings),
            {
                "index_entries": expected_entries_count,
                "warnings_count": len(warnings),
                "append_log_events": len(update_events),
            },
        )

    return _result(
        "PASS",
        "index, append log, and completion reports are mutually consistent",
        {
            "index_entries": expected_entries_count,
            "warnings_count": 0,
            "append_log_events": len(update_events),
        },
    )


def main() -> int:
    index_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INDEX_PATH
    log_path = Path(sys.argv[2]) if len(sys.argv) > 2 else APPEND_LOG_PATH
    result = validate_phase_evidence_integrity(index_path=index_path, log_path=log_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())