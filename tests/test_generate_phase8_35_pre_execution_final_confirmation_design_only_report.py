import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def test_generate_report_from_validator_result():
    _run(["python3", str(ROOT / "scripts/validate_phase8_35_pre_execution_final_confirmation_design_only.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_pre_execution_final_confirmation_design_only_report.py")])

    report_json = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.json"
    report_md = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.md"

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    md = report_md.read_text(encoding="utf-8")

    assert payload["production_status"] == "NO_GO"
    assert payload["execution"] == "DRY_RUN"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_not_executed"] is True
    assert payload["wordpress_write_not_executed"] is True
    assert payload["draft_creation_not_executed"] is True
    assert "WordPress API call not executed" in md
    assert "WordPress write not executed" in md
    assert "draft creation not executed" in md


def test_report_has_no_secret_values(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", secret)

    _run(["python3", str(ROOT / "scripts/validate_phase8_35_pre_execution_final_confirmation_design_only.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_pre_execution_final_confirmation_design_only_report.py")])

    report_json = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.json"
    report_md = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.md"

    assert secret not in report_json.read_text(encoding="utf-8")
    assert secret not in report_md.read_text(encoding="utf-8")
