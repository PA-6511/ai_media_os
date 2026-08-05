import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_manual_affiliate_items import load_json, validate


def _example_data():
    return load_json(ROOT / "manual_affiliate_builder" / "manual_items.example.json")


def _policy():
    return load_json(ROOT / "manual_affiliate_builder" / "schema_policy.json")


def test_validate_pass_on_example():
    ok, errors = validate(_example_data(), _policy())
    assert ok is True
    assert errors == []


def test_validate_fail_on_duplicate_asin():
    data = _example_data()
    item = copy.deepcopy(data["items"][0])
    data["items"].append(item)
    ok, errors = validate(data, _policy())
    assert ok is False
    assert any("is duplicated" in e for e in errors)


def test_validate_fail_on_non_amazon_url():
    data = _example_data()
    data["items"][0]["manual_affiliate_url"] = "https://example.com/item"
    ok, errors = validate(data, _policy())
    assert ok is False
    assert any("must be an amazon.co.jp URL" in e for e in errors)


def test_validate_fail_when_write_flag_true():
    data = _example_data()
    data["wordpress_write_allowed"] = True
    ok, errors = validate(data, _policy())
    assert ok is False
    assert "top_level.wordpress_write_allowed must be false" in errors
