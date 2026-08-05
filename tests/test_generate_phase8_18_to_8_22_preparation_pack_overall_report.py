import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_generate_pack_overall_report():
    subprocess.run([
        "python3",
        str(ROOT / "scripts/validate_phase8_18_single_controlled_wordpress_draft_creation_execution_design_only.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/validate_phase8_19_post_draft_creation_verification_design_only.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/validate_phase8_20_first_draft_creation_completion_report_design_only.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/validate_phase8_21_post_credentials_ready_rehandoff_design_only.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/validate_phase8_22_immediate_pre_execution_freeze_abort_gate_design_only.py"),
    ], check=True)

    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_report.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_19_post_draft_creation_verification_design_only_report.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_20_first_draft_creation_completion_report_design_only_report.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_21_post_credentials_ready_rehandoff_design_only_report.py"),
    ], check=True)
    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_22_immediate_pre_execution_freeze_abort_gate_design_only_report.py"),
    ], check=True)

    subprocess.run([
        "python3",
        str(ROOT / "scripts/generate_phase8_18_to_8_22_preparation_pack_overall_report.py"),
    ], check=True)

    report_json = ROOT / "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json"
    report_md = ROOT / "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.md"

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["final_status"] == "PHASE8_18_TO_8_22_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
    assert payload["execution_allowed"] is False
    assert payload["wordpress_api_call_allowed"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["wordpress_draft_created"] is False

    md = report_md.read_text(encoding="utf-8")
    assert "final_status" in md
    assert "NO_GO" in md
