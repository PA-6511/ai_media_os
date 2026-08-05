import json
import tempfile
from pathlib import Path

from scripts.generate_phase69_preparation_approval_report import generate_phase69_preparation_approval_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_phase68_report() -> dict:
    return {
        "package_type": "phase68_preparation_review_report",
        "phase": "Phase 68",
        "title": "Phase 68 Limited Dry-Run Preparation Review Report",
        "status": "PASS",
        "review_status": "PASS",
        "source_report": "exchange/logs/phase67_preparation_evidence_report.json",
        "source_report_type": "limited_dry_run_preparation_evidence_package_report",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "review_package": {
            "package_scope": "limited_dry_run_preparation_review_package_only",
            "does_not_execute": True,
            "review_target": "phase67_preparation_evidence_report",
            "status": "PREPARATION_REVIEW_REPORT_READY",
        },
        "review_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "PREPARATION_REVIEW_CONTROLS_READY",
        },
        "review_evidence_checks": {
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
            "status": "PREPARATION_REVIEW_EVIDENCE_CHECKS_READY",
        },
        "manual_review_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE69_READINESS_REVIEW_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_PREPARATION_REVIEW_GATE_READY",
        },
        "phase69_readiness": {
            "readiness_status": "READY_FOR_PHASE69_READINESS_REVIEW_ONLY",
            "approval_package_scope": "limited_dry_run_preparation_approval_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "all_checks_passed": True,
        "next_step": "decide_whether_to_start_phase69_limited_dry_run_preparation_approval_package",
    }


def test_generate_phase69_report_pass():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase68.json"
        output_path = tmpdir / "phase69.json"
        write_json(input_path, sample_phase68_report())

        result = generate_phase69_preparation_approval_report(input_path, output_path)

        assert result["status"] == "PASS"
        assert result["report_generated"] is True
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["status"] == "PASS"
        assert report["mode"] == "DRY_RUN"
        assert report["human_approval_required"] is True
        assert report["can_execute"] is False
        assert report["execute_allowed"] is False
        assert report["phase70_readiness"]["readiness_status"] == "READY_FOR_PHASE70_PLANNING_ONLY"


def test_generate_phase69_report_aborts_for_live_like_flag():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase68.json"
        output_path = tmpdir / "phase69.json"
        payload = sample_phase68_report()
        payload["execute_allowed"] = True
        write_json(input_path, payload)

        result = generate_phase69_preparation_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_generate_phase69_report_aborts_for_missing_required_evidence():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase68.json"
        output_path = tmpdir / "phase69.json"
        payload = sample_phase68_report()
        payload["review_evidence_checks"]["required_evidence"] = [
            "phase66_go_no_go_report_reference"
        ]
        write_json(input_path, payload)

        result = generate_phase69_preparation_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"


def test_generate_phase69_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase68.json"
        output_path = tmpdir / "phase69.json"
        write_json(input_path, sample_phase68_report())
        output_path.write_text("{}", encoding="utf-8")

        result = generate_phase69_preparation_approval_report(input_path, output_path)

        assert result["status"] == "ABORT"