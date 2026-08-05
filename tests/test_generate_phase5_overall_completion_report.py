import json
import tempfile
from pathlib import Path

from scripts.generate_phase5_overall_completion_report import generate_phase5_overall_completion_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def phase5_1_connection_config() -> dict:
    return {
        "active_connector": "LOCAL_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": False,
    }


def phase5_1_decision_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Decision Package (Real Data, Phase 5-1)",
        "properties": {},
        "required": ["self_builder_origin"],
    }


def phase5_2_validation_result() -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "overall_status": "WARN",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def phase5_3_draft_candidate_result() -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "PASS",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def phase5_4_review_result() -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "decision": "APPROVE_DRY_RUN_ONLY",
        "status": "PASS",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def phase5_5_approval_evidence() -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": "PASS_DRY_RUN_ONLY",
        "decision": "APPROVE_DRY_RUN_ONLY",
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


def phase5_6_flow_report() -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "completion_status": "PASS_DRY_RUN_ONLY",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def phase5_7_quality_validation(status: str = "WARN") -> dict:
    return {
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "status": status,
        "warnings": ["sample warn"] if status == "WARN" else [],
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def create_sources(tmpdir: Path) -> dict:
    paths = {
        "phase5_1_connection_config": tmpdir / "self_builder_connection.json",
        "phase5_1_decision_schema": tmpdir / "decision_schema.json",
        "phase5_2_validation_result": tmpdir / "validation_result.json",
        "phase5_3_draft_candidate_result": tmpdir / "draft_candidate_result.json",
        "phase5_4_review_result": tmpdir / "review_result.json",
        "phase5_5_approval_evidence": tmpdir / "approval_evidence.json",
        "phase5_6_flow_report": tmpdir / "flow_report.json",
        "phase5_7_quality_validation": tmpdir / "quality_validation.json",
    }

    write_json(paths["phase5_1_connection_config"], phase5_1_connection_config())
    write_json(paths["phase5_1_decision_schema"], phase5_1_decision_schema())
    write_json(paths["phase5_2_validation_result"], phase5_2_validation_result())
    write_json(paths["phase5_3_draft_candidate_result"], phase5_3_draft_candidate_result())
    write_json(paths["phase5_4_review_result"], phase5_4_review_result())
    write_json(paths["phase5_5_approval_evidence"], phase5_5_approval_evidence())
    write_json(paths["phase5_6_flow_report"], phase5_6_flow_report())
    write_json(paths["phase5_7_quality_validation"], phase5_7_quality_validation("WARN"))

    return paths


def test_generate_report_pass_with_warn_status():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"

        result = generate_phase5_overall_completion_report(sources, json_out, md_out)
        assert result["status"] == "PASS"
        assert result["completion_status"] == "PASS_DRY_RUN_ONLY_WITH_WARN"
        assert result["production_status"] == "NO_GO"
        assert json_out.exists()
        assert md_out.exists()

        report = json.loads(json_out.read_text(encoding="utf-8"))
        assert report["completion_status"] == "PASS_DRY_RUN_ONLY_WITH_WARN"
        assert report["wordpress_draft_creation"] == "NO_GO"


def test_quality_fail_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        write_json(sources["phase5_7_quality_validation"], phase5_7_quality_validation("FAIL"))

        result = generate_phase5_overall_completion_report(sources, tmpdir / "r.json", tmpdir / "r.md")
        assert result["status"] == "ABORT"


def test_execution_live_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        live = phase5_5_approval_evidence()
        live["execution"] = "LIVE"
        write_json(sources["phase5_5_approval_evidence"], live)

        result = generate_phase5_overall_completion_report(sources, tmpdir / "r.json", tmpdir / "r.md")
        assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        v = phase5_2_validation_result()
        v["auto_post"] = True
        write_json(sources["phase5_2_validation_result"], v)

        result = generate_phase5_overall_completion_report(sources, tmpdir / "r.json", tmpdir / "r.md")
        assert result["status"] == "ABORT"


def test_existing_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        sources = create_sources(tmpdir)
        json_out = tmpdir / "report.json"
        md_out = tmpdir / "report.md"
        json_out.write_text("{}", encoding="utf-8")

        result = generate_phase5_overall_completion_report(sources, json_out, md_out)
        assert result["status"] == "ABORT"
