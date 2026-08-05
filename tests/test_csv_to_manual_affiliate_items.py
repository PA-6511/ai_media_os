import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.csv_to_manual_affiliate_items import convert_csv_to_data
from scripts.validate_manual_affiliate_items import load_json as load_policy_json
from scripts.validate_manual_affiliate_items import validate


def test_csv_convert_success(tmp_path):
    src = ROOT / "manual_affiliate_builder" / "manual_items.csv.example"
    data = convert_csv_to_data(src)

    assert data["phase"] == "Phase 8-50-MANUAL"
    assert data["execution_mode"] == "DRY_RUN_ONLY"
    assert data["production_status"] == "NO_GO"
    assert data["amazon_api_call_allowed"] is False
    assert data["wordpress_write_allowed"] is False
    assert len(data["items"]) >= 1


def test_csv_output_passes_existing_validator(tmp_path):
    src = ROOT / "manual_affiliate_builder" / "manual_items.csv.example"
    data = convert_csv_to_data(src)
    policy = load_policy_json(ROOT / "manual_affiliate_builder" / "schema_policy.json")

    ok, errors = validate(data, policy)
    assert ok is True
    assert errors == []
