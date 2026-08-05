import hashlib
import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_phase_evidence import EXPECTED_FILES, validate_phase_evidence


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _record(timestamp: str, status: str = "PASS", tests_executed=None) -> dict:
    return {
        "timestamp_utc": timestamp,
        "phase": "Phase 6-2",
        "component": "wordpress_draft_preflight_gate",
        "mode": "DRY_RUN",
        "status": status,
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": "phase evidence record",
        "reason": "DRY_RUN evidence validation",
        "novelty": ["append-only log", "schema validation"],
        "files_changed": ["a.py"],
        "tests_executed": tests_executed if tests_executed is not None else ["pytest"],
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


def _build_manifest(evidence_dir: Path) -> dict:
    files = {}
    for name in EXPECTED_FILES[:-1]:
        files[name] = hashlib.sha256((evidence_dir / name).read_bytes()).hexdigest()
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "sha256": "manifest-placeholder",
    }


def test_validate_phase_evidence_passes():
    with tempfile.TemporaryDirectory() as td:
        evidence_dir = Path(td)
        timestamp = datetime.now(timezone.utc).isoformat()
        for name in EXPECTED_FILES[:-1]:
            _write_json(evidence_dir / name, _record(timestamp))
        _write_json(evidence_dir / "hash_manifest.json", _build_manifest(evidence_dir))

        result = validate_phase_evidence(evidence_dir)

        assert result["status"] == "PASS"
        assert result["production_status"] == "NO_GO"


def test_validate_phase_evidence_missing_file_aborts():
    with tempfile.TemporaryDirectory() as td:
        evidence_dir = Path(td)
        timestamp = datetime.now(timezone.utc).isoformat()
        _write_json(evidence_dir / "completion_report.json", _record(timestamp))

        result = validate_phase_evidence(evidence_dir)

        assert result["status"] == "ABORT"


def test_validate_phase_evidence_side_effect_violation_aborts():
    with tempfile.TemporaryDirectory() as td:
        evidence_dir = Path(td)
        timestamp = datetime.now(timezone.utc).isoformat()
        bad = _record(timestamp)
        bad["side_effect_policy"]["external_send"] = True
        for name in EXPECTED_FILES[:-1]:
            _write_json(evidence_dir / name, bad)
        _write_json(evidence_dir / "hash_manifest.json", _build_manifest(evidence_dir))

        result = validate_phase_evidence(evidence_dir)

        assert result["status"] == "ABORT"


def test_validate_phase_evidence_hash_mismatch_fails():
    with tempfile.TemporaryDirectory() as td:
        evidence_dir = Path(td)
        timestamp = datetime.now(timezone.utc).isoformat()
        for name in EXPECTED_FILES[:-1]:
            _write_json(evidence_dir / name, _record(timestamp))
        manifest = _build_manifest(evidence_dir)
        manifest["files"]["completion_report.json"] = "bad-hash"
        _write_json(evidence_dir / "hash_manifest.json", manifest)

        result = validate_phase_evidence(evidence_dir)

        assert result["status"] == "FAIL"


def test_validate_phase_evidence_warns_on_empty_tests():
    with tempfile.TemporaryDirectory() as td:
        evidence_dir = Path(td)
        timestamp = datetime.now(timezone.utc).isoformat()
        for name in EXPECTED_FILES[:-1]:
            _write_json(evidence_dir / name, _record(timestamp, tests_executed=[]))
        _write_json(evidence_dir / "hash_manifest.json", _build_manifest(evidence_dir))

        result = validate_phase_evidence(evidence_dir)

        assert result["status"] == "WARN"