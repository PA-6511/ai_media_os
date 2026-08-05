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


def test_sfb3_article_payload_generation_and_report_integration():
    policy = json.loads((CONFIG / "article_payload_policy.json").read_text(encoding="utf-8"))

    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["wordpress_write_allowed"] is False
    assert policy["creators_api_allowed"] is False
    assert policy["amazon_scraping_allowed"] is False

    normalize = _load_module("sfb3_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb3_queue", SCRIPTS / "generate_sale_review_queue.py")
    gate = _load_module("sfb3_gate", SCRIPTS / "apply_sale_review_quality_gate.py")
    readiness = _load_module("sfb3_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    payload_gen = _load_module("sfb3_payload", SCRIPTS / "generate_sale_article_payloads.py")
    report = _load_module("sfb3_report", SCRIPTS / "generate_sale_flash_block_report.py")

    assert normalize.normalize_candidates()["status"] == "PASS"
    assert queue.generate_review_queue()["status"] == "PASS"
    assert gate.apply_quality_gate()["status"] == "PASS"
    assert readiness.check_readiness()["status"] == "PASS"

    payload_result = payload_gen.generate_article_payloads()
    assert payload_result["status"] in {"PASS", "WARN"}
    assert payload_result["production_status"] == "NO_GO"
    assert payload_result["external_api_called"] is False
    assert payload_result["external_network_called"] is False
    assert payload_result["wordpress_write_executed"] is False
    assert payload_result["creators_api_called"] is False
    assert payload_result["amazon_scraping_called"] is False

    assert (LOGS / "sale_article_payloads.json").exists()
    assert (LOGS / "sale_article_payloads.md").exists()

    for item in payload_result["payloads"]:
        assert item["article_title"]
        assert item["short_intro"]
        assert item["recommended_reader"]
        assert item["pr_disclosure"]
        assert item["sns_post_candidate"]
        assert item["human_review_required"] is True
        assert item["production_status"] == "NO_GO"
        assert item["external_api_called"] is False
        assert item["external_network_called"] is False
        assert item["wordpress_write_executed"] is False
        assert item["creators_api_called"] is False
        assert item["amazon_scraping_called"] is False
        assert "price" not in item
        assert "discount_rate" not in item

    excluded = {"needs_metadata_fix", "duplicate_review", "blocked_or_invalid"}
    payload_buckets = {item["review_bucket"] for item in payload_result["payloads"]}
    assert not payload_buckets.intersection(excluded)

    report_result = report.generate_report()
    assert report_result["phase"] in {"SFB-3", "SFB-4", "SFB-5", "SFB-6", "SFB-7", "SFB-8", "SFB-8B", "SFB-9", "SFB-10", "SFB-10B"}
    assert report_result["article_payload_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert "article_payload_count" in report_result
    assert "human_review_handoff_status" in report_result

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## Article Payloads" in report_md
