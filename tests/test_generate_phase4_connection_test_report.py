import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase4_connection_test_report import generate_phase4_connection_test_report


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validation_result():
    return {
        "package_type": "exchange_connection_dry_run_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "human_review_required": True,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "overall_status": "WARN",
    }


def review_required():
    return {
        "package_type": "human_review_request",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "review_status": "REQUIRED",
        "overall_status": "WARN",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def human_decision_result():
    return {
        "package_type": "human_decision_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "APPROVE_DRY_RUN_ONLY",
        "status": "PASS",
        "next_step": "record_dry_run_evidence",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def dry_run_approval_evidence():
    return {
        "package_type": "dry_run_approval_evidence",
        "phase": "Phase 4-7",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "status": "PASS",
        "decision": "APPROVE_DRY_RUN_ONLY",
        "decision_status": "PASS",
        "decision_next_step": "record_dry_run_evidence",
        "allowed_next_step": "record_only_no_production_action",
        "safety_flags": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
    }


def create_sources(tmpdir: Path):
    paths = {
        "validation_result": tmpdir / "validation_result.json",
        "review_required": tmpdir / "review_required.json",
        "human_decision_result": tmpdir / "human_decision_result.json",
        "dry_run_approval_evidence": tmpdir / "dry_run_approval_evidence.json",
    }

    write_json(paths["validation_result"], validation_result())
    write_json(paths["review_required"], review_required())
    write_json(paths["human_decision_result"], human_decision_result())
    write_json(paths["dry_run_approval_evidence"], dry_run_approval_evidence())

    return paths


def test_generates_json_and_markdown_report():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"

        result = generate_phase4_connection_test_report(sources, json_out, md_out)

        assert result["status"] == "PASS"
        assert result["completion_status"] == "PASS_DRY_RUN_ONLY"
        assert result["production_status"] == "NO_GO"
        assert json_out.exists()
        assert md_out.exists()

        report = json.loads(json_out.read_text(encoding="utf-8"))
        assert report["completion_status"] == "PASS_DRY_RUN_ONLY"
        assert report["production_status"] == "NO_GO"

        md = md_out.read_text(encoding="utf-8")
        assert "PASS_DRY_RUN_ONLY" in md
        assert "NO_GO" in md


def test_evidence_status_not_pass_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = dry_run_approval_evidence()
        payload["status"] = "WARN"
        write_json(sources["dry_run_approval_evidence"], payload)

        result = generate_phase4_connection_test_report(
            sources,
            tmpdir / "report.json",
            tmpdir / "report.md",
        )

        assert result["status"] == "ABORT"


def test_execution_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = dry_run_approval_evidence()
        payload["execution"] = "LIVE"
        write_json(sources["dry_run_approval_evidence"], payload)

        result = generate_phase4_connection_test_report(
            sources,
            tmpdir / "report.json",
            tmpdir / "report.md",
        )

        assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = validation_result()
        payload["auto_post"] = True
        write_json(sources["validation_result"], payload)

        result = generate_phase4_connection_test_report(
            sources,
            tmpdir / "report.json",
            tmpdir / "report.md",
        )

        assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = review_required()
        payload["wordpress_write_executed"] = True
        write_json(sources["review_required"], payload)

        result = generate_phase4_connection_test_report(
            sources,
            tmpdir / "report.json",
            tmpdir / "report.md",
        )

        assert result["status"] == "ABORT"


def test_existing_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"
        json_out.write_text("{}", encoding="utf-8")

        result = generate_phase4_connection_test_report(sources, json_out, md_out)

        assert result["status"] == "ABORT"
