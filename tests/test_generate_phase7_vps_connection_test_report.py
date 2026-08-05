import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_phase7_vps_connection_test_report import generate_report


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_generate_report_pass():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        sources = {
            "policy_validation_result": td_path / "policy.json",
            "connectivity_check": td_path / "connectivity.json",
            "stability_evaluation": td_path / "stability.json",
            "failure_classification": td_path / "classification.json",
        }
        _write(sources["policy_validation_result"], {"status": "PASS"})
        _write(
            sources["connectivity_check"],
            {
                "check_id": "vps-check-001",
                "secrets_exposed": False,
                "remote_write_executed": False,
                "remote_command_executed": False,
            },
        )
        _write(sources["stability_evaluation"], {"overall_status": "PASS_DRY_RUN_ONLY"})
        _write(sources["failure_classification"], {"classification": ["UNKNOWN"]})

        json_out = td_path / "report.json"
        md_out = td_path / "report.md"
        result = generate_report(sources, json_out, md_out)

        assert result["status"] == "PASS"
        assert result["overall_status"] == "PASS_DRY_RUN_ONLY"
        assert json_out.exists()
        assert md_out.exists()


def test_generate_report_abort_on_secrets_exposed():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        sources = {
            "policy_validation_result": td_path / "policy.json",
            "connectivity_check": td_path / "connectivity.json",
            "stability_evaluation": td_path / "stability.json",
            "failure_classification": td_path / "classification.json",
        }
        _write(sources["policy_validation_result"], {"status": "PASS"})
        _write(
            sources["connectivity_check"],
            {
                "check_id": "vps-check-002",
                "secrets_exposed": True,
                "remote_write_executed": False,
                "remote_command_executed": False,
            },
        )
        _write(sources["stability_evaluation"], {"overall_status": "PASS_DRY_RUN_ONLY"})
        _write(sources["failure_classification"], {"classification": ["UNKNOWN"]})

        json_out = td_path / "report.json"
        md_out = td_path / "report.md"
        result = generate_report(sources, json_out, md_out)
        assert result["status"] == "ABORT"


def test_missing_source_aborts():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        sources = {
            "policy_validation_result": td_path / "policy.json",
            "connectivity_check": td_path / "connectivity.json",
            "stability_evaluation": td_path / "stability.json",
            "failure_classification": td_path / "classification.json",
        }
        _write(sources["policy_validation_result"], {"status": "PASS"})
        result = generate_report(sources, td_path / "report.json", td_path / "report.md")
        assert result["status"] == "ABORT"