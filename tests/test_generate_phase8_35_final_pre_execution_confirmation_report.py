import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def test_report_json_md_generated():
    _run(["python3", str(ROOT / "scripts/validate_phase8_35_final_pre_execution_confirmation.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_final_pre_execution_confirmation_report.py")])

    assert (ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.json").exists()
    assert (ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.md").exists()


def test_markdown_required_lines():
    _run(["python3", str(ROOT / "scripts/validate_phase8_35_final_pre_execution_confirmation.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_final_pre_execution_confirmation_report.py")])

    md = (ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.md").read_text(encoding="utf-8")
    assert "Phase 8-35 summary" in md
    assert "WordPress API call not executed" in md
    assert "WordPress write not executed" in md
    assert "draft creation not executed" in md
    assert "production remains NO_GO" in md


def test_no_secret_value_output(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", secret)

    _run(["python3", str(ROOT / "scripts/validate_phase8_35_final_pre_execution_confirmation.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_final_pre_execution_confirmation_report.py")])

    report_json = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.json"
    report_md = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.md"

    assert secret not in report_json.read_text(encoding="utf-8")
    assert secret not in report_md.read_text(encoding="utf-8")


def test_report_fields_are_safe_flags():
    _run(["python3", str(ROOT / "scripts/validate_phase8_35_final_pre_execution_confirmation.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_35_final_pre_execution_confirmation_report.py")])

    payload = json.loads((ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.json").read_text(encoding="utf-8"))
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_not_executed"] is True
    assert payload["wordpress_write_not_executed"] is True
    assert payload["draft_creation_not_executed"] is True
    assert payload["actual_go_decision_issued"] is False
    assert payload["handoff_evidence_generated_for_execution"] is False
    assert payload["production_remains_no_go"] is True
