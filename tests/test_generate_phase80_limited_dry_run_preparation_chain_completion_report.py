import json
import tempfile
from pathlib import Path

from scripts.generate_phase80_limited_dry_run_preparation_chain_completion_report import (
    CHAIN_SPECS,
    generate_phase80_limited_dry_run_preparation_chain_completion_report,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_phase_payload(spec: dict) -> dict:
    payload = {
        "package_type": spec["package_type"],
        "phase": spec["phase"],
        "status": "PASS",
        spec["status_field"]: "PASS",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        spec["controls_key"]: {
            "does_not_execute": True,
        },
        spec["evidence_key"]: {
            "does_not_execute": True,
            "required_evidence": [
                "phase66_go_no_go_report_reference",
                "preparation_scope_statement",
                "target_files_manifest",
                "sandbox_scope_confirmation",
                "single_file_scope_confirmation",
                "dry_run_mode_confirmation",
                "non_execution_confirmation",
            ],
        },
        spec["gate_key"]: {
            "does_not_execute": True,
            "allowed_decisions": [
                spec["expected_decision"],
                "REJECT",
            ],
        },
        spec["readiness_key"]: {
            "readiness_status": spec["readiness_status"],
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
    }
    return payload


def write_chain(logs_dir: Path) -> None:
    for spec in CHAIN_SPECS:
        write_json(logs_dir / spec["file"], sample_phase_payload(spec))


def test_generate_phase80_report_pass():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        logs_dir = tmpdir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        write_chain(logs_dir)

        input_path = logs_dir / "phase79_limited_dry_run_final_go_no_go_planning_report.json"
        output_path = logs_dir / "phase80_limited_dry_run_preparation_chain_completion_report.json"

        result = generate_phase80_limited_dry_run_preparation_chain_completion_report(input_path, output_path)

        assert result["status"] == "PASS"
        assert result["report_generated"] is True
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["status"] == "PASS"
        assert report["mode"] == "DRY_RUN"
        assert report["pass_status_summary"]["pass_count"] == 12
        assert report["phase80_readiness"]["readiness_status"] == "READY_FOR_PHASE80_PLANNING_ONLY"


def test_generate_phase80_report_aborts_for_live_like_flag():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        logs_dir = tmpdir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        write_chain(logs_dir)

        phase74 = logs_dir / "phase74_limited_dry_run_sandbox_plan_report.json"
        payload = json.loads(phase74.read_text(encoding="utf-8"))
        payload["execute_allowed"] = True
        write_json(phase74, payload)

        input_path = logs_dir / "phase79_limited_dry_run_final_go_no_go_planning_report.json"
        output_path = logs_dir / "phase80_limited_dry_run_preparation_chain_completion_report.json"
        result = generate_phase80_limited_dry_run_preparation_chain_completion_report(input_path, output_path)

        assert result["status"] == "ABORT"
        assert output_path.exists() is False


def test_generate_phase80_report_aborts_for_missing_chain_file():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        logs_dir = tmpdir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        write_chain(logs_dir)

        (logs_dir / "phase72_preparation_final_signoff_report.json").unlink()

        input_path = logs_dir / "phase79_limited_dry_run_final_go_no_go_planning_report.json"
        output_path = logs_dir / "phase80_limited_dry_run_preparation_chain_completion_report.json"
        result = generate_phase80_limited_dry_run_preparation_chain_completion_report(input_path, output_path)

        assert result["status"] == "ABORT"


def test_generate_phase80_report_aborts_without_overwrite():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        logs_dir = tmpdir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        write_chain(logs_dir)

        input_path = logs_dir / "phase79_limited_dry_run_final_go_no_go_planning_report.json"
        output_path = logs_dir / "phase80_limited_dry_run_preparation_chain_completion_report.json"
        output_path.write_text("{}", encoding="utf-8")

        result = generate_phase80_limited_dry_run_preparation_chain_completion_report(input_path, output_path)

        assert result["status"] == "ABORT"
