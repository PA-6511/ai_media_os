import copy
import json
from pathlib import Path

from legal_compliance_gate_ai.core.legal_compliance_scanner import scan_legal_compliance


BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BASE_DIR / "config" / "legal_risk_registry.json"
EXAMPLE_INPUT_PATH = BASE_DIR / "examples" / "legal_scan_input.example.json"


def _load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _load_example_input():
    return json.loads(EXAMPLE_INPUT_PATH.read_text(encoding="utf-8"))


def test_affiliate_without_disclosure_requires_legal_review():
    payload = _load_example_input()
    payload["signals"] = ["affiliate_link"]
    payload["disclosure_checked"] = False

    result = scan_legal_compliance(payload, _load_registry())

    assert result["status"] == "LEGAL_REVIEW_REQUIRED"


def test_secret_like_text_causes_abort():
    payload = _load_example_input()
    payload["contains_secret_like_text"] = True

    result = scan_legal_compliance(payload, _load_registry())

    assert result["status"] == "ABORT"


def test_amazon_service_detects_api_terms_risk():
    payload = _load_example_input()
    payload["signals"] = []
    payload["external_services"] = ["amazon_pa_api"]

    result = scan_legal_compliance(payload, _load_registry())

    risk_ids = {risk["risk_id"] for risk in result["detected_risks"]}
    assert "API_TERMS_CHECK_REQUIRED" in risk_ids


def test_clean_input_returns_pass():
    payload = _load_example_input()
    payload.update(
        {
            "signals": ["wordpress_draft"],
            "external_services": ["wordpress"],
            "disclosure_checked": True,
            "contains_secret_like_text": False,
            "contains_personal_data": False,
            "policy_sources": ["https://example.com/policy"],
        }
    )

    result = scan_legal_compliance(payload, _load_registry())

    assert result["status"] == "PASS"


def test_result_contains_required_keys_and_core_flag_always_true():
    payload = _load_example_input()
    result = scan_legal_compliance(payload, _load_registry())

    required_keys = {
        "status",
        "block_id",
        "detected_risks",
        "required_actions",
        "human_review_required",
        "core_final_decision_required",
        "execution",
    }
    assert required_keys.issubset(result.keys())
    assert result["core_final_decision_required"] is True


def test_auto_operations_are_not_executed_by_design():
    payload = copy.deepcopy(_load_example_input())
    payload.update(
        {
            "auto_post": True,
            "auto_update": True,
            "auto_delete": True,
            "auto_export": True,
        }
    )

    result = scan_legal_compliance(payload, _load_registry())

    assert result["auto_operations_executed"] is False
    assert result["auto_operation_flags"] == {
        "auto_post": True,
        "auto_update": True,
        "auto_delete": True,
        "auto_export": True,
    }
