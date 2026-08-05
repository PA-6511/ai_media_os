import json
import tempfile
from pathlib import Path

from scripts.generate_phase5_draft_candidate_flow_report import generate_phase5_draft_candidate_flow_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validation_result() -> dict:
    return {
        "package_type": "exchange_connection_dry_run_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "overall_status": "WARN",
    }


def wordpress_draft_candidate_result() -> dict:
    return {
        "package_type": "wordpress_draft_candidate_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "PASS",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "human_review",
    }


def wordpress_draft_candidate_review_result() -> dict:
    return {
        "package_type": "wordpress_draft_candidate_review_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "APPROVE_DRY_RUN_ONLY",
        "status": "PASS",
        "next_step": "record_draft_candidate_approval_evidence",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def draft_candidate_approval_evidence() -> dict:
    return {
        "package_type": "draft_candidate_approval_evidence",
        "phase": "Phase 5-5",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "status": "PASS_DRY_RUN_ONLY",
        "decision": "APPROVE_DRY_RUN_ONLY",
        "review_status": "PASS",
        "review_next_step": "record_draft_candidate_approval_evidence",
        "allowed_next_step": "record_only_no_wordpress_write",
        "safety_flags": {
            "wordpress_write_executed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "github_actions_triggered": False,
            "slack_notification_executed": False,
        },
    }


def create_sources(tmpdir: Path) -> dict:
    paths = {
        "validation_result": tmpdir / "validation_result.json",
        "wordpress_draft_candidate_result": tmpdir / "wordpress_draft_candidate_result.json",
        "wordpress_draft_candidate_review_result": tmpdir / "wordpress_draft_candidate_review_result.json",
        "draft_candidate_approval_evidence": tmpdir / "draft_candidate_approval_evidence.json",
    }

    write_json(paths["validation_result"], validation_result())
    write_json(paths["wordpress_draft_candidate_result"], wordpress_draft_candidate_result())
    write_json(paths["wordpress_draft_candidate_review_result"], wordpress_draft_candidate_review_result())
    write_json(paths["draft_candidate_approval_evidence"], draft_candidate_approval_evidence())

    return paths


def test_generates_json_and_markdown_report():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"

        result = generate_phase5_draft_candidate_flow_report(sources, json_out, md_out)

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


def test_evidence_status_not_pass_dry_run_only_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = draft_candidate_approval_evidence()
        payload["status"] = "PASS"
        write_json(sources["draft_candidate_approval_evidence"], payload)

        result = generate_phase5_draft_candidate_flow_report(sources, tmpdir / "report.json", tmpdir / "report.md")
        assert result["status"] == "ABORT"


def test_execution_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = draft_candidate_approval_evidence()
        payload["execution"] = "LIVE"
        write_json(sources["draft_candidate_approval_evidence"], payload)

        result = generate_phase5_draft_candidate_flow_report(sources, tmpdir / "report.json", tmpdir / "report.md")
        assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = validation_result()
        payload["auto_post"] = True
        write_json(sources["validation_result"], payload)

        result = generate_phase5_draft_candidate_flow_report(sources, tmpdir / "report.json", tmpdir / "report.md")
        assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        payload = wordpress_draft_candidate_result()
        payload["wordpress_write_executed"] = True
        write_json(sources["wordpress_draft_candidate_result"], payload)

        result = generate_phase5_draft_candidate_flow_report(sources, tmpdir / "report.json", tmpdir / "report.md")
        assert result["status"] == "ABORT"


def test_existing_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"
        json_out.write_text("{}", encoding="utf-8")

        result = generate_phase5_draft_candidate_flow_report(sources, json_out, md_out)
        assert result["status"] == "ABORT"
