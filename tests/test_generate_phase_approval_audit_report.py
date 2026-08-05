import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_phase_approval_audit_report import generate_phase_approval_audit_report


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
        "novelty": ["approval audit test"],
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


def _index_entry(root: Path, phase_dir: Path, state: str = "PENDING") -> dict:
    return {
        "phase": "Phase 6-1",
        "component": "xxx",
        "status": "PASS",
        "evidence_dir": str(phase_dir.relative_to(root)),
        "completion_report": str((phase_dir / "completion_report.json").relative_to(root)),
        "approval_state": state,
        "sha256": "index-placeholder",
    }


def _write_index(index_path: Path, entries: list[dict]) -> None:
    _write_json(
        index_path,
        {
            "schema_version": "phase_evidence_index_v1.1",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if entries else "WARN",
            "reason": "index updated from evidence directories" if entries else "no phase evidence entries found",
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


def test_generate_phase_approval_audit_report_passes_when_all_approved():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)
        _write_json(phase_dir / "completion_report.json", _completion_report("APPROVED"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        report_json_path = evidence_root / "approval_audit_report.json"
        report_md_path = evidence_root / "approval_audit_report.md"
        log_path = root / "logs" / "evidence_append.log"
        _write_index(index_path, [_index_entry(root, phase_dir, "APPROVED")])
        _write_history(history_path, [
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase": "Phase 6-1",
                "component": "xxx",
                "approval_state": "APPROVED",
                "previous_approval_state": "UNKNOWN",
                "status": "PASS",
                "evidence_dir": str(phase_dir.relative_to(root)),
                "source": "approval_evidence.json",
            }
        ])
        _write_log(log_path, [])

        result = generate_phase_approval_audit_report(
            index_path=index_path,
            history_path=history_path,
            report_json_path=report_json_path,
            report_md_path=report_md_path,
            log_path=log_path,
        )

        assert result["status"] == "PASS"
        assert result["summary"]["approved_count"] == 1
        assert result["summary"]["unresolved_count"] == 0
        assert report_json_path.exists()
        assert report_md_path.exists()
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event"] == "approval_audit_report_generated"
        assert event["entries_count"] == 1
        assert event["warnings_count"] == 0


def test_generate_phase_approval_audit_report_warns_on_unresolved():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_xxx"
        phase_dir.mkdir(parents=True, exist_ok=True)
        _write_json(phase_dir / "completion_report.json", _completion_report("PENDING"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        report_json_path = evidence_root / "approval_audit_report.json"
        report_md_path = evidence_root / "approval_audit_report.md"
        log_path = root / "logs" / "evidence_append.log"
        _write_index(index_path, [_index_entry(root, phase_dir, "PENDING")])
        _write_history(history_path, [])
        _write_log(log_path, [])

        result = generate_phase_approval_audit_report(
            index_path=index_path,
            history_path=history_path,
            report_json_path=report_json_path,
            report_md_path=report_md_path,
            log_path=log_path,
        )

        assert result["status"] == "WARN"
        assert result["summary"]["pending_count"] == 1
        assert result["summary"]["unresolved_count"] == 1


def test_generate_phase_approval_audit_report_fails_on_bad_history_json():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        index_path = evidence_root / "index.json"
        index_path.write_text("{invalid json", encoding="utf-8")
        history_path = evidence_root / "approval_history.json"
        history_path.write_text("{invalid json", encoding="utf-8")
        log_path = root / "logs" / "evidence_append.log"
        _write_log(log_path, [])

        try:
            generate_phase_approval_audit_report(
                index_path=index_path,
                history_path=history_path,
                report_json_path=evidence_root / "approval_audit_report.json",
                report_md_path=evidence_root / "approval_audit_report.md",
                log_path=log_path,
            )
            assert False, "expected failure"
        except ValueError:
            assert True