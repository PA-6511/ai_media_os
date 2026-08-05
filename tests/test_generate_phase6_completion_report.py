import json
import tempfile
from pathlib import Path

from scripts.generate_phase6_completion_report import build_report, build_md, run_report

SUBPHASE_FILES = [
    "phase6_1_design_validation_result.json",
    "phase6_2_preflight_gate_validation_result.json",
    "phase6_3_release_decision_rules_validation_result.json",
    "phase6_4_controlled_unlock_plan_validation_result.json",
    "phase6_5_execution_spec_validation_result.json",
    "phase6_6_pre_execution_rehearsal_validation_result.json",
    "phase6_7_unlock_readiness_decision_result.json",
    "phase6_8_final_unlock_go_no_go_result.json",
    "phase6_9_manual_unlock_protocol_validation_result.json",
]


def seed_logs(logs_dir: Path, status: str = "PASS"):
    logs_dir.mkdir(parents=True, exist_ok=True)
    for fname in SUBPHASE_FILES:
        (logs_dir / fname).write_text(
            json.dumps({"status": status}, ensure_ascii=False),
            encoding="utf-8",
        )


def test_all_pass_gives_complete_design_only():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td)
        seed_logs(logs, "PASS")
        report = build_report(logs)
        assert report["overall_status"] == "COMPLETE_DESIGN_ONLY"
        assert report["production_status"] == "NO_GO"
        assert report["wordpress_draft_creation"] == "NO_GO"
        assert report["real_write_enabled"] is False
        assert report["manual_unlock_status"] == "DESIGN_ONLY"
        assert report["wordpress_write_executed"] is False


def test_any_fail_gives_incomplete():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td)
        seed_logs(logs, "PASS")
        (logs / "phase6_5_execution_spec_validation_result.json").write_text(
            json.dumps({"status": "ABORT"}), encoding="utf-8"
        )
        report = build_report(logs)
        assert report["overall_status"] == "INCOMPLETE"


def test_missing_file_gives_incomplete():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td)
        seed_logs(logs, "PASS")
        (logs / "phase6_9_manual_unlock_protocol_validation_result.json").unlink()
        report = build_report(logs)
        assert report["overall_status"] == "INCOMPLETE"


def test_subphase_count_is_nine():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td)
        seed_logs(logs, "PASS")
        report = build_report(logs)
        assert len(report["subphase_results"]) == 9


def test_md_contains_all_phases():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td)
        seed_logs(logs, "PASS")
        report = build_report(logs)
        md = build_md(report)
        for tag in ["6-1", "6-2", "6-3", "6-4", "6-5", "6-6", "6-7", "6-8", "6-9"]:
            assert f"Phase {tag}" in md
        assert "NO_GO" in md
        assert "COMPLETE_DESIGN_ONLY" in md


def test_run_report_writes_both_files():
    with tempfile.TemporaryDirectory() as td:
        logs = Path(td) / "logs"
        out_json = Path(td) / "report.json"
        out_md = Path(td) / "report.md"
        seed_logs(logs, "PASS")

        report = run_report(logs, out_json, out_md)

        assert out_json.exists()
        assert out_md.exists()
        saved = json.loads(out_json.read_text(encoding="utf-8"))
        assert saved["overall_status"] == "COMPLETE_DESIGN_ONLY"
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        md_text = out_md.read_text(encoding="utf-8")
        assert "Phase 6-9" in md_text
        assert report["overall_status"] == "COMPLETE_DESIGN_ONLY"
