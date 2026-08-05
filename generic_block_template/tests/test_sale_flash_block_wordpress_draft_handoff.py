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


def test_sfb5_wordpress_draft_handoff_generation_and_report_integration():
    policy = json.loads((CONFIG / "wordpress_draft_handoff_policy.json").read_text(encoding="utf-8"))

    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["wordpress_write_allowed"] is False
    assert policy["creators_api_allowed"] is False
    assert policy["amazon_scraping_allowed"] is False

    normalize = _load_module("sfb5_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb5_queue", SCRIPTS / "generate_sale_review_queue.py")
    gate = _load_module("sfb5_gate", SCRIPTS / "apply_sale_review_quality_gate.py")
    readiness = _load_module("sfb5_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    payload = _load_module("sfb5_payload", SCRIPTS / "generate_sale_article_payloads.py")
    human = _load_module("sfb5_human", SCRIPTS / "generate_sale_human_review_handoff.py")
    wp = _load_module("sfb5_wp", SCRIPTS / "generate_wordpress_draft_handoff.py")
    report = _load_module("sfb5_report", SCRIPTS / "generate_sale_flash_block_report.py")

    assert normalize.normalize_candidates()["status"] == "PASS"
    assert queue.generate_review_queue()["status"] == "PASS"
    assert gate.apply_quality_gate()["status"] == "PASS"
    assert readiness.check_readiness()["status"] == "PASS"
    assert payload.generate_article_payloads()["status"] in {"PASS", "WARN"}
    assert human.generate_handoff()["status"] in {"PASS", "WARN"}

    wp_result = wp.generate_wordpress_draft_handoff()
    assert wp_result["status"] in {"PASS", "WARN"}
    assert wp_result["production_status"] == "NO_GO"
    assert wp_result["external_api_called"] is False
    assert wp_result["external_network_called"] is False
    assert wp_result["wordpress_write_executed"] is False
    assert wp_result["creators_api_called"] is False
    assert wp_result["amazon_scraping_called"] is False
    assert wp_result["publish_executed"] is False
    assert wp_result["update_executed"] is False
    assert wp_result["delete_executed"] is False
    assert wp_result["export_executed"] is False
    assert wp_result["human_approval_consumed"] is False

    assert (LOGS / "wordpress_draft_handoff.json").exists()
    assert (LOGS / "wordpress_draft_handoff.md").exists()

    for draft in wp_result["draft_candidates"]:
        wp_payload = draft["wordpress_draft_candidate"]
        assert wp_payload["post_status"] == "draft_candidate_only"
        assert wp_payload["post_title"]
        assert draft["human_review_status"] == "NOT_REVIEWED"

    report_result = report.generate_report()
    assert report_result["wordpress_draft_handoff_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert "wordpress_draft_handoff_count" in report_result

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## WordPress Draft Handoff" in report_md
