import json
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import generate_phase_evidence_v1_completion_report as reporter


def test_generate_phase_evidence_v1_completion_report_creates_files_and_appends_log():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "reports" / "evidence").mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "evidence_append.log").write_text('{"timestamp_utc":"2026-05-23T00:00:00Z","event":"seed"}\n', encoding="utf-8")

        original_json = reporter.REPORT_JSON_PATH
        original_md = reporter.REPORT_MD_PATH
        original_index = reporter.INDEX_PATH
        original_history = reporter.HISTORY_PATH
        original_audit = reporter.AUDIT_REPORT_PATH
        original_dashboard = reporter.DASHBOARD_PATH
        original_log = reporter.APPEND_LOG_PATH
        reporter.REPORT_JSON_PATH = root / "reports" / "evidence" / "phase_evidence_v1_completion_report.json"
        reporter.REPORT_MD_PATH = root / "reports" / "evidence" / "phase_evidence_v1_completion_report.md"
        reporter.INDEX_PATH = root / "reports" / "evidence" / "index.json"
        reporter.HISTORY_PATH = root / "reports" / "evidence" / "approval_history.json"
        reporter.AUDIT_REPORT_PATH = root / "reports" / "evidence" / "approval_audit_report.json"
        reporter.DASHBOARD_PATH = root / "reports" / "evidence" / "dashboard.md"
        reporter.APPEND_LOG_PATH = root / "logs" / "evidence_append.log"
        try:
            report = reporter.generate_phase_evidence_v1_completion_report()
        finally:
            reporter.REPORT_JSON_PATH = original_json
            reporter.REPORT_MD_PATH = original_md
            reporter.INDEX_PATH = original_index
            reporter.HISTORY_PATH = original_history
            reporter.AUDIT_REPORT_PATH = original_audit
            reporter.DASHBOARD_PATH = original_dashboard
            reporter.APPEND_LOG_PATH = original_log

        assert report["overall_status"] == "PASS"
        assert (root / "reports" / "evidence" / "phase_evidence_v1_completion_report.json").exists()
        assert (root / "reports" / "evidence" / "phase_evidence_v1_completion_report.md").exists()
        lines = (root / "logs" / "evidence_append.log").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        event = json.loads(lines[-1])
        assert event["event"] == "evidence_v1_completion_report_generated"
        assert "sha256_manifest" in event


def test_generate_phase_evidence_v1_completion_report_has_expected_sections():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "reports" / "evidence").mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        (root / "logs" / "evidence_append.log").write_text("", encoding="utf-8")

        original_json = reporter.REPORT_JSON_PATH
        original_md = reporter.REPORT_MD_PATH
        original_index = reporter.INDEX_PATH
        original_history = reporter.HISTORY_PATH
        original_audit = reporter.AUDIT_REPORT_PATH
        original_dashboard = reporter.DASHBOARD_PATH
        original_log = reporter.APPEND_LOG_PATH
        reporter.REPORT_JSON_PATH = root / "reports" / "evidence" / "phase_evidence_v1_completion_report.json"
        reporter.REPORT_MD_PATH = root / "reports" / "evidence" / "phase_evidence_v1_completion_report.md"
        reporter.INDEX_PATH = root / "reports" / "evidence" / "index.json"
        reporter.HISTORY_PATH = root / "reports" / "evidence" / "approval_history.json"
        reporter.AUDIT_REPORT_PATH = root / "reports" / "evidence" / "approval_audit_report.json"
        reporter.DASHBOARD_PATH = root / "reports" / "evidence" / "dashboard.md"
        reporter.APPEND_LOG_PATH = root / "logs" / "evidence_append.log"
        try:
            reporter.generate_phase_evidence_v1_completion_report()
        finally:
            reporter.REPORT_JSON_PATH = original_json
            reporter.REPORT_MD_PATH = original_md
            reporter.INDEX_PATH = original_index
            reporter.HISTORY_PATH = original_history
            reporter.AUDIT_REPORT_PATH = original_audit
            reporter.DASHBOARD_PATH = original_dashboard
            reporter.APPEND_LOG_PATH = original_log

        md = (root / "reports" / "evidence" / "phase_evidence_v1_completion_report.md").read_text(encoding="utf-8")
        assert "## Completed Versions" in md
        assert "## Implemented Components" in md
        assert "## Verification Results" in md
        assert "## Operational Meaning" in md
        assert "## Restrictions" in md
        assert "## Next Candidates" in md