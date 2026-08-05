import json
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import export_phase_evidence_pack as exporter


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_sources(root: Path) -> dict[str, Path]:
    reports = root / "reports" / "evidence"
    _write_text(reports / "index.json", json.dumps({"schema_version": "x", "updated_at_utc": "2026-05-23T00:00:00Z", "entries": []}, indent=2))
    _write_text(reports / "approval_history.json", json.dumps({"schema_version": "x", "updated_at_utc": "2026-05-23T00:00:00Z", "entries": []}, indent=2))
    _write_text(reports / "approval_audit_report.json", json.dumps({"schema_version": "x"}, indent=2))
    _write_text(reports / "approval_audit_report.md", "# report\n")
    _write_text(root / "logs" / "evidence_append.log", '{"event":"seed"}\n')
    _write_text(root / "schemas" / "phase_evidence.schema.json", json.dumps({"schema_version": "x"}, indent=2))
    _write_text(root / "prompts" / "phase_evidence_compact_v1.txt", "compact\n")
    _write_text(root / "docs" / "checklists" / "phase_evidence_checklist_v1.md", "checklist\n")
    return {
        "reports_evidence": reports,
        "logs": root / "logs" / "evidence_append.log",
        "schemas": root / "schemas" / "phase_evidence.schema.json",
        "prompts": root / "prompts" / "phase_evidence_compact_v1.txt",
        "docs_checklists": root / "docs" / "checklists" / "phase_evidence_checklist_v1.md",
    }


def test_export_phase_evidence_pack_creates_pack_and_manifest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sources = _make_sources(root)
        export_root = root / "exports" / "phase_evidence"
        log_path = root / "logs" / "evidence_append.log"

        result = exporter.export_phase_evidence_pack(
            export_root=export_root,
            sources=sources,
            timestamp_utc="2026-05-23T06:30:00Z",
            log_path=log_path,
        )

        pack_dir = result["pack_dir"]
        assert pack_dir.exists()
        assert result["manifest_path"].exists()
        assert result["readme_path"].exists()
        manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
        assert manifest["source_paths"]
        assert manifest["sha256_manifest"]
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        event = json.loads(lines[-1])
        assert event["event"] == "phase_evidence_export_pack_generated"
        assert event["status"] == "PASS"


def test_export_phase_evidence_pack_warns_on_missing_sources():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sources = _make_sources(root)
        sources["schemas"] = root / "schemas" / "missing_phase_evidence.schema.json"
        export_root = root / "exports" / "phase_evidence"
        log_path = root / "logs" / "evidence_append.log"

        result = exporter.export_phase_evidence_pack(
            export_root=export_root,
            sources=sources,
            timestamp_utc="2026-05-23T06:31:00Z",
            log_path=log_path,
        )

        assert result["status"] == "WARN"
        assert result["missing_sources"]
        manifest = json.loads(result["manifest_path"].read_text(encoding="utf-8"))
        assert manifest["status"] == "WARN"
        assert manifest["missing_sources"]


def test_export_phase_evidence_pack_does_not_overwrite_existing_pack():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sources = _make_sources(root)
        export_root = root / "exports" / "phase_evidence"
        log_path = root / "logs" / "evidence_append.log"

        first = exporter.export_phase_evidence_pack(
            export_root=export_root,
            sources=sources,
            timestamp_utc="2026-05-23T06:32:00Z",
            log_path=log_path,
        )
        second = exporter.export_phase_evidence_pack(
            export_root=export_root,
            sources=sources,
            timestamp_utc="2026-05-23T06:32:00Z",
            log_path=log_path,
        )

        assert first["pack_dir"] != second["pack_dir"]
        assert first["pack_dir"].exists()
        assert second["pack_dir"].exists()
        assert first["manifest_path"].exists()
        assert second["manifest_path"].exists()