import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.legal_compliance_gate_adapter import (
    build_legal_gate_decision_package,
    observe_legal_gate_in_core_input,
    run_legal_compliance_gate_for_core,
)


EXAMPLE_INPUT_PATH = BASE_DIR / "legal_compliance_gate_ai" / "examples" / "legal_scan_input.example.json"


def _load_example_payload() -> dict:
    return json.loads(EXAMPLE_INPUT_PATH.read_text(encoding="utf-8"))


def test_adapter_returns_decision_package_like_payload():
    payload = _load_example_payload()

    result = run_legal_compliance_gate_for_core(payload)

    assert result["package_type"] == "decision_package"
    assert result["source"] == "legal_compliance_gate_ai"
    assert result["execution"] == "DRY_RUN"
    assert result["auto_post"] is False
    assert result["auto_update"] is False
    assert result["auto_delete"] is False
    assert result["auto_export"] is False


def test_core_final_decision_required_is_always_true():
    payload = _load_example_payload()

    result = run_legal_compliance_gate_for_core(payload)

    assert result["decision"]["core_final_decision_required"] is True
    assert result["legal_gate"]["core_final_decision_required"] is True


def test_legal_review_required_is_marked_for_human_review_route():
    payload = _load_example_payload()
    payload["disclosure_checked"] = False
    payload["signals"] = ["affiliate_link", "monetized_article"]

    result = run_legal_compliance_gate_for_core(payload)

    assert result["legal_gate"]["status"] == "LEGAL_REVIEW_REQUIRED"
    assert result["integration_notes"]["human_review_route_ready"] is True
    assert result["decision"]["requires_human_review"] is True


def test_decision_package_status_is_compatible_with_existing_pipeline():
    scan_result = {
        "status": "LEGAL_REVIEW_REQUIRED",
        "execution": "DRY_RUN",
        "detected_risks": [],
        "required_actions": [],
        "human_review_required": True,
        "core_final_decision_required": True,
    }

    result = build_legal_gate_decision_package(scan_result)

    assert result["decision"]["status"] in {"PASS", "WARN", "FAIL", "ABORT"}
    assert result["decision"]["status"] == "WARN"


def test_observe_mode_appends_decision_package_and_writes_report(tmp_path):
    core_input = {
        "event_id": "evt_l35_001",
        "proposals": [
            {
                "block_name": "ebook_affiliate_ai",
                "item_id": "item-1",
                "task_id": "task-1",
                "priority": 0.9,
                "reason": "affiliate article candidate",
                "metadata": {
                    "signals": ["affiliate_link", "monetized_article"],
                    "external_services": ["amazon_pa_api"],
                    "disclosure_checked": False,
                    "contains_secret_like_text": False,
                    "contains_personal_data": False,
                    "policy_sources": [],
                },
            }
        ],
    }

    observation = observe_legal_gate_in_core_input(
        core_input,
        event_id="evt_l35_001",
        output_dir=tmp_path,
    )

    assert "decision_packages" in core_input
    assert isinstance(core_input["decision_packages"], list)
    assert len(core_input["decision_packages"]) == 1
    appended = core_input["decision_packages"][0]
    assert appended["package_type"] == "decision_package"
    assert appended["legal_gate"]["status"] == "LEGAL_REVIEW_REQUIRED"

    report_path = Path(observation["report_path"])
    assert report_path.exists() is True


def test_observe_mode_is_log_only_and_does_not_change_execution_flags(tmp_path):
    core_input = {
        "event_id": "evt_l35_002",
        "proposals": [],
    }

    observation = observe_legal_gate_in_core_input(
        core_input,
        event_id="evt_l35_002",
        output_dir=tmp_path,
    )

    assert observation["mode"] == "LOG_ONLY"
    assert observation["execution"] == "DRY_RUN"
    assert observation["core_flow_impact"] == "NONE"
    decision_package = observation["decision_package"]
    assert decision_package["auto_post"] is False
    assert decision_package["auto_update"] is False
    assert decision_package["auto_delete"] is False
    assert decision_package["auto_export"] is False
