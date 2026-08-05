import hashlib
import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.update_phase_evidence_index import update_phase_evidence_index
from scripts import update_phase_evidence_index as updater


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _evidence_record(phase: str, component: str, status: str = "PASS") -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "component": component,
        "mode": "DRY_RUN",
        "status": status,
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": "ok",
        "reason": "ok",
        "novelty": ["index test"],
        "files_changed": ["x.py"],
        "tests_executed": ["pytest"],
        "approval_state": "PENDING",
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


def _build_completion_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_update_phase_evidence_index_passes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        completion = phase_dir / "completion_report.json"
        _write_json(completion, _evidence_record("Phase 6-1", "xxx"))

        index = update_phase_evidence_index(evidence_root)

        assert index["status"] == "PASS"
        assert len(index["entries"]) == 1
        assert index["entries"][0]["sha256"] == _build_completion_sha(completion)


def test_update_phase_evidence_index_warns_when_empty():
    with tempfile.TemporaryDirectory() as td:
        evidence_root = Path(td) / "reports" / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)

        index = update_phase_evidence_index(evidence_root)

        assert index["status"] == "WARN"
        assert index["entries"] == []


def test_update_phase_evidence_index_skips_invalid_json():
    with tempfile.TemporaryDirectory() as td:
        evidence_root = Path(td) / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_2_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / "completion_report.json").write_text("{invalid json", encoding="utf-8")

        index = update_phase_evidence_index(evidence_root)

        assert index["status"] == "WARN"
        assert index["entries"] == []


def test_update_phase_evidence_index_appends_log_without_overwriting():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_3_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        completion = phase_dir / "completion_report.json"
        _write_json(completion, _evidence_record("Phase 6-3", "xxx"))

        index_path = root / "reports" / "evidence" / "index.json"
        log_path = root / "logs" / "evidence_append.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text('{"timestamp_utc":"2026-05-23T00:00:00Z","event":"seed"}\n', encoding="utf-8")

        original_index_path = updater.INDEX_PATH
        original_log_path = updater.APPEND_LOG_PATH
        updater.INDEX_PATH = index_path
        updater.APPEND_LOG_PATH = log_path
        try:
            index = updater.run_update(evidence_root=evidence_root)
        finally:
            updater.INDEX_PATH = original_index_path
            updater.APPEND_LOG_PATH = original_log_path

        assert index["status"] == "PASS"
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["event"] == "seed"
        assert second["event"] == "evidence_index_updated"
        assert second["entries_count"] == 1
        assert second["warnings_count"] == 0
        assert second["index_path"] == "reports/evidence/index.json"