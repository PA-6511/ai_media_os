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


def test_sfb9_final_signoff_archive_generation():
    run = _load_module("sfb9_run", BLOCK_ROOT / "run.py")
    signoff = _load_module("sfb9_signoff", SCRIPTS / "generate_final_signoff_archive.py")
    report = _load_module("sfb9_report", SCRIPTS / "generate_sale_flash_block_report.py")

    policy = json.loads((CONFIG / "final_signoff_archive_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "SFB-9"
    assert policy["mode"] == "DRY_RUN"
    assert policy["production_status"] == "NO_GO"
    assert policy["wordpress_write_allowed"] is False

    run_result = run.run_block()
    assert run_result["status"] in {"PASS", "WARN"}

    payload = signoff.generate_final_signoff_archive()
    assert payload["status"] == "PASS"
    assert payload["phase"] == "SFB-9"
    assert payload["mode"] == "DRY_RUN"
    assert payload["production_status"] == "NO_GO"

    assert payload["baseline_locked"] is True
    assert payload["final_human_gate_status"] == "READY_FOR_FINAL_HUMAN_GATE"
    assert payload["wordpress_dry_run_execution_gate"] == "READY_FOR_DRY_RUN_ONLY"
    assert payload["signoff_ready"] is True

    assert payload["approval_token_consumed"] is False
    assert payload["approval_label_consumed"] is False
    assert payload["human_approval_consumed"] is False

    assert payload["production_write_blocked"] is True
    assert payload["allow_production_write"] is False
    assert payload["decision"]["allow_wordpress_production_write"] is False

    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["publish_executed"] is False
    assert payload["update_executed"] is False
    assert payload["delete_executed"] is False
    assert payload["export_executed"] is False

    assert (LOGS / "final_signoff_archive.json").exists()
    assert (LOGS / "final_signoff_archive.md").exists()

    md_text = (LOGS / "final_signoff_archive.md").read_text(encoding="utf-8")
    assert "# Final Sign-off Archive" in md_text
    assert "- production_status: NO_GO" in md_text
    assert "- production_write_blocked: True" in md_text

    report_result = report.generate_report()
    assert report_result["phase"] in {"SFB-9", "SFB-10", "SFB-10B"}
    assert report_result["final_signoff_archive_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert report_result["signoff_ready"] is True

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## Final Sign-off Archive" in report_md
