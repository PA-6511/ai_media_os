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


def test_sfb2_quality_gate_generation_and_report_extension():
    policy = json.loads((CONFIG / "quality_gate_policy.json").read_text(encoding="utf-8"))
    assert policy["production_status"] == "NO_GO"
    assert policy["phase"] == "SFB-2"

    normalize = _load_module("sfb2_normalize", SCRIPTS / "normalize_sale_candidates.py")
    queue = _load_module("sfb2_queue", SCRIPTS / "generate_sale_review_queue.py")
    gate = _load_module("sfb2_gate", SCRIPTS / "apply_sale_review_quality_gate.py")
    readiness = _load_module("sfb2_readiness", SCRIPTS / "check_sale_intake_readiness.py")
    report = _load_module("sfb2_report", SCRIPTS / "generate_sale_flash_block_report.py")

    normalize_result = normalize.normalize_candidates()
    assert normalize_result["status"] == "PASS"

    queue_result = queue.generate_review_queue()
    assert queue_result["status"] == "PASS"

    gate_result = gate.apply_quality_gate()
    assert gate_result["status"] == "PASS"
    assert gate_result["production_status"] == "NO_GO"
    assert gate_result["external_api_called"] is False
    assert gate_result["external_network_called"] is False
    assert gate_result["wordpress_write_executed"] is False
    assert gate_result["creators_api_called"] is False
    assert gate_result["amazon_scraping_called"] is False

    assert gate_result["item_count"] >= 5
    assert "ready_high_priority" in gate_result["bucket_counts"]
    assert "blocked_or_invalid" in gate_result["bucket_counts"]

    quality_queue = gate_result["quality_queue"]
    assert len(quality_queue) == gate_result["item_count"]

    assert any(item["asin_present"] is True for item in quality_queue)
    assert any(item["asin_missing"] is True for item in quality_queue)
    assert any(item["missing_title"] is True or item["missing_author"] is True for item in quality_queue)

    bucket_order = {name: idx for idx, name in enumerate(gate_result["bucket_order"])}
    bucket_ranks = [bucket_order[item["review_bucket"]] for item in quality_queue]
    assert bucket_ranks == sorted(bucket_ranks)

    readiness_result = readiness.check_readiness()
    assert readiness_result["status"] == "PASS"

    report_result = report.generate_report()
    assert report_result["status"] == "PASS"
    assert report_result["phase"] in {"SFB-2", "SFB-3", "SFB-4", "SFB-5", "SFB-6", "SFB-7", "SFB-8", "SFB-8B", "SFB-9", "SFB-10", "SFB-10B"}
    assert report_result["quality_gate_status"] == "PASS"
    assert report_result["production_status"] == "NO_GO"
    assert report_result["external_api_called"] is False
    assert report_result["external_network_called"] is False
    assert report_result["wordpress_write_executed"] is False

    assert (LOGS / "sale_review_quality_gate.json").exists()
    assert (LOGS / "sale_flash_block_report.json").exists()
    assert (LOGS / "sale_flash_block_report.md").exists()
