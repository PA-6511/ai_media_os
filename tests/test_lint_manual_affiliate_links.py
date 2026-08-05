import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.csv_to_manual_affiliate_items import convert_csv_to_data
from scripts.lint_manual_affiliate_links import lint_items, load_json


def _base_data():
    return convert_csv_to_data(ROOT / "manual_affiliate_builder" / "manual_items.csv.example")


def _policy():
    return load_json(ROOT / "manual_affiliate_builder" / "migration_policy.json")


def test_lint_pass_on_csv_converted_data():
    ok, errors = lint_items(_base_data(), _policy())
    assert ok is True
    assert errors == []


def test_lint_fail_invalid_asin():
    data = _base_data()
    data["items"][0]["asin"] = "BAD"
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("asin must be 10" in e for e in errors)


def test_lint_fail_non_amazon_url():
    data = _base_data()
    data["items"][0]["manual_affiliate_url"] = "https://example.com/dp/B0DUMMY001?tag=x-22"
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("amazon.co.jp" in e for e in errors)


def test_lint_fail_missing_tag():
    data = _base_data()
    data["items"][0]["manual_affiliate_url"] = "https://www.amazon.co.jp/dp/B0DUMMY001"
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("tag parameter" in e for e in errors)


def test_lint_fail_asin_mismatch_between_url_and_item():
    data = _base_data()
    data["items"][0]["manual_affiliate_url"] = "https://www.amazon.co.jp/dp/B0DUMMY009?tag=exampletag-22"
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("asin mismatch" in e.lower() for e in errors)


def test_lint_fail_duplicate_asin():
    data = _base_data()
    dup = copy.deepcopy(data["items"][0])
    dup["manual_affiliate_url"] = "https://www.amazon.co.jp/dp/B0DUMMY001?tag=othertag-22"
    data["items"].append(dup)
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("asin duplicated" in e for e in errors)


def test_lint_fail_duplicate_url():
    data = _base_data()
    dup = copy.deepcopy(data["items"][0])
    dup["asin"] = "B0DUMMY003"
    dup["canonical_item_id"] = "amazon_jp:B0DUMMY003"
    data["items"].append(dup)
    ok, errors = lint_items(data, _policy())
    assert ok is False
    assert any("url duplicated" in e.lower() for e in errors)
