import json
import tempfile
from pathlib import Path

from scripts.generate_phase68_preparation_review_report import generate_phase68_preparation_review_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_phase67_report() -> dict:
    return {
        "phase": "67",
        "report_type": "limited_dry_run_preparation_evidence_package_report",
        "human_approval_required": True,
        "readiness_status": "READY_FOR_PHASE68_PLANNING_ONLY",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "prepare_phase68_limited_dry_run_preparation_evidence_review",
        "policy_result": {
            "policy_status": "PASS",
            "reasons": [],
        },
        "preparation_evidence_package": {
            "phase": 67,
            "mode": "DRY_RUN",
            "human_approval_required": True,
            "package_scope": "limited_dry_run_preparation_evidence_package_design_only",
            "can_execute": False,
            "execute_allowed": False,
            "max_files_to_execute": 1,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "status": "PREPARATION_EVIDENCE_PACKAGE_READY",
            "next_step": "build_preparation_controls",
        },
        "preparation_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "execute_allowed": False,
            "preparation_controls_does_not_execute": True,
            "status": "PREPARATION_CONTROLS_READY",
        },
        "preparation_evidence_requirements": {
            "evidence_required": True,
            "missing_evidence_blocks_progress": True,
            "required_evidence": [
                "phase66_go_no_go_report_reference",
                "preparation_scope_statement",
                "target_files_manifest",
                "sandbox_scope_confirmation",
                "single_file_scope_confirmation",
                "dry_run_mode_confirmation",
                "non_execution_confirmation",
            ],
            "preparation_evidence_does_not_execute": True,
            "status": "PREPARATION_EVIDENCE_REQUIREMENTS_READY",
        },
        "manual_preparation_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE68_PLANNING_ONLY",
                "REJECT",
            ],
            "manual_preparation_gate_does_not_execute": True,
            "status": "MANUAL_PREPARATION_GATE_READY",
        },
        "selected_decision": "ALLOW_PHASE68_PLANNING_ONLY",
    }


def test_generate_phase68_report_pass():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase67.json"
        output_path = tmpdir / "phase68.json"
        write_json(input_path, sample_phase67_report())

        result = generate_phase68_preparation_review_report(input_path, output_path)

        assert result["status"] == "PASS"
        assert result["report_generated"] is True
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["status"] == "PASS"
        assert report["mode"] == "DRY_RUN"
        assert report["human_approval_required"] is True
        assert report["can_execute"] is False
        assert report["execute_allowed"] is False
        assert report["phase69_readiness"]["readiness_status"] == "READY_FOR_PHASE69_READINESS_REVIEW_ONLY"


def test_generate_phase68_report_aborts_for_live_like_flag():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase67.json"
        output_path = tmpdir / "phase68.json"
        payload = sample_phase67_report()
        payload["preparation_evidence_package"]["execute_allowed"] = True
        write_json(input_path, payload)

        result = generate_phase68_preparation_review_report(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_generate_phase68_report_aborts_for_missing_required_evidence():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase67.json"
        output_path = tmpdir / "phase68.json"
        payload = sample_phase67_report()
        payload["preparation_evidence_requirements"]["required_evidence"] = [
            "phase66_go_no_go_report_reference"
        ]
        write_json(input_path, payload)

        result = generate_phase68_preparation_review_report(input_path, output_path)

        assert result["status"] == "ABORT"


def test_generate_phase68_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        input_path = tmpdir / "phase67.json"
        output_path = tmpdir / "phase68.json"
        write_json(input_path, sample_phase67_report())
        output_path.write_text("{}", encoding="utf-8")

        result = generate_phase68_preparation_review_report(input_path, output_path)

        assert result["status"] == "ABORT"