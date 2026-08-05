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


def test_sfb6b_baseline_lock_report_generation():
    run = _load_module("sfb6b_run", BLOCK_ROOT / "run.py")
    lock = _load_module("sfb6b_lock", SCRIPTS / "generate_sale_flash_block_baseline_lock_report.py")

    policy = json.loads((CONFIG / "baseline_lock_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "SFB-6B"
    assert policy["mode"] == "DRY_RUN"
    assert policy["production_status"] == "NO_GO"
    assert policy["external_api_allowed"] is False
    assert policy["external_network_allowed"] is False
    assert policy["wordpress_write_allowed"] is False

    run_result = run.run_block()
    assert run_result["status"] in {"PASS", "WARN"}

    payload = lock.generate_baseline_lock_report()
    assert payload["status"] == "PASS"
    assert payload["phase"] == "SFB-6B"
    assert payload["baseline_locked"] is True
    assert payload["production_status"] == "NO_GO"

    checks = payload["checks"]
    assert checks["required_reports_present"] is True
    assert checks["phase_status_all_pass"] is True
    assert checks["production_status_no_go"] is True
    assert checks["no_external_communication"] is True
    assert checks["human_approval_unconsumed"] is True
    assert checks["final_human_gate_ready"] is True
    assert checks["final_human_gate_status"] == "READY_FOR_FINAL_HUMAN_GATE"

    assert (LOGS / "sale_flash_block_baseline_lock_report.json").exists()
    assert (LOGS / "sale_flash_block_baseline_lock_report.md").exists()

    md_text = (LOGS / "sale_flash_block_baseline_lock_report.md").read_text(encoding="utf-8")
    assert "# Sale Flash Block Baseline Lock Report" in md_text
    assert "- status: PASS" in md_text
    assert "- baseline_locked: True" in md_text
    assert "- production_status: NO_GO" in md_text
