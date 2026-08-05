import json
import tempfile
from pathlib import Path

from scripts.generate_phase71_preparation_final_approval_report import generate_phase71_preparation_final_approval_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_phase70_report() -> dict:
    return {
        "package_type": "phase70_preparation_final_review_report",
        "phase": "Phase 70",
        "title": "Phase 70 Limited Dry-Run Preparation Final Review Report",
        "status": "PASS",
        "final_review_status": "PASS",
        "source_report": "exchange/logs/phase69_preparation_approval_report.json",
        "source_report_type": "phase69_preparation_approval_report",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "final_review_package": {
            "package_scope": "limited_dry_run_preparation_final_review_package_only",
            "does_not_execute": True,
            "final_review_target": "phase69_preparation_approval_report",
            "status": "PREPARATION_FINAL_REVIEW_PACKAGE_READY",
        },
        "final_review_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "PREPARATION_FINAL_REVIEW_CONTROLS_READY",
        },
        "final_review_evidence_checks": {
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
            "status": "PREPARATION_FINAL_REVIEW_EVIDENCE_CHECKS_READY",
        },
        "manual_final_review_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE71_PLANNING_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_PREPARATION_FINAL_REVIEW_GATE_READY",
        },
        "phase71_readiness": {
            "readiness_status": "READY_FOR_PHASE71_PLANNING_ONLY",
            "planning_package_scope": "limited_dry_run_preparation_planning_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "all_checks_passed": True,
        "next_step": "decide_whether_to_start_phase71_limited_dry_run_preparation_planning_package",
    }


def test_generate_phase71_report_pass():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase70.json"
        output_path = tmpdir / "phase71.json"
        write_json(input_path, sample_phase70_report())

        result = generate_phase71_preparation_final_approval_report(input_path, output_path)

        assert result["status"] == "PASS"
        assert result["report_generated"] is True
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["status"] == "PASS"
        assert report["mode"] == "DRY_RUN"
        assert report["human_approval_required"] is True
        assert report["can_execute"] is False
        assert report["execute_allowed"] is False
        assert report["phase72_readiness"]["readiness_status"] == "READY_FOR_PHASE72_PLANNING_ONLY"


def test_generate_phase71_report_aborts_for_live_like_flag():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase70.json"
        output_path = tmpdir / "phase71.json"
        payload = sample_phase70_report()
        payload["execute_allowed"] = True
        write_json(input_path, payload)

        result = generate_phase71_preparation_final_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_generate_phase71_report_aborts_for_missing_required_evidence():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase70.json"
        output_path = tmpdir / "phase71.json"
        payload = sample_phase70_report()
        payload["final_review_evidence_checks"]["required_evidence"] = [
            "phase66_go_no_go_report_reference"
        ]
        write_json(input_path, payload)

        result = generate_phase71_preparation_final_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"


def test_generate_phase71_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase70.json"
        output_path = tmpdir / "phase71.json"
        write_json(input_path, sample_phase70_report())
        output_path.write_text("{}", encoding="utf-8")

        result = generate_phase71_preparation_final_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"
