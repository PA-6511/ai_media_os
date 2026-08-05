import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_phase_dashboard import generate_phase_dashboard


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _index_entry(root: Path, phase_dir: Path, status: str = "PASS", approval_state: str = "PENDING") -> dict:
    return {
        "phase": phase_dir.name.replace("_", " ").replace("phase", "Phase ").replace("6 1", "6-1"),
        "component": phase_dir.name.split("_", 2)[-1],
        "status": status,
        "evidence_dir": str(phase_dir.relative_to(root)),
        "completion_report": str((phase_dir / "completion_report.json").relative_to(root)),
        "approval_state": approval_state,
        "sha256": "index-placeholder",
    }


def _completion_report(phase: str, component: str, approval_state: str) -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "component": component,
        "mode": "DRY_RUN",
        "status": "PASS",
        "human_review_required": True,
        "production_status": "NO_GO",
        "summary": "ok",
        "reason": "ok",
        "novelty": ["dashboard test"],
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


def _write_audit_report(path: Path, summary: dict, entries: list[dict]) -> None:
    _write_json(
        path,
        {
            "schema_version": "phase_approval_audit_report_v1.5",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if summary.get("unresolved_count", 0) == 0 else "WARN",
            "summary": summary,
            "entries": entries,
            "unresolved_entries": [entry for entry in entries if entry["approval_state"] != "APPROVED"],
            "source_index": "reports/evidence/index.json",
            "source_approval_history": "reports/evidence/approval_history.json",
        },
    )


def test_generate_phase_dashboard_empty_data():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        audit_path = evidence_root / "approval_audit_report.json"
        dashboard_path = evidence_root / "dashboard.md"
        _write_index(index_path, [])
        _write_history(history_path, [])
        _write_audit_report(
            audit_path,
            {
                "total_count": 0,
                "approved_count": 0,
                "pending_count": 0,
                "request_fix_count": 0,
                "rejected_count": 0,
                "aborted_count": 0,
                "unknown_count": 0,
                "unresolved_count": 0,
            },
            [],
        )

        result = generate_phase_dashboard(
            index_path=index_path,
            history_path=history_path,
            audit_report_path=audit_path,
            dashboard_path=dashboard_path,
        )

        assert result["status"] == "PASS"
        assert dashboard_path.exists()
        content = dashboard_path.read_text(encoding="utf-8")
        assert "# Phase Evidence Dashboard" in content


def test_generate_phase_dashboard_mixed_states():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_a = evidence_root / "phase6_1_core_validator"
        phase_b = evidence_root / "phase6_2_wordpress_gate"
        phase_c = evidence_root / "phase6_3_block_ai"
        for phase_dir in [phase_a, phase_b, phase_c]:
            phase_dir.mkdir(parents=True, exist_ok=True)

        _write_json(phase_a / "completion_report.json", _completion_report("Phase 6-1", "core_validator", "APPROVED"))
        _write_json(phase_b / "completion_report.json", _completion_report("Phase 6-2", "wordpress_gate", "PENDING"))
        _write_json(phase_c / "completion_report.json", _completion_report("Phase 6-3", "block_ai", "REJECTED"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        audit_path = evidence_root / "approval_audit_report.json"
        dashboard_path = evidence_root / "dashboard.md"

        _write_index(
            index_path,
            [
                _index_entry(root, phase_a, "PASS", "APPROVED"),
                _index_entry(root, phase_b, "PASS", "PENDING"),
                _index_entry(root, phase_c, "PASS", "REJECTED"),
            ],
        )
        _write_history(
            history_path,
            [
                {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "phase": "Phase 6-1", "component": "core_validator", "approval_state": "APPROVED", "previous_approval_state": "UNKNOWN", "status": "PASS", "evidence_dir": str(phase_a.relative_to(root)), "source": "approval_evidence.json"},
                {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "phase": "Phase 6-2", "component": "wordpress_gate", "approval_state": "PENDING", "previous_approval_state": "UNKNOWN", "status": "PASS", "evidence_dir": str(phase_b.relative_to(root)), "source": "completion_report.json"},
                {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "phase": "Phase 6-3", "component": "block_ai", "approval_state": "REJECTED", "previous_approval_state": "UNKNOWN", "status": "PASS", "evidence_dir": str(phase_c.relative_to(root)), "source": "approval_evidence.json"},
            ],
        )
        _write_audit_report(
            audit_path,
            {
                "total_count": 3,
                "approved_count": 1,
                "pending_count": 1,
                "request_fix_count": 0,
                "rejected_count": 1,
                "aborted_count": 0,
                "unknown_count": 0,
                "unresolved_count": 2,
            },
            [
                {"phase": "Phase 6-1", "component": "core_validator", "approval_state": "APPROVED", "source": "approval_history.json", "status": "resolved", "completion_report": str(phase_a / "completion_report.json"), "evidence_dir": str(phase_a.relative_to(root))},
                {"phase": "Phase 6-2", "component": "wordpress_gate", "approval_state": "PENDING", "source": "approval_history.json", "status": "unresolved", "completion_report": str(phase_b / "completion_report.json"), "evidence_dir": str(phase_b.relative_to(root))},
                {"phase": "Phase 6-3", "component": "block_ai", "approval_state": "REJECTED", "source": "approval_history.json", "status": "unresolved", "completion_report": str(phase_c / "completion_report.json"), "evidence_dir": str(phase_c.relative_to(root))},
            ],
        )

        result = generate_phase_dashboard(
            index_path=index_path,
            history_path=history_path,
            audit_report_path=audit_path,
            dashboard_path=dashboard_path,
        )

        assert result["status"] == "WARN"
        assert result["summary"]["unresolved_count"] == 2
        content = dashboard_path.read_text(encoding="utf-8")
        assert "Phase 6-1" in content
        assert "APPROVED" in content
        assert "PENDING" in content
        assert "REJECTED" in content


def test_generate_phase_dashboard_falls_back_to_index_state():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence_root = root / "reports" / "evidence"
        phase_dir = evidence_root / "phase6_1_core_validator"
        phase_dir.mkdir(parents=True, exist_ok=True)
        _write_json(phase_dir / "completion_report.json", _completion_report("Phase 6-1", "core_validator", "UNKNOWN"))

        index_path = evidence_root / "index.json"
        history_path = evidence_root / "approval_history.json"
        audit_path = evidence_root / "approval_audit_report.json"
        dashboard_path = evidence_root / "dashboard.md"
        _write_index(index_path, [_index_entry(root, phase_dir, "PASS", "APPROVED")])
        _write_history(history_path, [])
        _write_audit_report(
            audit_path,
            {
                "total_count": 1,
                "approved_count": 1,
                "pending_count": 0,
                "request_fix_count": 0,
                "rejected_count": 0,
                "aborted_count": 0,
                "unknown_count": 0,
                "unresolved_count": 0,
            },
            [
                {"phase": "Phase 6-1", "component": "core_validator", "approval_state": "APPROVED", "source": "index.json", "status": "resolved", "completion_report": str(phase_dir / "completion_report.json"), "evidence_dir": str(phase_dir.relative_to(root))},
            ],
        )

        result = generate_phase_dashboard(
            index_path=index_path,
            history_path=history_path,
            audit_report_path=audit_path,
            dashboard_path=dashboard_path,
        )

        assert result["status"] == "PASS"
        assert result["rows"][0]["approval_state"] == "APPROVED"
        assert result["rows"][0]["source"] == "index.json"