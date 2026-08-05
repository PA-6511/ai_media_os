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


def test_sfb4_human_review_handoff_generation_and_report_integration():
    policy = json.loads((CONFIG / "human_review_handoff_policy.json").read_text(encoding="utf-8"))

    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["wordpress_write_allowed"] is False
    assert policy["creators_api_allowed"] is False
    assert policy["amazon_scraping_allowed"] is False

    normalize = _load_module("sfb4_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb4_queue", SCRIPTS / "generate_sale_review_queue.py")
    gate = _load_module("sfb4_gate", SCRIPTS / "apply_sale_review_quality_gate.py")
    readiness = _load_module("sfb4_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    payloads = _load_module("sfb4_payloads", SCRIPTS / "generate_sale_article_payloads.py")
    handoff = _load_module("sfb4_handoff", SCRIPTS / "generate_sale_human_review_handoff.py")
    report = _load_module("sfb4_report", SCRIPTS / "generate_sale_flash_block_report.py")

    assert normalize.normalize_candidates()["status"] == "PASS"
    assert queue.generate_review_queue()["status"] == "PASS"
    assert gate.apply_quality_gate()["status"] == "PASS"
    assert readiness.check_readiness()["status"] == "PASS"
    assert payloads.generate_article_payloads()["status"] in {"PASS", "WARN"}

    handoff_result = handoff.generate_handoff()
    assert handoff_result["status"] in {"PASS", "WARN"}

    assert (LOGS / "sale_human_review_handoff.json").exists()
    assert (LOGS / "sale_human_review_handoff.md").exists()

    assert "adopt_candidates" in handoff_result
    assert "needs_fix_candidates" in handoff_result
    assert "excluded_candidates" in handoff_result

    all_items = (
        handoff_result["adopt_candidates"]
        + handoff_result["needs_fix_candidates"]
        + handoff_result["excluded_candidates"]
    )

    for item in all_items:
        assert item["human_review_status"] == "NOT_REVIEWED"
        assert "pr_disclosure_present" in item["review_checks"]
        assert "link_candidate_present" in item["review_checks"]
        assert "sns_post_candidate_present" in item["review_checks"]
        assert "no_price_claim" in item["review_checks"]
        assert "no_discount_claim" in item["review_checks"]

    assert handoff_result["human_approval_consumed"] is False
    assert handoff_result["final_publish_decision_allowed"] is False
    assert handoff_result["production_status"] == "NO_GO"
    assert handoff_result["external_api_called"] is False
    assert handoff_result["external_network_called"] is False
    assert handoff_result["wordpress_write_executed"] is False
    assert handoff_result["creators_api_called"] is False
    assert handoff_result["amazon_scraping_called"] is False
    assert handoff_result["publish_executed"] is False
    assert handoff_result["update_executed"] is False
    assert handoff_result["delete_executed"] is False
    assert handoff_result["export_executed"] is False

    report_result = report.generate_report()
    assert report_result["human_review_handoff_status"] in {"PASS", "WARN", "NOT_GENERATED"}

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## Human Review Handoff" in report_md
