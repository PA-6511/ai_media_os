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


def test_sfb8_wordpress_dry_run_execution_evidence_generation():
    run = _load_module("sfb8_run", BLOCK_ROOT / "run.py")
    evidence = _load_module("sfb8_evidence", SCRIPTS / "generate_wordpress_dry_run_execution_evidence.py")
    report = _load_module("sfb8_report", SCRIPTS / "generate_sale_flash_block_report.py")

    policy = json.loads((CONFIG / "wordpress_dry_run_execution_evidence_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "SFB-8"
    assert policy["mode"] == "DRY_RUN"
    assert policy["production_status"] == "NO_GO"
    assert policy["wordpress_write_allowed"] is False

    run_result = run.run_block()
    assert run_result["status"] in {"PASS", "WARN"}

    payload = evidence.generate_wordpress_dry_run_execution_evidence()
    assert payload["status"] == "PASS"
    assert payload["phase"] == "SFB-8"
    assert payload["mode"] == "DRY_RUN"
    assert payload["production_status"] == "NO_GO"
    assert payload["gate_ready"] is True
    assert payload["wordpress_dry_run_execution_gate"] == "READY_FOR_DRY_RUN_ONLY"

    assert payload["simulated_execution_count"] >= 1
    assert len(payload["simulated_execution_events"]) == payload["simulated_execution_count"]

    for event in payload["simulated_execution_events"]:
        assert event["event_type"] == "wordpress_dry_run_simulation"
        assert event["simulated_endpoint"] == "/wp-json/wp/v2/posts"
        assert event["simulated_result"]["accepted"] is True
        assert event["network_called"] is False
        assert event["wordpress_write_executed"] is False

    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["publish_executed"] is False
    assert payload["update_executed"] is False
    assert payload["delete_executed"] is False
    assert payload["export_executed"] is False
    assert payload["human_approval_consumed"] is False
    assert payload["production_write_blocked"] is True

    assert (LOGS / "wordpress_dry_run_execution_evidence.json").exists()
    assert (LOGS / "wordpress_dry_run_execution_evidence.md").exists()

    md_text = (LOGS / "wordpress_dry_run_execution_evidence.md").read_text(encoding="utf-8")
    assert "# WordPress DRY_RUN Execution Evidence" in md_text
    assert "- production_status: NO_GO" in md_text
    assert "- simulated_execution_count:" in md_text

    report_result = report.generate_report()
    assert report_result["phase"] in {"SFB-8", "SFB-8B", "SFB-9", "SFB-10", "SFB-10B"}
    assert report_result["wordpress_dry_run_evidence_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert "wordpress_dry_run_evidence_count" in report_result

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## WordPress DRY_RUN Execution Evidence" in report_md
