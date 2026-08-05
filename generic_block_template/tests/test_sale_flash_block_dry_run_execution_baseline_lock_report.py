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


def test_sfb8b_dry_run_execution_baseline_lock_report_generation():
    run = _load_module("sfb8b_run", BLOCK_ROOT / "run.py")
    report = _load_module("sfb8b_report", SCRIPTS / "generate_sale_flash_block_report.py")
    lock = _load_module(
        "sfb8b_lock",
        SCRIPTS / "generate_sale_flash_block_dry_run_execution_baseline_lock_report.py",
    )

    policy = json.loads((CONFIG / "dry_run_execution_baseline_lock_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "SFB-8B"
    assert policy["mode"] == "DRY_RUN"
    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["wordpress_write_allowed"] is False

    run_result = run.run_block()
    assert run_result["status"] in {"PASS", "WARN"}

    payload = lock.generate_dry_run_execution_baseline_lock_report()
    assert payload["status"] == "PASS"
    assert payload["phase"] == "SFB-8B"
    assert payload["baseline_locked"] is True
    assert payload["production_status"] == "NO_GO"

    checks = payload["checks"]
    assert checks["required_reports_present"] is True
    assert checks["phase_status_all_pass"] is True
    assert checks["production_status_no_go"] is True
    assert checks["no_external_communication"] is True
    assert checks["human_approval_unconsumed"] is True
    assert checks["final_human_gate_ready"] is True
    assert checks["wordpress_dry_run_execution_gate_ready"] is True
    assert checks["simulated_execution_count_ready"] is True
    assert checks["simulated_execution_count"] >= 1

    assert (LOGS / "sale_flash_block_dry_run_execution_baseline_lock_report.json").exists()
    assert (LOGS / "sale_flash_block_dry_run_execution_baseline_lock_report.md").exists()

    md_text = (LOGS / "sale_flash_block_dry_run_execution_baseline_lock_report.md").read_text(encoding="utf-8")
    assert "# Sale Flash Block DRY_RUN Execution Baseline Lock Report" in md_text
    assert "- status: PASS" in md_text
    assert "- baseline_locked: True" in md_text
    assert "- production_status: NO_GO" in md_text

    report_result = report.generate_report()
    assert report_result["phase"] in {"SFB-8B", "SFB-9", "SFB-10", "SFB-10B"}
    assert report_result["dry_run_execution_baseline_lock_status"] in {"PASS", "WARN", "NOT_GENERATED"}
    assert report_result["dry_run_execution_baseline_locked"] is True

    report_md = (LOGS / "sale_flash_block_report.md").read_text(encoding="utf-8")
    assert "## DRY_RUN Execution Baseline Lock" in report_md
