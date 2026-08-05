import json
import tempfile
from pathlib import Path

from scripts.generate_phase76_limited_dry_run_rollback_plan_report import generate_phase76_limited_dry_run_rollback_plan_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_phase75_report() -> dict:
    return {
        "package_type": "phase75_limited_dry_run_fixture_plan_report",
        "phase": "Phase 75",
        "title": "Phase 75 Limited Dry-Run Fixture Plan Report",
        "status": "PASS",
        "fixture_plan_status": "PASS",
        "source_report": "exchange/logs/phase74_limited_dry_run_sandbox_plan_report.json",
        "source_report_type": "phase74_limited_dry_run_sandbox_plan_report",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "fixture_plan_package": {
            "package_scope": "limited_dry_run_fixture_plan_package_only",
            "does_not_execute": True,
            "fixture_plan_target": "phase74_limited_dry_run_sandbox_plan_report",
            "status": "LIMITED_DRY_RUN_FIXTURE_PLAN_PACKAGE_READY",
        },
        "fixture_plan_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "LIMITED_DRY_RUN_FIXTURE_PLAN_CONTROLS_READY",
        },
        "fixture_plan_evidence_checks": {
            "evidence_required": True,
            "required_evidence": [
                "phase66_go_no_go_report_reference",
                "preparation_scope_statement",
                "target_files_manifest",
                "sandbox_scope_confirmation",
                "single_file_scope_confirmation",
                "dry_run_mode_confirmation",
                "non_execution_confirmation",
            ],
            "missing_evidence_blocks_progress": True,
            "does_not_execute": True,
            "status": "LIMITED_DRY_RUN_FIXTURE_PLAN_EVIDENCE_CHECKS_READY",
        },
        "manual_fixture_plan_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE76_PLANNING_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_LIMITED_DRY_RUN_FIXTURE_PLAN_GATE_READY",
        },
        "phase76_readiness": {
            "readiness_status": "READY_FOR_PHASE76_PLANNING_ONLY",
            "planning_package_scope": "limited_dry_run_rollback_planning_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "all_checks_passed": True,
        "next_step": "decide_whether_to_start_phase76_limited_dry_run_rollback_planning_package",
    }


def test_generate_phase76_report_pass():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase75.json"
        output_path = tmpdir / "phase76.json"
        write_json(input_path, sample_phase75_report())

        result = generate_phase76_limited_dry_run_rollback_plan_report(input_path, output_path)

        assert result["status"] == "PASS"
        assert result["report_generated"] is True
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["status"] == "PASS"
        assert report["mode"] == "DRY_RUN"
        assert report["human_approval_required"] is True
        assert report["can_execute"] is False
        assert report["execute_allowed"] is False
        assert report["phase77_readiness"]["readiness_status"] == "READY_FOR_PHASE77_PLANNING_ONLY"


def test_generate_phase76_report_aborts_for_live_like_flag():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase75.json"
        output_path = tmpdir / "phase76.json"
        payload = sample_phase75_report()
        payload["execute_allowed"] = True
        write_json(input_path, payload)

        result = generate_phase76_limited_dry_run_rollback_plan_report(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_generate_phase76_report_aborts_for_missing_required_evidence():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase75.json"
        output_path = tmpdir / "phase76.json"
        payload = sample_phase75_report()
        payload["fixture_plan_evidence_checks"]["required_evidence"] = [
            "phase66_go_no_go_report_reference"
        ]
        write_json(input_path, payload)

        result = generate_phase76_limited_dry_run_rollback_plan_report(input_path, output_path)

        assert result["status"] == "ABORT"


def test_generate_phase76_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase75.json"
        output_path = tmpdir / "phase76.json"
        write_json(input_path, sample_phase75_report())
        output_path.write_text("{}", encoding="utf-8")

        result = generate_phase76_limited_dry_run_rollback_plan_report(input_path, output_path)

        assert result["status"] == "ABORT"
