import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_manual_wp_draft_payload_preview import build_payload, load_json


def _example_data():
    return load_json(ROOT / "manual_affiliate_builder" / "manual_items.example.json")


def test_build_payload_is_dry_run_only():
    payload = build_payload(_example_data())
    assert payload["status"] == "PREVIEW_GENERATED_DRY_RUN_ONLY"
    assert payload["execution_mode"] == "DRY_RUN_ONLY"
    assert payload["production_status"] == "NO_GO"
    assert payload["amazon_api_call_allowed"] is False
    assert payload["wordpress_write_allowed"] is False


def test_build_payload_post_flags_are_safe():
    payload = build_payload(_example_data())
    assert payload["post_count"] == 1
    post = payload["posts"][0]
    assert post["post_status"] == "draft_preview_only"
    assert post["amazon_api_call_allowed"] is False
    assert post["wordpress_write_allowed"] is False
    assert post["meta"]["phase"] == "Phase 8-50-MANUAL"


def test_build_payload_preserves_asin_canonical_link():
    payload = build_payload(_example_data())
    post = payload["posts"][0]
    assert post["asin"] == "B0DUMMY001"
    assert post["canonical_item_id"] == "amazon_jp:B0DUMMY001"


def test_content_contains_affiliate_url():
    payload = build_payload(_example_data())
    post = payload["posts"][0]
    assert "amazon.co.jp" in post["content"]
    assert "tag=" in post["content"]
