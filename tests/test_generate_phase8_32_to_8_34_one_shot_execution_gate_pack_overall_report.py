import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _validate_all() -> None:
    _run(["python3", str(ROOT / "scripts/validate_phase8_32_final_execution_gate_decision_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_33_one_shot_lock_enforcement_abort_condition_design_only.py")])
    _run(["python3", str(ROOT / "scripts/validate_phase8_34_post_run_evidence_contract_rollback_trigger_design_only.py")])


def test_overall_pack_pass_when_all_design_pass():
    _validate_all()
    _run(["python3", str(ROOT / "scripts/generate_phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.py")])

    report_json = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert payload["pack_status"] == "PHASE8_32_TO_8_34_ONE_SHOT_EXECUTION_GATE_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    assert payload["all_design_only"] is True
    assert payload["all_no_execution"] is True
    assert payload["all_no_secret_leak"] is True
    assert payload["all_no_lock_operation"] is True
    assert payload["all_no_rollback_execution"] is True


def test_overall_pack_not_pass_when_abort_exists():
    _validate_all()
    source = ROOT / "exchange/logs/phase8_32_final_execution_gate_decision_design_only_result.json"
    original = source.read_text(encoding="utf-8")
    try:
        payload = json.loads(original)
        payload["final_status"] = "ABORT_POLICY_VIOLATION"
        source.write_text(json.dumps(payload), encoding="utf-8")

        proc = subprocess.run(
            ["python3", str(ROOT / "scripts/generate_phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.py")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0

        report_json = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"
        report = json.loads(report_json.read_text(encoding="utf-8"))
        assert report["pack_status"] != "PHASE8_32_TO_8_34_ONE_SHOT_EXECUTION_GATE_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    finally:
        source.write_text(original, encoding="utf-8")


def test_previous_credentials_not_ready_not_failure():
    _validate_all()
    _run(["python3", str(ROOT / "scripts/generate_phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.py")])

    report_json = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert payload["previous_credentials_not_ready"] is True
    assert payload["credentials_blocked_reason_recorded"] is True
    assert payload["pack_status"] == "PHASE8_32_TO_8_34_ONE_SHOT_EXECUTION_GATE_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"


def test_reports_do_not_include_secret_values(monkeypatch):
    secret = "TOP_SECRET_SAMPLE_123"
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", secret)

    _validate_all()
    _run(["python3", str(ROOT / "scripts/generate_phase8_32_final_execution_gate_decision_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_33_one_shot_lock_enforcement_abort_condition_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_34_post_run_evidence_contract_rollback_trigger_design_only_report.py")])
    _run(["python3", str(ROOT / "scripts/generate_phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.py")])

    report_json = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"
    report_md = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.md"

    assert secret not in report_json.read_text(encoding="utf-8")
    assert secret not in report_md.read_text(encoding="utf-8")


def test_markdown_contains_required_lines():
    _validate_all()
    _run(["python3", str(ROOT / "scripts/generate_phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.py")])

    md = (ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.md").read_text(encoding="utf-8")
    assert "Phase 8-32〜8-34" in md
    assert "DESIGN_ONLY" in md
    assert "WordPress API call not executed" in md
    assert "WordPress write not executed" in md
    assert "draft creation not executed" in md
    assert "lock_created=false" in md
    assert "rollback_executed=false" in md
    assert "production remains NO_GO" in md
