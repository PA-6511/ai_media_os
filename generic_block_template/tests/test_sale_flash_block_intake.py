from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCK_ROOT = ROOT / "blocks/sale_flash_block"
SCRIPTS = BLOCK_ROOT / "scripts"
CONFIG = BLOCK_ROOT / "config"
LOGS = BLOCK_ROOT / "logs"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sfb1_policies_and_pipeline_generation():
    intake_policy = json.loads((CONFIG / "intake_policy.json").read_text(encoding="utf-8"))
    source_registry = json.loads((CONFIG / "source_registry.json").read_text(encoding="utf-8"))
    migration_policy = json.loads((CONFIG / "migration_policy.json").read_text(encoding="utf-8"))

    assert intake_policy["production_status"] == "NO_GO"
    assert intake_policy["mode"] == "DRY_RUN"
    assert intake_policy["external_api_allowed"] is False
    assert intake_policy["external_network_allowed"] is False
    assert intake_policy["wordpress_write_allowed"] is False
    assert intake_policy["creators_api_allowed"] is False
    assert intake_policy["amazon_scraping_allowed"] is False

    creators_placeholder = source_registry["adapters"]["creators_api_placeholder"]
    assert creators_placeholder["enabled"] is False

    assert migration_policy["creators_api_migration_allowed"] is False

    normalize = _load_module("sfb_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb_queue", SCRIPTS / "generate_sale_review_queue.py")
    readiness = _load_module("sfb_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    report = _load_module("sfb_report", SCRIPTS / "generate_sale_flash_block_report.py")

    normalized = normalize.normalize_candidates()
    assert normalized["status"] == "PASS"
    assert normalized["production_status"] == "NO_GO"
    assert normalized["external_api_called"] is False
    assert normalized["external_network_called"] is False
    assert normalized["wordpress_write_executed"] is False
    assert normalized["item_count"] >= 5

    candidates = normalized["candidates"]
    assert any(c["asin"] and c["link_strategy"] == "amazon_product_link_candidate" for c in candidates)
    assert any((not c["asin"]) and c["link_strategy"] == "amazon_search_link_candidate" for c in candidates)
    assert any(c["review_required"] is True for c in candidates)

    review_queue = queue.generate_review_queue()
    assert review_queue["status"] == "PASS"
    assert review_queue["production_status"] == "NO_GO"
    assert review_queue["external_api_called"] is False
    assert review_queue["external_network_called"] is False
    assert review_queue["wordpress_write_executed"] is False
    assert review_queue["item_count"] == normalized["item_count"]

    readiness_result = readiness.check_readiness()
    assert readiness_result["status"] == "PASS"
    assert readiness_result["production_status"] == "NO_GO"

    report_result = report.generate_report()
    assert report_result["status"] == "PASS"
    assert report_result["production_status"] == "NO_GO"
    assert report_result["external_api_called"] is False
    assert report_result["external_network_called"] is False
    assert report_result["wordpress_write_executed"] is False

    assert (LOGS / "normalized_sale_candidates.json").exists()
    assert (LOGS / "sale_review_queue.json").exists()
    assert (LOGS / "sale_intake_readiness.json").exists()
    assert (LOGS / "sale_flash_block_report.json").exists()
    assert (LOGS / "sale_flash_block_report.md").exists()
