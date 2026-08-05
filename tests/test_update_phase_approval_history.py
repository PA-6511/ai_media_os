import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import update_phase_approval_history as updater


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_index_entry(root: Path, phase_dir: Path, approval_state: str = "PENDING") -> dict:
    return {
        "phase": "Phase 6-1",
        "component": "xxx",
        "status": "PASS",
        "evidence_dir": str(phase_dir.relative_to(root)),
        "completion_report": str((phase_dir / "completion_report.json").relative_to(root)),
        "approval_state": approval_state,
        "sha256": "index-placeholder",
    }


def _completion_report(approval_state: str = "PENDING") -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 6-1",
        "component": "xxx",
        "mode": "DRY_RUN",
        "status": "PASS",
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": "ok",
        "reason": "ok",
        "novelty": ["approval history test"],
        "files_changed": ["a.py"],
        "tests_executed": ["pytest"],
        "approval_state": approval_state,
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
        "sha256": "placeholder",
    }


def _approval_evidence(approval_state: str) -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 6-1",
        "component": "xxx",
        "approval_state": approval_state,
        "reviewer": "human",
    }


def _write_index(index_path: Path, entries: list[dict]) -> None:
    _write_json(
        index_path,
        {
            "schema_version": "phase_evidence_index_v1.1",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "reason": "index updated from evidence directories",
            "entries": entries,
        },
    )


def _write_history(history_path: Path, entries: list[dict]) -> None:
    _write_json(
        history_path,
        {
            "schema_version": "phase_approval_history_v1.4",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "entries": entries,
        },
    )


def _write_log(log_path: Path, lines: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(json.dumps(line, ensure_ascii=False) for line in lines) + ("\n" if lines else ""), encoding="utf-8")


def test_update_phase_approval_history_passes_and_appends_event():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        _write_json(phase_dir / "completion_report.json", _completion_report("PENDING"))
        _write_json(phase_dir / "approval_evidence.json", _approval_evidence("APPROVED"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        log_path = root / "logs" / "evidence_append.log"
        _write_index(index_path, [_make_index_entry(root, phase_dir)])
        _write_history(history_path, [])
        _write_log(log_path, [{"timestamp_utc": "2026-05-23T00:00:00Z", "event": "seed"}])

        original_index = updater.INDEX_PATH
        original_history = updater.HISTORY_PATH
        original_log = updater.APPEND_LOG_PATH
        updater.INDEX_PATH = index_path
        updater.HISTORY_PATH = history_path
        updater.APPEND_LOG_PATH = log_path
        try:
            result = updater.update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)
        finally:
            updater.INDEX_PATH = original_index
            updater.HISTORY_PATH = original_history
            updater.APPEND_LOG_PATH = original_log

        assert result["status"] == "PASS"
        history = json.loads(history_path.read_text(encoding="utf-8"))
        assert len(history["entries"]) == 1
        assert history["entries"][0]["approval_state"] == "APPROVED"
        assert history["entries"][0]["previous_approval_state"] == "UNKNOWN"

        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        event = json.loads(lines[-1])
        assert event["event"] == "approval_state_updated"
        assert event["approval_state"] == "APPROVED"
        assert event["previous_approval_state"] == "UNKNOWN"


def test_update_phase_approval_history_warns_on_no_change():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        _write_json(phase_dir / "completion_report.json", _completion_report("PENDING"))
        _write_json(phase_dir / "approval_evidence.json", _approval_evidence("PENDING"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        log_path = root / "logs" / "evidence_append.log"
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "phase": "Phase 6-1",
            "component": "xxx",
            "approval_state": "PENDING",
            "previous_approval_state": "UNKNOWN",
            "status": "PASS",
            "evidence_dir": str(phase_dir.relative_to(root)),
            "source": "approval_evidence.json",
        }
        _write_index(index_path, [_make_index_entry(root, phase_dir)])
        _write_history(history_path, [entry])
        _write_log(log_path, [])

        result = updater.update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)

        assert result["status"] == "WARN"
        assert "no approval state changes detected" in result["reason"]
        assert log_path.read_text(encoding="utf-8") == ""


def test_update_phase_approval_history_warns_when_sources_missing():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        log_path = root / "logs" / "evidence_append.log"
        _write_index(index_path, [_make_index_entry(root, phase_dir)])
        _write_history(history_path, [])
        _write_log(log_path, [])

        result = updater.update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)

        assert result["status"] == "WARN"


def test_update_phase_approval_history_fails_on_bad_index_json():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index_path = root / "reports" / "evidence" / "index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("{invalid json", encoding="utf-8")
        history_path = root / "reports" / "evidence" / "approval_history.json"
        _write_history(history_path, [])
        log_path = root / "logs" / "evidence_append.log"
        _write_log(log_path, [])

        result = updater.update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)

        assert result["status"] == "FAIL"


def test_update_phase_approval_history_fails_on_bad_history_json():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        _write_json(phase_dir / "completion_report.json", _completion_report("PENDING"))
        _write_json(phase_dir / "approval_evidence.json", _approval_evidence("APPROVED"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        log_path = root / "logs" / "evidence_append.log"
        _write_index(index_path, [_make_index_entry(root, phase_dir)])
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text("{invalid json", encoding="utf-8")
        _write_log(log_path, [])

        result = updater.update_phase_approval_history(index_path=index_path, history_path=history_path, log_path=log_path)

        assert result["status"] == "FAIL"