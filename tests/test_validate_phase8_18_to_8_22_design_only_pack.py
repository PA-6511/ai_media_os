import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VALIDATORS = [
    "scripts/validate_phase8_18_single_controlled_wordpress_draft_creation_execution_design_only.py",
    "scripts/validate_phase8_19_post_draft_creation_verification_design_only.py",
    "scripts/validate_phase8_20_first_draft_creation_completion_report_design_only.py",
    "scripts/validate_phase8_21_post_credentials_ready_rehandoff_design_only.py",
    "scripts/validate_phase8_22_immediate_pre_execution_freeze_abort_gate_design_only.py",
]

RESULTS = [
    "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_result.json",
    "exchange/logs/phase8_19_post_draft_creation_verification_design_only_result.json",
    "exchange/logs/phase8_20_first_draft_creation_completion_report_design_only_result.json",
    "exchange/logs/phase8_21_post_credentials_ready_rehandoff_design_only_result.json",
    "exchange/logs/phase8_22_immediate_pre_execution_freeze_abort_gate_design_only_result.json",
]

EXPECTED = {
    "8-18": "DESIGN_ONLY_EXECUTION_SPEC_READY_NO_EXECUTION",
    "8-19": "DESIGN_ONLY_POST_VERIFICATION_SPEC_READY_NO_EXECUTION",
    "8-20": "DESIGN_ONLY_COMPLETION_REPORT_SPEC_READY_NO_EXECUTION",
    "8-21": "DESIGN_ONLY_REHANDOFF_SPEC_READY_NO_EXECUTION",
    "8-22": "DESIGN_ONLY_FREEZE_ABORT_GATE_READY_NO_EXECUTION",
}


def test_design_only_validators_chain_pass():
    for rel in VALIDATORS:
        subprocess.run(["python3", str(ROOT / rel)], check=True)

    for rel in RESULTS:
        payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        phase = payload["phase"]
        assert payload["final_status"] == EXPECTED[phase]
        assert payload["execution_allowed"] is False
        assert payload["wordpress_api_call_attempted"] is False
        assert payload["wordpress_write_executed"] is False
        assert payload["wordpress_draft_created"] is False
        assert payload["production_status"] == "NO_GO"


def test_safe_secret_management_keys_do_not_trigger_false_positive():
    payload = json.loads(
        (ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_result.json").read_text(encoding="utf-8")
    )
    assert "secret_values_output" in payload
    assert payload["secret_values_output"] is False
    assert payload["secret_values_written"] is False
    assert payload["secret_values_logged"] is False
