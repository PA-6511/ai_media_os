import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "governance_routing_thresholds.json"


def test_governance_routing_thresholds_json_is_valid_and_design_only():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert data["version"] == "0.1.0"
    assert data["mode"] == "DESIGN_ONLY"
    assert data["production_status"] == "NO_GO"
    assert data["core_impact"] == "NONE"

    thresholds = data["thresholds"]
    assert set(thresholds.keys()) == {
        "secret_abort_count",
        "disclosure_missing_rate",
        "api_terms_pending_rate",
    }

    assert thresholds["secret_abort_count"] == {
        "window": "7d",
        "operator": ">",
        "value": 0,
        "recommended_action": "REQUIRE_HUMAN_REVIEW",
    }
    assert thresholds["disclosure_missing_rate"] == {
        "window": "7d",
        "operator": ">=",
        "value": 0.5,
        "recommended_action": "REQUIRE_HUMAN_REVIEW",
    }
    assert thresholds["api_terms_pending_rate"] == {
        "window": "30d",
        "operator": ">=",
        "value": 0.5,
        "recommended_action": "REQUIRE_POLICY_REVIEW",
    }

    safety = data["safety_constraints"]
    assert safety["core_routing_integration"] == "DISABLED"
    assert safety["auto_stop"] is False
    assert safety["auto_block"] is False
    assert safety["auto_freeze"] is False
    assert safety["auto_go_nogo_change"] is False
