import json
import tempfile
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_phase_evidence_integrity import validate_phase_evidence_integrity


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _record(phase: str, component: str, status: str = "PASS", approval_state: str = "PENDING") -> dict:
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
        "novelty": ["integrity test"],
        "files_changed": ["x.py"],
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


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_index_entry(index_root: Path, phase_dir: Path, completion: Path) -> dict:
    record = json.loads(completion.read_text(encoding="utf-8"))
    return {
        "phase": record["phase"],
        "component": record["component"],
        "status": record["status"],
        "evidence_dir": str(phase_dir.relative_to(index_root.parents[1])),
        "completion_report": str(completion.relative_to(index_root.parents[1])),
        "approval_state": record["approval_state"],
        "sha256": _sha256(completion),
    }


def _write_index(index_path: Path, entries: list[dict], updated_at: str) -> None:
    _write_json(
        index_path,
        {
            "schema_version": "phase_evidence_index_v1.1",
            "updated_at_utc": updated_at,
            "status": "PASS" if entries else "WARN",
            "reason": "index updated from evidence directories" if entries else "no phase evidence entries found",
            "entries": entries,
        },
    )


def _write_log(log_path: Path, events: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event, ensure_ascii=False) for event in events]
    log_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def test_integrity_passes_when_index_and_log_match():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        completion = phase_dir / "completion_report.json"
        _write_json(completion, _record("Phase 6-1", "xxx"))
        updated_at = datetime.now(timezone.utc).isoformat()
        entry = _make_index_entry(evidence_root, phase_dir, completion)
        index_path = evidence_root / "index.json"
        _write_index(index_path, [entry], updated_at)

        log_path = root / "logs" / "evidence_append.log"
        _write_log(
            log_path,
            [
                {
                    "timestamp_utc": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                    "event": "evidence_index_updated",
                    "status": "PASS",
                    "entries_count": 1,
                    "warnings_count": 0,
                    "index_path": "reports/evidence/index.json",
                }
            ],
        )

        result = validate_phase_evidence_integrity(index_path=index_path, log_path=log_path)

        assert result["status"] == "PASS"


def test_integrity_warns_when_completion_report_missing():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        index_path = evidence_root / "index.json"
        _write_index(
            index_path,
            [
                {
                    "phase": "Phase 6-1",
                    "component": "xxx",
                    "status": "PASS",
                    "evidence_dir": str(phase_dir.relative_to(root)),
                    "completion_report": str((phase_dir / "completion_report.json").relative_to(root)),
                    "approval_state": "PENDING",
                    "sha256": "missing",
                }
            ],
            datetime.now(timezone.utc).isoformat(),
        )
        log_path = root / "logs" / "evidence_append.log"
        _write_log(
            log_path,
            [
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "event": "evidence_index_updated",
                    "status": "WARN",
                    "entries_count": 1,
                    "warnings_count": 1,
                    "index_path": "reports/evidence/index.json",
                }
            ],
        )

        result = validate_phase_evidence_integrity(index_path=index_path, log_path=log_path)

        assert result["status"] == "WARN"


def test_integrity_warns_when_log_and_index_counts_differ():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)

        completion = phase_dir / "completion_report.json"
        _write_json(completion, _record("Phase 6-1", "xxx"))
        index_path = evidence_root / "index.json"
        entry = _make_index_entry(evidence_root, phase_dir, completion)
        _write_index(index_path, [entry], datetime.now(timezone.utc).isoformat())

        log_path = root / "logs" / "evidence_append.log"
        _write_log(
            log_path,
            [
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "event": "evidence_index_updated",
                    "status": "PASS",
                    "entries_count": 2,
                    "warnings_count": 0,
                    "index_path": "reports/evidence/index.json",
                }
            ],
        )

        result = validate_phase_evidence_integrity(index_path=index_path, log_path=log_path)

        assert result["status"] == "WARN"


def test_integrity_fails_on_json_syntax_error():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index_path = root / "reports" / "evidence" / "index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("{invalid json", encoding="utf-8")
        log_path = root / "logs" / "evidence_append.log"
        _write_log(log_path, [])

        result = validate_phase_evidence_integrity(index_path=index_path, log_path=log_path)

        assert result["status"] == "FAIL"