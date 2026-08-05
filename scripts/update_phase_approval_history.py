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
APPEND_LOG_PATH = ROOT / "logs" / "evidence_append.log"

ALLOWED_APPROVAL_STATES = {
    "UNKNOWN",
    "PENDING",
    "APPROVED",
    "REJECTED",
    "REQUEST_FIX",
    "ABORTED",
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_root(index_path: Path) -> Path:
    if len(index_path.parents) >= 3:
        return index_path.parents[2]
    return index_path.parent


def _relative_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _empty_history(reason: str) -> dict:
    return {
        "schema_version": "phase_approval_history_v1.4",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "WARN",
        "reason": reason,
        "entries": [],
    }


def _empty_result(status: str, reason: str, details: dict | None = None) -> dict:
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase Approval History v1.4",
        "component": "phase_approval_history_updater",
        "mode": "DRY_RUN",
        "status": status,
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": reason,
        "reason": reason,
        "novelty": ["approval history tracking", "approval state change audit"],
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
    return _empty_result("WARN", reason, details)


def _fail(reason: str, details: dict | None = None) -> dict:
    return _empty_result("FAIL", reason, details)


def _abort(reason: str, details: dict | None = None) -> dict:
    return _empty_result("ABORT", reason, details)


def _read_current_approval_state(evidence_dir: Path) -> tuple[str, str]:
    approval_evidence = evidence_dir / "approval_evidence.json"
    completion_report = evidence_dir / "completion_report.json"

    if approval_evidence.exists():
        try:
            payload = _load_json(approval_evidence)
        except json.JSONDecodeError as exc:
            raise ValueError(f"approval_evidence.json JSON syntax error: {approval_evidence}: {exc}") from exc
        if isinstance(payload, dict) and payload.get("approval_state") in ALLOWED_APPROVAL_STATES:
            return payload["approval_state"], "approval_evidence.json"
        return "UNKNOWN", "approval_evidence.json"

    if completion_report.exists():
        try:
            payload = _load_json(completion_report)
        except json.JSONDecodeError as exc:
            raise ValueError(f"completion_report.json JSON syntax error: {completion_report}: {exc}") from exc
        if isinstance(payload, dict) and payload.get("approval_state") in ALLOWED_APPROVAL_STATES:
            return payload["approval_state"], "completion_report.json"
        return "UNKNOWN", "completion_report.json"

    return "UNKNOWN", "UNKNOWN"


def _load_history(history_path: Path) -> dict:
    if not history_path.exists():
        return {
            "schema_version": "phase_approval_history_v1.4",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "entries": [],
        }
    payload = _load_json(history_path)
    if not isinstance(payload, dict):
        raise ValueError("approval_history.json must be a JSON object")
    for key in ["schema_version", "updated_at_utc", "entries"]:
        if key not in payload:
            raise ValueError(f"approval_history.json missing required key {key}")
    if not isinstance(payload["entries"], list):
        raise ValueError("approval_history.entries must be a list")
    return payload


def _last_state_map(entries: list[dict]) -> dict[tuple[str, str, str], str]:
    mapping: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        phase = entry.get("phase", "UNKNOWN")
        component = entry.get("component", "UNKNOWN")
        evidence_dir = entry.get("evidence_dir", "UNKNOWN")
        approval_state = entry.get("approval_state", "UNKNOWN")
        mapping[(phase, component, evidence_dir)] = approval_state
    return mapping


def _collect_approval_entry(index_entry: dict, project_root: Path) -> dict:
    evidence_dir = project_root / index_entry["evidence_dir"]
    current_state, source = _read_current_approval_state(evidence_dir)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": index_entry["phase"],
        "component": index_entry["component"],
        "approval_state": current_state,
        "previous_approval_state": "UNKNOWN",
        "status": index_entry["status"],
        "evidence_dir": index_entry["evidence_dir"],
        "source": source,
        "completion_report": index_entry.get("completion_report", "UNKNOWN"),
    }


