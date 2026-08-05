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


def test_sfb6_wordpress_draft_validation_and_report_integration():
    policy = json.loads((CONFIG / "wordpress_draft_validation_policy.json").read_text(encoding="utf-8"))

    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["wordpress_write_allowed"] is False
    assert policy["creators_api_allowed"] is False
    assert policy["amazon_scraping_allowed"] is False

    normalize = _load_module("sfb6_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb6_queue", SCRIPTS / "generate_sale_review_queue.py")
    gate = _load_module("sfb6_gate", SCRIPTS / "apply_sale_review_quality_gate.py")
    readiness = _load_module("sfb6_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    article = _load_module("sfb6_article", SCRIPTS / "generate_sale_article_payloads.py")
    human = _load_module("sfb6_human", SCRIPTS / "generate_sale_human_review_handoff.py")
    wp_handoff = _load_module("sfb6_wp_handoff", SCRIPTS / "generate_wordpress_draft_handoff.py")
    validate = _load_module("sfb6_validate", SCRIPTS / "validate_wordpress_draft_payloads.py")
    report = _load_module("sfb6_report", SCRIPTS / "generate_sale_flash_block_report.py")

    assert normalize.normalize_candidates()["status"] == "PASS"
    assert queue.generate_review_queue()["status"] == "PASS"
    assert gate.apply_quality_gate()["status"] == "PASS"
    assert readiness.check_readiness()["status"] == "PASS"
    assert article.generate_article_payloads()["status"] in {"PASS", "WARN"}
    assert human.generate_handoff()["status"] in {"PASS", "WARN"}
    assert wp_handoff.generate_wordpress_draft_handoff()["status"] in {"PASS", "WARN"}

    validation = validate.validate_wordpress_draft_payloads()
    assert validation["status"] in {"PASS", "WARN"}
    assert validation["production_status"] == "NO_GO"
    assert validation["external_api_called"] is False
    assert validation["external_network_called"] is False
    assert validation["wordpress_write_executed"] is False
    assert validation["publish_executed"] is False
    assert validation["update_executed"] is False
    assert validation["delete_executed"] is False
    assert validation["export_executed"] is False
    assert validation["human_approval_consumed"] is False

    assert (LOGS / "wordpress_draft_payload_validation.json").exists()
    assert (LOGS / "wordpress_draft_payload_validation.md").exists()

    checked_items = validation["valid_items"] + validation["needs_fix_items"]
    for item in checked_items:
        checks = item.get("validation_checks", {})
        assert "pr_disclosure_present" in checks
        assert "link_candidate_present" in checks
        assert "body_required_fields_present" in checks
        assert "no_price_claim" in checks
        assert "no_discount_claim" in checks
        assert "safety_flags_no_go" in checks

    report_result = report.generate_report()
    assert report_result["wordpress_draft_validation_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert "wordpress_draft_validation_count" in report_result

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## WordPress Draft Payload Validation" in report_md