def update_phase_approval_history(
    index_path: Path | str | None = None,
    history_path: Path | str | None = None,
    log_path: Path | str | None = None,
) -> dict:
    index_path = Path(index_path or INDEX_PATH)
    history_path = Path(history_path or HISTORY_PATH)
    log_path = Path(log_path or APPEND_LOG_PATH)

    if not index_path.exists():
        return _fail(f"index.json not found: {index_path}")

    try:
        index = _load_json(index_path)
    except json.JSONDecodeError as exc:
        return _fail(f"index.json JSON syntax error: {exc}")

    if not isinstance(index, dict):
        return _fail("index.json must be a JSON object")
    if not isinstance(index.get("entries"), list):
        return _fail("index.entries must be a list")

    project_root = _project_root(index_path)

    try:
        history = _load_history(history_path)
    except ValueError as exc:
        return _fail(str(exc))
    except json.JSONDecodeError as exc:
        return _fail(f"approval_history.json JSON syntax error: {exc}")

    existing_entries = history.get("entries", [])
    last_state = _last_state_map(existing_entries)

    warnings = []
    new_entries = []
    log_events = []

    for index_entry in index["entries"]:
        if not isinstance(index_entry, dict):
            warnings.append("index entry is not an object")
            continue
        missing_keys = False
        for key in ["phase", "component", "status", "evidence_dir", "completion_report", "approval_state"]:
            if key not in index_entry:
                warnings.append(f"index entry missing required key {key}")
                missing_keys = True
        if missing_keys:
            continue

        evidence_dir_value = index_entry["evidence_dir"]
        evidence_dir = project_root / evidence_dir_value
        if not evidence_dir.exists():
            warnings.append(f"missing evidence directory: {evidence_dir_value}")
            continue

        approval_state, source = _read_current_approval_state(evidence_dir)
        if source == "UNKNOWN":
            warnings.append(f"{evidence_dir_value}: approval_evidence.json and completion_report.json approval_state are missing")
        elif source == "completion_report.json" and approval_state == "UNKNOWN":
            warnings.append(f"{evidence_dir_value}: completion_report.json approval_state is missing")
        elif source == "approval_evidence.json" and approval_state == "UNKNOWN":
            warnings.append(f"{evidence_dir_value}: approval_evidence.json approval_state is missing")

        key = (index_entry["phase"], index_entry["component"], evidence_dir_value)
        previous_state = last_state.get(key, "UNKNOWN")
        if approval_state != previous_state:
            history_entry = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase": index_entry["phase"],
                "component": index_entry["component"],
                "approval_state": approval_state,
                "previous_approval_state": previous_state,
                "status": index_entry["status"],
                "evidence_dir": evidence_dir_value,
                "source": source,
            }
            new_entries.append(history_entry)
            log_events.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "event": "approval_state_updated",
                    "phase": index_entry["phase"],
                    "component": index_entry["component"],
                    "previous_approval_state": previous_state,
                    "approval_state": approval_state,
                    "evidence_dir": evidence_dir_value,
                    "history_path": _relative_or_str(history_path, project_root),
                }
            )

    if new_entries:
        history.setdefault("entries", [])
        history["entries"].extend(new_entries)
        history["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        history["schema_version"] = "phase_approval_history_v1.4"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            for event in log_events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "phase": "Phase Approval History v1.4",
            "component": "phase_approval_history_updater",
            "mode": "DRY_RUN",
            "status": "PASS",
            "human_review_required": True,
            "production_status": "NO_GO",
            "summary": "approval history updated with state changes",
            "reason": "approval history updated with state changes",
            "novelty": ["approval history tracking", "approval state change audit"],
            "files_changed": [str(history_path.relative_to(project_root)), str(log_path.relative_to(project_root))],
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
            "details": {
                "new_entries": len(new_entries),
                "warnings": warnings,
            },
        }

    if warnings:
        return _warn(
            "; ".join(warnings),
            {
                "new_entries": 0,
                "warnings": warnings,
            },
        )

    return _warn(
        "no approval state changes detected",
        {
            "new_entries": 0,
            "warnings": warnings,
        },
    )


def main() -> int:
    index_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INDEX_PATH
    history_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HISTORY_PATH
    log_path = Path(sys.argv[3]) if len(sys.argv) > 3 else APPEND_LOG_PATH
    result = update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())